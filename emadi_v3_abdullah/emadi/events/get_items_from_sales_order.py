import frappe
from frappe import _
from frappe.utils import flt

from emadi_v3_abdullah.emadi.events.weaving_yarn_balance import (
	get_per_piece_total,
	get_tcs_lines,
	get_yarn_balances,
)

# 2026-09-26: weaving balance is now tracked PER YARN (lbs), not per fabric
# piece - see weaving_yarn_balance.py. Several Weaving Contracts can be made
# against the same Sales Order item / yarn, each taking part of the lbs
# (e.g. 1000 lbs of 20/S -> two contracts of 500 lbs). The prefill offers
# whatever is left of each yarn; the user edits Yarn Qty down to split it.
# Fabric Qty is then derived from the lbs on save (Weaving Contract
# validate), so the old per-piece draw-down (custom_weave_qty) still works.


@frappe.whitelist()
def get_sales_order_items(sales_order):
	"""Finish items on a Sales Order that still have yarn left to contract,
	for the Weaving Contract item pickers (Sales Order button and Weaving
	Contract's "Get Items From > Sales Order"). One entry per item_code,
	combined across all of its Sales Order rows (one per Color).

	Items with no Towel Costing Sheet yarn lines fall back to the old
	per-piece balance (qty - custom_weave_qty) so they still show up."""
	so_items = frappe.get_all(
		"Sales Order Item",
		filters={"parent": sales_order},
		fields=["item_code", "item_name", "qty", "custom_weave_qty"],
		order_by="idx asc",
	)

	groups = {}
	for d in so_items:
		g = groups.setdefault(
			d.item_code,
			{"item_code": d.item_code, "item_name": d.item_name, "balance_qty": 0.0, "yarn_balance_lbs": 0.0},
		)
		g["balance_qty"] += flt(d.qty) - flt(d.custom_weave_qty)

	balances = get_yarn_balances(sales_order)
	has_yarn_lines = set()
	for (item_code, _for, _yarn), b in balances.items():
		if item_code in groups:
			has_yarn_lines.add(item_code)
			groups[item_code]["yarn_balance_lbs"] += b["balance"]

	out = []
	for item_code, g in groups.items():
		if item_code in has_yarn_lines:
			if g["yarn_balance_lbs"] > 0.001:
				out.append(g)
		elif g["balance_qty"] > 0:
			out.append(g)
	return out


@frappe.whitelist()
def get_weaving_items_from_sales_order(sales_order, item_code):
	"""Weaving Contract's own "Get Items From > Sales Order" picker."""
	return _get_weaving_data_from_sales_order(sales_order, item_code)


@frappe.whitelist()
def create_weaving_contract_from_sales_order(sales_order, item_code=None):
	"""Sales Order -> Weaving Contract button: unsaved draft, prefilled with
	the same data as the picker above, routed to by the browser."""
	multi = _get_multi_item_data(sales_order) if not item_code else None
	if multi:
		# Several unique items on the Sales Order: one Commercial, Multi Item contract
		wc = frappe.new_doc("Weaving Contract")
		wc.sales_order = sales_order
		wc.sales_order_item = multi["sales_order_item"]
		wc.type = "Commercial"
		wc.multi_item_weaving_contract = 1
		for row in multi["finish_items"]:
			wc.append("finish_items", row)
		for row in multi["bom_items"]:
			wc.append("bom_items", row)
		return wc

	if not item_code:
		frappe.throw(_("Select a Finish Item."))

	data = _get_weaving_data_from_sales_order(sales_order, item_code)

	wc = frappe.new_doc("Weaving Contract")
	wc.sales_order = sales_order
	wc.sales_order_item = data["sales_order_item"]
	wc.construction = data["item_code"]
	wc.fabric_qty = data["order_qty"]
	wc.finish_weight = data["finish_weight"]
	wc.gross_weight = data["gross_weight"]

	for row in data["bom_items"]:
		wc.append("bom_items", row)

	return wc


