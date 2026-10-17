# Copyright (c) 2025, Safdar Ali and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from emadi_v3_abdullah.emadi.events.weaving_yarn_balance import (
	get_contract_tcs,
	get_tcs_lines,
	validate_contract_yarn_balance,
)


class WeavingContract(Document):
	def validate(self):
		# Submitted contracts are re-saved by Open / Close (custom_status) -
		# leave their quantities alone then.
		if self.docstatus == 1 and getattr(self, "_action", None) != "submit":
			return
		sync_yarn_driven_fields(self)
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
	total_yarn = 0.0
	total_bags = 0.0
	for row in doc.get("bom_items") or []:
		if flt(row.lbs_per_bag):
			row.required_bags = flt(row.yarn_qty) / flt(row.lbs_per_bag)
		total_yarn += flt(row.yarn_qty)
		total_bags += flt(row.required_bags)

	doc.total_yarn = total_yarn
	doc.total_consumption = total_yarn
	doc.total_bags = total_bags

	if doc.get("sales_order") and doc.get("construction"):
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

	rows = frappe.get_all(
		"Sales Order Item",
		filters={"parent": doc.sales_order, "item_code": doc.construction},
		fields=["name", "qty", "custom_weave_qty"],
		order_by="idx asc",
	)

	remaining = flt(doc.fabric_qty)
	allocations = []

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
			).format(flt(doc.fabric_qty) - remaining, doc.fabric_qty, doc.sales_order, doc.construction)
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
