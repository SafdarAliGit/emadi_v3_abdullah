# Copyright (c) 2025, Safdar Ali and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from emadi_v3_abdullah.emadi.events.weaving_yarn_balance import (
	get_contract_tcs,
	get_tcs_lines,
	validate_contract_yarn_balance,
)


class WeavingContract(Document):
	def validate(self):
		if is_multi_item(self):
			sync_multi_item_fields(self)
		else:
			sync_gsm(self)
		# Submitted contracts are re-saved by Open / Close (custom_status) -
		# leave their quantities alone then.
		if self.docstatus == 1 and getattr(self, "_action", None) != "submit":
			return
		sync_yarn_driven_fields(self)
		if is_multi_item(self):
			validate_multi_item_ratios(self)
		# Commercial contracts don't use the Towel Costing Sheet, so there is
		# no TCS yarn balance to check.
		if self.type != "Commercial":
			# Draft save: warn only. Submit: hard stop (fresh DB re-read).
			validate_contract_yarn_balance(self, hard=self.docstatus == 1)

	def on_submit(self):
		allocate_sales_order_balance(self)
		create_beam_items(self)

	def on_cancel(self):
		release_sales_order_balance(self)

	@frappe.whitelist()
	def recalc_yarn_from_order_qty(self):
		"""2026-09-28 (feature v3) - "yarn qty will be recalculated upon
		changing Order Qty. yarn qty = yarn reqd per lbs (from TCS) *
		order qty" (your words). Forward direction of the same relationship
		sync_yarn_driven_fields already runs backwards (yarn lbs -> Order
		Qty): only touches BOM Items rows whose (For, Yarn) is actually on
		this Finish Item's Towel Costing Sheet, same restriction used
		everywhere else this balance logic runs. Called from the client on
		the Order Qty field's change event - only reachable there when the
		field isn't read-only, i.e. this contract isn't already being
		driven the other way by yarn balances (see weaving_contract.js)."""
		if not (self.sales_order and self.construction):
			frappe.throw(_("Set Sales Order and Finish Item first."))

		tcs = get_contract_tcs(self)
		lines = get_tcs_lines(tcs, self.construction)
		if not lines:
			frappe.throw(
				_("No yarn lines found on the Towel Costing Sheet for {0}.").format(self.construction)
			)

		for row in self.get("bom_items") or []:
			k = (self.construction, (row.get("for") or "").strip(), row.yarn_count or "")
			if k in lines:
				row.yarn_qty = lines[k]["per_pc"] * flt(self.fabric_qty)

		sync_yarn_driven_fields(self)


def is_multi_item(doc):
	return doc.get("type") == "Commercial" and cint(doc.get("multi_item_weaving_contract"))


def sync_multi_item_fields(doc):
	"""Multi Item Weaving Contract: Finish Item, GSM, Finish Weight and Gross
	Weight come from the first row of the Finish Items table, Order Qty is the
	total of all rows."""
	rows = doc.get("finish_items") or []
	if not rows:
		frappe.throw(_("Add at least one row in the Finish Items table."))

	seen = set()
	for row in rows:
		if row.finish_item in seen:
			frappe.throw(_("Row {0}: Finish Item {1} is entered more than once.").format(row.idx, row.finish_item))
		seen.add(row.finish_item)

	first = rows[0]
	doc.construction = first.finish_item
	doc.gsm = flt(first.gsm)
	doc.finish_weight = flt(first.finish_weight)
	doc.gross_weight = flt(first.gross_weight)
	doc.fabric_qty = sum(flt(r.order_qty) for r in rows)


def validate_multi_item_ratios(doc):
	"""Every BOM Items row needs a Finish Item from the Finish Items table, and
	the Ratio % of each Finish Item's rows must add up to 100."""
	finish_items = [r.finish_item for r in doc.get("finish_items") or []]
	totals = {item: 0.0 for item in finish_items}

	for row in doc.get("bom_items") or []:
		if not row.get("finish_item"):
			frappe.throw(_("BOM Items row {0}: Finish Item is required.").format(row.idx))
		if row.finish_item not in totals:
			frappe.throw(
				_("BOM Items row {0}: Finish Item {1} is not in the Finish Items table.").format(row.idx, row.finish_item)
			)
		totals[row.finish_item] += flt(row.ratio)

	for item, total in totals.items():
		if abs(total - 100) > 0.01:
			frappe.throw(
				_("Ratio % of the yarn rows for Finish Item {0} adds up to {1}, it must be 100.").format(
					item, frappe.format(total, {"fieldtype": "Float", "precision": 2})
				)
			)


def get_gsm_from_tcs(towel_costing_sheet, item_code):
	"""GSM lives on the Towel Costing Sheet's Finish Item table - one row
	per Article (finish item), matched here the same way Sales Order Item's
	GSM is matched (garments_app_v3_abdullah.events.sales_order_dyeing_calc)."""
	if not (towel_costing_sheet and item_code):
		return 0
	tcs = frappe.get_cached_doc("Towel Costing Sheet", towel_costing_sheet)
	for row in tcs.get("finish_item_towel_costing") or []:
		if row.article == item_code:
			return flt(row.gsm)
	return 0