def _get_weaving_data_from_sales_order(sales_order, item_code):
	so_items = frappe.get_all(
		"Sales Order Item",
		filters={"parent": sales_order, "item_code": item_code},
		fields=["name", "qty", "custom_weave_qty", "custom_towel_costing_sheet"],
		order_by="idx asc",
	)
	if not so_items:
		frappe.throw(_("Item {0} not found on Sales Order {1}").format(item_code, sales_order))

	# Representative row: its TCS supplies wastage / weights / ratios, and
	# its name goes on Weaving Contract.sales_order_item so downstream docs
	# (e.g. Weaving Receipt's TCS lookup) keep working unchanged.
	representative = next((d for d in so_items if d.custom_towel_costing_sheet), so_items[0])
	towel_costing_sheet = representative.custom_towel_costing_sheet

	piece_balance = sum(flt(d.qty) - flt(d.custom_weave_qty) for d in so_items)

	bom_items = []
	weaving_wastage = 0
	finish_weight = 0
	gross_weight = 0
	order_qty = piece_balance

	if towel_costing_sheet:
		tcs = frappe.get_doc("Towel Costing Sheet", towel_costing_sheet)
		for finish_row in tcs.finish_item_towel_costing or []:
			if finish_row.article == item_code:
				weaving_wastage = flt(finish_row.weaving_wastage_percet)
				finish_weight = flt(finish_row.finish_weight)
				gross_weight = flt(finish_row.greige_weight)
				break

		balances = get_yarn_balances(sales_order, item_code)
		total_lbs = 0.0
		for k, line in get_tcs_lines(towel_costing_sheet, item_code).items():
			remaining = flt(balances.get(k, {}).get("balance"))
			if remaining <= 0.001:
				# this yarn is fully contracted already - no 0-lbs row
				continue
			per_pc = line["per_pc"]
			lbs_per_bag = per_pc / line["bags_per_pc"] if line["bags_per_pc"] else 0
			bom_items.append(
				{
					"for": k[1],
					"yarn_count": k[2],
					"ratio": line["ratio"],
					"weaving_wastage": weaving_wastage,
					"yarn_qty": remaining,
					"so_yarn_balance": remaining,
					"lbs_per_bag": lbs_per_bag,
					# Required Bags is a Float field - no rounding.
					"required_bags": remaining / lbs_per_bag if lbs_per_bag else 0,
				}
			)
			total_lbs += remaining

		per_piece_total = get_per_piece_total(towel_costing_sheet, item_code)
		if per_piece_total:
			order_qty = total_lbs / per_piece_total

	return {
		"item_code": item_code,
		"order_qty": order_qty,
		"sales_order_item": representative.name,
		"towel_costing_sheet": towel_costing_sheet,
		"finish_weight": finish_weight,
		"gross_weight": gross_weight,
		"bom_items": bom_items,
	}


def _get_multi_item_data(sales_order):
	"""Several unique finish items on one Sales Order become ONE Commercial,
	Multi Item Weaving Contract: a Finish Items row per item (Order Qty, Finish
	Weight and Greige Weight from the item's Towel Costing Sheet) and BOM Items
	rows tagged with their Finish Item. Returns None when the Sales Order has
	fewer than two weavable items (the normal single item flow applies)."""
	from emadi_v3_abdullah.emadiv3.doctype.weaving_contract.weaving_contract import get_gsm_from_tcs

	items = get_sales_order_items(sales_order)
	if len(items) < 2:
		return None

	finish_items = []
	bom_items = []
	sales_order_item = None
	for item in items:
		data = _get_weaving_data_from_sales_order(sales_order, item["item_code"])
		sales_order_item = sales_order_item or data["sales_order_item"]
		gross_weight = flt(data["gross_weight"])
		order_qty = flt(data["order_qty"])
		finish_items.append(
			{
				"finish_item": item["item_code"],
				"gsm": get_gsm_from_tcs(data["towel_costing_sheet"], item["item_code"]),
				"finish_weight": flt(data["finish_weight"]),
				"gross_weight": gross_weight,
				"order_qty": order_qty,
			}
		)
		for row in data["bom_items"]:
			row = dict(row)
			row["finish_item"] = item["item_code"]
			# Commercial formula (same as Weaving Contract's save-time one)
			row["yarn_qty"] = (
				(gross_weight * order_qty / 1000)
				* 2.2046
				* flt(row.get("ratio"))
				/ 100
				* (1 + flt(row.get("weaving_wastage")) / 100)
			)
			if flt(row.get("lbs_per_bag")):
				row["required_bags"] = row["yarn_qty"] / flt(row["lbs_per_bag"])
			bom_items.append(row)

	return {
		"sales_order_item": sales_order_item,
		"finish_items": finish_items,
		"bom_items": bom_items,
	}


@frappe.whitelist()
def get_multi_item_weaving_data(sales_order):
	"""Weaving Contract's own "Get Items From > Sales Order": the payload for a
	multi item contract, or None if the Sales Order has a single weavable item."""
	return _get_multi_item_data(sales_order)
