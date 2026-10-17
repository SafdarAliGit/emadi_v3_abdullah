import frappe
from frappe import _
from frappe.utils import flt

# Per-yarn (lbs) weaving balance against a Sales Order - 2026-09-26.
#
# "Sales order qty requires 1000 LBS of 20/S Yarn, there can be 2 weaving
# contracts of 500 LBS each" (your words) - split confirmed to be BY YARN
# LBS, so the balance is tracked per yarn, not per fabric piece.
#
# Balance key = (finish item, for, yarn count), i.e. one line of the Towel
# Costing Sheet's Raw Materials table:
#   Required = sum over every Sales Order Item row of that finish item of
#              row Qty x Yarn Required in (Lbs)   (row's own TCS)
#   Used     = sum of BOM Items Yarn Qty on every SUBMITTED Weaving
#              Contract for this Sales Order + finish item, same for/yarn
#   Balance  = Required - Used
#
# "Used" is always re-read from submitted contracts, never stored as a
# counter - so cancelling a contract gives its lbs back automatically and
# nothing can drift. Drafts don't reserve anything; the hard check runs on
# submit. Closed (custom_status = Close) contracts still count as used.

TOLERANCE = 0.001


def _key(item_code, for_, yarn):
	return (item_code or "", (for_ or "").strip(), yarn or "")


def get_tcs_lines(towel_costing_sheet, item_code):
	"""Raw Materials lines of one TCS for one finish item, merged per
	(for, yarn): {key: {"per_pc": lbs per piece, "bags_per_pc": bags per
	piece, "ratio": ratio}}"""
	lines = {}
	if not towel_costing_sheet:
		return lines
	tcs = frappe.get_cached_doc("Towel Costing Sheet", towel_costing_sheet)
	for m in tcs.get("materials") or []:
		if m.item != item_code or not m.raw_material:
			continue
		k = _key(item_code, m.get("for"), m.raw_material)
		line = lines.setdefault(k, {"per_pc": 0.0, "bags_per_pc": 0.0, "ratio": 0.0})
		line["per_pc"] += flt(m.yarn_required_in_lbs)
		line["bags_per_pc"] += flt(m.bags_reqd)
		line["ratio"] += flt(m.ratio)
	return lines


def get_yarn_required(sales_order, item_code=None):
	filters = {"parent": sales_order}
	if item_code:
		filters["item_code"] = item_code
	rows = frappe.get_all(
		"Sales Order Item",
		filters=filters,
		fields=["item_code", "qty", "custom_towel_costing_sheet"],
		order_by="idx asc",
	)
	required = {}
	for row in rows:
		for k, line in get_tcs_lines(row.custom_towel_costing_sheet, row.item_code).items():
			required[k] = required.get(k, 0) + flt(row.qty) * line["per_pc"]
	return required


def get_yarn_used(sales_order, item_code=None, exclude_contract=None):
	conditions = ["wc.docstatus = 1", "wc.sales_order = %(sales_order)s"]
	values = {"sales_order": sales_order}
	if item_code:
		conditions.append("wc.construction = %(item_code)s")
		values["item_code"] = item_code
	if exclude_contract:
		conditions.append("wc.name != %(exclude)s")
		values["exclude"] = exclude_contract

	rows = frappe.db.sql(
		f"""
		select wc.construction, bi.`for` as for_, bi.yarn_count, sum(bi.yarn_qty) as qty
		from `tabBOM Items` bi
		inner join `tabWeaving Contract` wc on wc.name = bi.parent and bi.parenttype = 'Weaving Contract'
		where {" and ".join(conditions)}
		group by wc.construction, bi.`for`, bi.yarn_count
		""",
		values,
		as_dict=True,
	)
	return {_key(r.construction, r.for_, r.yarn_count): flt(r.qty) for r in rows}


def get_yarn_balances(sales_order, item_code=None, exclude_contract=None):
	"""{key: {"required", "used", "balance"}} for every TCS yarn line."""
	required = get_yarn_required(sales_order, item_code)
	used = get_yarn_used(sales_order, item_code, exclude_contract)
	out = {}
	for k, req in required.items():
		u = flt(used.get(k))
		out[k] = {"required": req, "used": u, "balance": max(0.0, req - u)}
	return out


def get_per_piece_total(towel_costing_sheet, item_code):
	"""Total yarn lbs per piece of this finish item on its TCS - used to
	convert a contract's yarn lbs back into an equivalent fabric qty."""
	return sum(line["per_pc"] for line in get_tcs_lines(towel_costing_sheet, item_code).values())


def get_contract_tcs(doc):
	"""The TCS behind a Weaving Contract - from its Sales Order Item row,
	else the first row of that Sales Order carrying this item."""
	tcs = None
	if doc.get("sales_order_item"):
		tcs = frappe.db.get_value("Sales Order Item", doc.sales_order_item, "custom_towel_costing_sheet")
	if not tcs and doc.get("sales_order") and doc.get("construction"):
		tcs = frappe.db.get_value(
			"Sales Order Item",
			{"parent": doc.sales_order, "item_code": doc.construction, "custom_towel_costing_sheet": ["is", "set"]},
			"custom_towel_costing_sheet",
		)
	return tcs


def validate_contract_yarn_balance(doc, hard=True):
	"""Every BOM Items row must fit inside what's left of its yarn on the
	Sales Order (other submitted contracts excluded from `used`, this one
	not counted). Rows for a yarn that isn't on the TCS aren't checked."""
	if not (doc.get("sales_order") and doc.get("construction")):
		return

	balances = get_yarn_balances(doc.sales_order, doc.construction, exclude_contract=doc.name)

	asked = {}
	for row in doc.get("bom_items") or []:
		k = _key(doc.construction, row.get("for"), row.yarn_count)
		if k in balances:
			asked[k] = asked.get(k, 0) + flt(row.yarn_qty)

	over = []
	for k, qty in asked.items():
		bal = balances[k]["balance"]
		if qty > bal + TOLERANCE:
			over.append(
				_("{0} ({1}): {2} lbs entered, only {3} lbs left (required {4}, already contracted {5})").format(
					k[2],
					k[1] or "-",
					frappe.format(qty, {"fieldtype": "Float"}),
					frappe.format(bal, {"fieldtype": "Float"}),
					frappe.format(balances[k]["required"], {"fieldtype": "Float"}),
					frappe.format(balances[k]["used"], {"fieldtype": "Float"}),
				)
			)

	if not over:
		return

	msg = _("Yarn exceeds the Sales Order {0} balance for {1}:").format(doc.sales_order, doc.construction)
	msg += "<br>" + "<br>".join(over)
	if hard:
		frappe.throw(msg, title=_("Yarn Balance Exceeded"))
	else:
		frappe.msgprint(msg + "<br><br>" + _("You can save, but it will be blocked on submit."), indicator="orange", title=_("Yarn Balance"))