def find_tcs_by_finish_item(item_code):
	"""2026-09-28 - "the gsm should be fetched from Towel Cost Sheet of
	Finish Item" (your words): the Sales Order-linked TCS lookup
	(get_contract_tcs) came back empty on your test contract, most likely
	because it wasn't created via Get Items From Sales Order (or the
	Sales Order Item's Towel Costing Sheet was blank), leaving no TCS to
	find GSM on. This is a direct fallback that doesn't need a Sales
	Order at all: any Towel Costing Sheet whose Finish Item table lists
	this Finish Item as its Article, most recently modified one first."""
	if not item_code:
		return None
	rows = frappe.db.sql(
		"""
		select fi.parent as tcs
		from `tabFinish Item Towel Costing` fi
		inner join `tabTowel Costing Sheet` tcs on tcs.name = fi.parent
		where fi.article = %s
		order by tcs.modified desc
		limit 1
		""",
		(item_code,),
	)
	return rows[0][0] if rows else None


def sync_gsm(doc):
	"""2026-09-28 (feature v3) - GSM on Weaving Contract. Prefers the TCS
	actually behind this contract's Sales Order (get_contract_tcs, most
	accurate to this specific order); falls back to any TCS listing this
	Finish Item (find_tcs_by_finish_item above) so GSM still shows on a
	contract with no Sales Order / Sales Order Item TCS set. Authoritative
	recompute on every save; the client-side get_contract_gsm below is
	just a live preview on Finish Item / Sales Order change."""
	construction = doc.get("construction")
	tcs = get_contract_tcs(doc) or find_tcs_by_finish_item(construction)
	doc.gsm = get_gsm_from_tcs(tcs, construction)


@frappe.whitelist()
def get_contract_gsm(sales_order=None, sales_order_item=None, construction=None):
	"""Live client-side fetch for the Finish Item / Sales Order change
	handlers in weaving_contract.js - see sync_gsm above for the
	authoritative, save-time version of this same lookup."""
	fake_doc = frappe._dict(
		sales_order=sales_order, sales_order_item=sales_order_item, construction=construction
	)
	tcs = get_contract_tcs(fake_doc) or find_tcs_by_finish_item(construction)
	return get_gsm_from_tcs(tcs, construction)


def sync_yarn_driven_fields(doc):
	"""2026-09-26 - contracts are split BY YARN LBS. Yarn Qty is what the
	user edits; everything else follows it:
	  Required Bags = Yarn Qty / Lbs per Bag            (per row)
	  Total Yarn / Total Consumption / Total Bags        (sums)
	  Fabric Qty    = total Yarn Qty / TCS lbs per piece (all yarns of
	                  this item) - only when linked to a Sales Order.
	Fabric Qty is what allocate_sales_order_balance draws down per piece
	on submit; because every yarn is capped at its own lbs balance, the
	pieces derived this way can never add up to more than the Sales Order
	qty across contracts."""
	commercial = doc.get("type") == "Commercial"
	# Multi item: each yarn row is worked out from its own Finish Item's
	# Order Qty and Gross Weight.
	finish_items = (
		{r.finish_item: r for r in doc.get("finish_items") or []} if is_multi_item(doc) else {}
	)
	total_yarn = 0.0
	total_bags = 0.0
	for row in doc.get("bom_items") or []:
		if commercial:
			# Commercial: no TCS - Yarn Qty comes from the parent's Gross Weight
			# (grams per piece), in LBS:
			# ((Gross Weight * Order Qty) / 1000) * 2.2046 * Ratio %, plus Weaving Wastage %
			if finish_items:
				source = finish_items.get(row.get("finish_item"))
				gross_weight = flt(source.gross_weight) if source else 0
				order_qty = flt(source.order_qty) if source else 0
			else:
				gross_weight = flt(doc.get("gross_weight"))
				order_qty = flt(doc.get("fabric_qty"))
			row.yarn_qty = (
				(gross_weight * order_qty / 1000)
				* 2.2046
				* flt(row.ratio)
				/ 100
				* (1 + flt(row.get("weaving_wastage")) / 100)
			)
		if flt(row.lbs_per_bag):
			row.required_bags = flt(row.yarn_qty) / flt(row.lbs_per_bag)
		total_yarn += flt(row.yarn_qty)
		total_bags += flt(row.required_bags)

	doc.total_yarn = total_yarn
	doc.total_consumption = total_yarn
	doc.total_bags = total_bags

	if not commercial and doc.get("sales_order") and doc.get("construction"):
		tcs = get_contract_tcs(doc)
		lines = get_tcs_lines(tcs, doc.construction)
		per_piece_total = sum(line["per_pc"] for line in lines.values())
		if per_piece_total:
			# only yarns that are on the TCS count towards pieces
			tcs_lbs = sum(
				flt(row.yarn_qty)
				for row in doc.get("bom_items") or []
				if (doc.construction, (row.get("for") or "").strip(), row.yarn_count or "") in lines
			)
			doc.fabric_qty = tcs_lbs / per_piece_total


