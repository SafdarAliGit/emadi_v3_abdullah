import frappe
from frappe.model.document import Document


@frappe.whitelist()
def create_material_request_from_weaving_contract(weaving_contract):
    # Fetch the Weaving Contract document
    contract = frappe.get_doc("Weaving Contract", weaving_contract)
    mr = frappe.db.get_value("Material Request", {"weaving_contract": weaving_contract}, "name")
    mr_doc = None
    if mr:
        mr_doc = frappe.get_doc("Material Request", mr) if mr else None  
    # if mr_doc and mr_doc.docstatus != 2:
    #     frappe.throw(f"Material Request already created for {weaving_contract} Weaving Contract")
    # Create a new Stock Entry
    material_request = frappe.new_doc("Material Request")
    material_request.material_request_type = "Customer Provided"  # Change as needed
    material_request.schedule_date = frappe.utils.nowdate()
    material_request.weaving_contract = weaving_contract  # Link back to Weaving Contract
    material_request.customer = contract.weaver  # Link back to Weaving Contract

    # Loop through child items (bom_items) and add them to Stock Entry items
    for item in contract.bom_items:
        material_request.append("items", {
            "item_code": item.yarn_count,
            "qty": item.yarn_qty,
            "weaving_contract": contract.name,
            "for":item.get("for"),
            "construction":contract.construction,
            "bags":item.required_bags,
            "uom":item.uom,
            "stock_uom":item.uom,
            "description":item.yarn_count,
            "brand": item.brand
        })

    # Return the Stock Entry name to open in the form view
    return material_request

