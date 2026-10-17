import json

import frappe
from frappe import _
from frappe.utils import flt

# "Issue Yarn" button on Weaving Contract (submitted only) - "same workflow
# like issue fabric in dyeing contract is needed in Weaving Contract ...
# user will enter qty of each yarn mentioned in weaving contract in the
# popup, same material transfer entry will be opened, user will submit the
# entry himself, same sales order and weaving contract reference will be
# mentioned in stock entry" (your words). Mirrors Dyeing Contract's
# issue_fabric()/apply_issued_qty()/reverse_issued_qty() almost exactly -
# see mjfsd_v3_abdullah/events/issue_fabric.py - with two differences:
#
# 1. Rows are BOM Items (one per yarn), not Dyeing Contract Items - the
#    qty issued/remaining is tracked in Lbs against `yarn_qty` (your
#    choice when asked - Yarn Qty (Lbs), not Required Bags), in a new
#    `yarn_issued` custom field (see custom/bom_items.json).
#
# 2. Source/Target Warehouse are fixed, not read off the contract or asked
#    in the popup (your answer when asked): always "Source - PT" ->
#    "Supplier - PT". Validated to actually exist before building the
#    Stock Entry, so a typo'd/renamed warehouse throws a clear error
#    instead of a confusing one lower down in ERPNext's own stock code.
#
# Built the accumulator (yarn_issued) as self-healing from day one -
# sync_yarn_issued_totals() below queries actually-submitted Stock Entries
# directly, the same fix that had to be retrofitted onto Dyeing Contract's
# Issued Qty after its on_submit hooks.py wiring couldn't be confirmed
# (see claude/dyeing-workflow.md, 2026-09-16 follow-up). No separate
# on_submit/on_cancel hooks.py entries needed for this one at all.

SOURCE_WAREHOUSE = "Source - PT"
TARGET_WAREHOUSE = "Supplier - PT"


@frappe.whitelist()
def issue_yarn(weaving_contract, rows):
	"""rows: JSON list of {"row_name": <BOM Items row name>, "qty": <float, Lbs>}.
	Returns the inserted (not yet submitted) Stock Entry doc, for the
	browser to route to - same "user reviews and submits it himself"
	pattern as Issue Fabric."""
	if isinstance(rows, str):
		rows = json.loads(rows)

	for wh in (SOURCE_WAREHOUSE, TARGET_WAREHOUSE):
		if not frappe.db.exists("Warehouse", wh):
			frappe.throw(_("Warehouse {0} doesn't exist - check the exact name/spelling.").format(wh))

	wc = frappe.get_doc("Weaving Contract", weaving_contract)
	if wc.docstatus != 1:
		frappe.throw(_("Weaving Contract must be submitted before yarn can be issued."))

	bom_rows_by_name = {r.name: r for r in wc.bom_items}

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Transfer"
	se.purpose = "Material Transfer"
	se.company = frappe.defaults.get_global_default("company")
	# 2026-09-28 fix - this was setting `custom_weaving_contract`, a field
	# that doesn't exist anywhere on Stock Entry (silently dropped on
	# save - Frappe lets you set an attribute that isn't a real field,
	# it just never gets persisted). Stock Entry already has its own
	# plain `weaving_contract` field (no "custom_" prefix, from
	# emadi_v3_abdullah's own custom/stock_entry.json) - that's the one to set.
	# Same bug, already caught and fixed in mjfsd_v3_abdullah's copy of this file
	# a while back; this is the copy actually wired to the Issue Yarn
	# button (see weaving_contract.js) and had fallen out of sync.
	# "same sales order and weaving contract reference will be mentioned
	# in stock entry" (your words) - now also fetches Weaver, added
	# 2026-09-28: "create a field of Weaver (Linked to supplier, fetch
	# from weaving contract) ... Weaving Contract Ref".
	se.weaving_contract = wc.name
	se.weaver = wc.weaver
	if wc.sales_order:
		se.custom_sales_order = wc.sales_order

	issued_any = False
	for entry in rows:
		qty = flt(entry.get("qty"))
		if not qty:
			continue

		row_name = entry.get("row_name")
		bom_row = bom_rows_by_name.get(row_name)
		if not bom_row:
			frappe.throw(_("Row {0} not found on Weaving Contract {1}").format(row_name, wc.name))
		if not bom_row.yarn_count:
			frappe.throw(_("Row #{0} has no Yarn Count set - can't issue.").format(bom_row.idx))

		se.append(
			"items",
			{
				"s_warehouse": SOURCE_WAREHOUSE,
				"t_warehouse": TARGET_WAREHOUSE,
				"item_code": bom_row.yarn_count,
				"qty": qty,
				"uom": frappe.db.get_value("Item", bom_row.yarn_count, "stock_uom"),
				"custom_bom_item": row_name,
			},
		)
		issued_any = True

	if not issued_any:
		frappe.throw(_("Enter a qty to issue for at least one yarn."))

	se.insert(ignore_permissions=True)

	return se


@frappe.whitelist()
def sync_yarn_issued_totals(weaving_contract):
	"""Self-healing recompute, hooks.py-independent from day one - see the
	module docstring above and claude/dyeing-workflow.md's 2026-09-16
	follow-up for why this pattern is preferred over an incremental
	on_submit/on_cancel accumulator in this project now. Overwrites each
	BOM Items row's yarn_issued with the real sum straight from
	actually-submitted Stock Entries. Only writes (and only tells the
	caller to reload) when something was actually stale."""
	wc = frappe.get_doc("Weaving Contract", weaving_contract)
	row_names = [row.name for row in wc.bom_items or []]
	if not row_names:
		return {"changed": False}

	totals = frappe.db.sql(
		"""
		select sed.custom_bom_item as row_name,
		       sum(sed.qty) as yarn_issued
		from `tabStock Entry Detail` sed
		inner join `tabStock Entry` se on se.name = sed.parent
		where se.docstatus = 1
		  and sed.custom_bom_item in %(row_names)s
		group by sed.custom_bom_item
		""",
		{"row_names": row_names},
		as_dict=True,
	)
	totals_by_row = {t.row_name: flt(t.yarn_issued) for t in totals}

	changed = False
	for row in wc.bom_items or []:
		real_yarn_issued = totals_by_row.get(row.name, 0.0)
		if abs(real_yarn_issued - flt(row.get("yarn_issued"))) > 0.0001:
			frappe.db.set_value("BOM Items", row.name, "yarn_issued", real_yarn_issued)
			changed = True

	return {"changed": changed}
