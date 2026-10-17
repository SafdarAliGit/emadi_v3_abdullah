import frappe
from frappe.model.document import Document

@frappe.whitelist()
def create_stock_entry_from_weaving_contract(weaving_contract):
    # Fetch the Weaving Contract document
    contract = frappe.get_doc("Weaving Contract", weaving_contract)
    se = frappe.db.get_value("Stock Entry", {"weaving_contract": weaving_contract}, "name")
    se_doc = None
    if se:
        se_doc = frappe.get_doc("Stock Entry", se)
    if se_doc and se_doc.docstatus != 2:
        frappe.throw(f"Stock Entry already created for {weaving_contract} Weaving Contract")
    # Create a new Stock Entry
    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Receipt"  # Change as needed
    stock_entry.purpose = "Material Receipt"
    stock_entry.weaving_contract = weaving_contract  # Link back to Weaving Contract
    stock_entry.weaver = contract.weaver  # Link back to Weaving Contract

    # Loop through child items (bom_items) and add them to Stock Entry items
    for item in contract.bom_items:
        stock_entry.append("items", {
            "item_code": item.yarn_count,
            "qty": item.yarn_qty,
            "uom": item.uom,
            "stock_uom": item.uom,
            "allow_zero_valuation_rate": 1,
            "t_warehouse": "Customer Warehouse - ET"
        })

    # Return the Stock Entry name to open in the form view
    return stock_entry

