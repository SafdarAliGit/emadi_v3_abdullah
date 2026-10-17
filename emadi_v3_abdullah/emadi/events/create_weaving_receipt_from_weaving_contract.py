import frappe
from frappe import _

# "Weaving Receipt" button on Weaving Contract (shown only when Type =
# External). Builds an unsaved Weaving Receipt with one Items row
# prefilled from this contract - reuses the exact same row shape as
# mjfsd_v3_abdullah's own get_weaving_contract_items() (the "Get Items From > Weaving
# Contract" popup already on Weaving Receipt itself), so both paths stay
# consistent. Returns the unsaved doc for the browser to route to
# (frappe.model.sync + frappe.set_route) - does NOT insert or submit
# anything, matching this project's "prefill, open the form, let the user
# review and save" pattern for buttons that create a new document.
#
# 2026-09-28 fix - "weaving receipt is still asking for weaver ... when it
# is already mentioned in Weaving Contract. Also, Source and Target
# warehouse is also empty" (your words). This button never went through
# weaving_receipt.js's own "Get Items From" dialog (that's what sets
# Weaver + locks it, on the OTHER path into Weaving Receipt) - it only
# ever appended the Items row and returned. Weaver, Source Warehouse and
# Target Warehouse were never set on the header at all here, which is why
# they came back empty/required no matter what the Weaving Contract had.
# Fixed to set all three explicitly, same fixed-warehouse pattern as
# issue_yarn.py's own SOURCE_WAREHOUSE/TARGET_WAREHOUSE (validated to
# actually exist first, so a typo'd/renamed warehouse throws a clear
# error here too instead of failing confusingly on save).
#
# Also stopped dumping the row's "weaver" key straight into the Items
# child row - Weaving Receipt Item has no such field (it's header-only),
# so it was just a harmless but meaningless extra attribute on the child
# doc; now popped off and used to set the header field instead.

SOURCE_WAREHOUSE = "Supplier - PT"
TARGET_WAREHOUSE = "Finished Goods - PT"


@frappe.whitelist()
def create_weaving_receipt_from_weaving_contract(weaving_contract):
	from mjfsd_v3_abdullah.loom_production.events.create_weaving_receipt import get_weaving_contract_items

	for wh in (SOURCE_WAREHOUSE, TARGET_WAREHOUSE):
		if not frappe.db.exists("Warehouse", wh):
			frappe.throw(_("Warehouse {0} doesn't exist - check the exact name/spelling.").format(wh))

	wc = frappe.get_doc("Weaving Contract", weaving_contract)
	if wc.docstatus != 1:
		frappe.throw(_("Weaving Contract must be submitted first."))

	rows = get_weaving_contract_items([wc.name])
	if not rows:
		frappe.throw(_("Could not build a Weaving Receipt row from {0}.").format(wc.name))

	wr = frappe.new_doc("Weaving Receipt")
	wr.source_warehouse = SOURCE_WAREHOUSE
	wr.target_warehouse = TARGET_WAREHOUSE

	weavers = set()
	for row in rows:
		weaver = row.pop("weaver", None)
		if weaver:
			weavers.add(weaver)
		wr.append("items", row)

	# Only set/locked when every row (i.e. every selected contract - here
	# always just one) agrees on the weaver, same rule as the "Get Items
	# From" dialog on Weaving Receipt itself.
	if len(weavers) == 1:
		wr.weaver = weavers.pop()

	return wr