def allocate_sales_order_balance(doc):
	"""Draws doc.fabric_qty down against every Sales Order Item row on
	doc.sales_order matching doc.construction (item_code) - oldest row
	(lowest idx) first - and records exactly what was drawn from each row
	in doc.sales_order_item_allocations (JSON), so on_cancel can release
	precisely that back, no more no less.

	2026-09-14 update: replaces the old single-sales_order_item reserve.
	An Item can now span multiple Sales Order Item rows (one per Color -
	see the Dyeing feature), and weaving draws from the combined pool
	since it doesn't care about Color. Re-queries fresh from the database
	rather than trusting anything computed client-side at fetch time -
	same "server is the source of truth" pattern used everywhere else in
	this project - so a balance change from another contract submitted in
	between fetch and this submit is still respected correctly (and
	over-drawing is a hard error, not a silent short-allocation).
	"""
	if not (doc.sales_order and doc.construction):
		return

	# Multi item contracts draw each Finish Item's Order Qty from its own
	# Sales Order rows; every other contract has the one item.
	if is_multi_item(doc):
		draws = [(r.finish_item, flt(r.order_qty)) for r in doc.get("finish_items") or []]
	else:
		draws = [(doc.construction, flt(doc.fabric_qty))]

	allocations = []
	for item_code, qty in draws:
		rows = frappe.get_all(
			"Sales Order Item",
			filters={"parent": doc.sales_order, "item_code": item_code},
			fields=["name", "qty", "custom_weave_qty"],
			order_by="idx asc",
		)

		remaining = qty

		for row in rows:
			if remaining <= 0:
				break
			available = flt(row.qty) - flt(row.custom_weave_qty)
			if available <= 0:
				continue
			take = min(available, remaining)
			frappe.db.set_value(
				"Sales Order Item", row.name, "custom_weave_qty", flt(row.custom_weave_qty) + take
			)
			allocations.append({"sales_order_item": row.name, "qty": take})
			remaining -= take

		# Fabric Qty is derived from yarn lbs (sync_yarn_driven_fields), so a
		# few thousandths of a piece of float rounding must not block submit.
		if remaining > 0.01:
			frappe.throw(
				_(
					"Only {0} of {1} is actually available against Sales Order {2} for Item {3} right now "
					"(someone else may have used part of the balance since you fetched it) - reduce Order "
					"Qty or use Get Items From Sales Order again."
				).format(qty - remaining, qty, doc.sales_order, item_code)
			)

	frappe.db.set_value(
		"Weaving Contract", doc.name, "sales_order_item_allocations", json.dumps(allocations)
	)


def release_sales_order_balance(doc):
	raw = doc.get("sales_order_item_allocations")
	if raw:
		try:
			allocations = json.loads(raw)
		except ValueError:
			allocations = []
		for allocation in allocations:
			current = flt(
				frappe.db.get_value("Sales Order Item", allocation["sales_order_item"], "custom_weave_qty")
			)
			frappe.db.set_value(
				"Sales Order Item",
				allocation["sales_order_item"],
				"custom_weave_qty",
				max(0, current - flt(allocation["qty"])),
			)
		return

	# Fallback for a Weaving Contract submitted before this update (no
	# allocations JSON was ever recorded for it) - old single-row release,
	# unchanged, so an in-flight contract from before this fix still
	# cancels correctly.
	if not doc.sales_order_item:
		return
	current = flt(frappe.db.get_value("Sales Order Item", doc.sales_order_item, "custom_weave_qty"))
	frappe.db.set_value(
		"Sales Order Item", doc.sales_order_item, "custom_weave_qty", max(0, current - flt(doc.fabric_qty))
	)


def create_beam_items(doc):
	"""On submit, make sure a Beam Item exists for each Pile/Ground row in
	the BOM Items table - item_code = BEAM-<Pile or Ground>-<yarn count>.
	Never blocks submission: an existing item is just reported, not an error.
	"""
	created = []
	existing = []

	for row in doc.bom_items or []:
		beam_for = row.get("for")
		if beam_for not in ("Pile", "Ground"):
			continue
		if not row.yarn_count:
			continue

		item_code = f"BEAM-{beam_for}-{row.yarn_count}"

		if frappe.db.exists("Item", item_code):
			existing.append(item_code)
			continue

		item = frappe.new_doc("Item")
		item.item_code = item_code
		item.item_name = item_code
		item.item_group = "Beam"
		item.stock_uom = "Nos"
		item.is_stock_item = 1
		# Sizing Receipt makes one Batch per beam, so Beam items are batch tracked
		item.has_batch_no = 1
		item.insert(ignore_permissions=True)
		created.append(item_code)

	if created:
		frappe.msgprint(
			_("Item(s) created: {0}").format(", ".join(created)),
			alert=True,
			indicator="green",
		)
	if existing:
		frappe.msgprint(
			_("Item(s) already exist: {0}").format(", ".join(existing)),
			alert=True,
			indicator="blue",
		)
