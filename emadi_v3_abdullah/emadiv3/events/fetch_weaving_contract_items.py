import frappe
from frappe.model.document import Document

@frappe.whitelist()
def fetch_weaving_contract_items(weaving_contract,qty):
    items = frappe.get_all(
        "BOM Items",
        filters={"parent": weaving_contract},
        fields=["for", "yarn_count", "consumption","uom","brand"]
    )

    for item in items:
        item["yarn_qty"] = item["consumption"] * float(qty)  # Calculate yarn_qty

    return items
