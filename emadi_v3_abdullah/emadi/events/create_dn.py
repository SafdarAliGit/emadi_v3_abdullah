import frappe
from frappe.model.document import Document

def onsubmit(doc, method):
    if not doc.custom_non_conversion:
        
        if doc.is_return == 1:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.set_posting_time = 1
            stock_entry.stock_entry_type = "Fabric Return"
            stock_entry.posting_date = doc.posting_date
            stock_entry.posting_time = doc.posting_time
            stock_entry.company = doc.company
            stock_entry.return_entry = 1

            stock_entry.append("items", {
                "item_code": doc.fabric_item,
                "qty": abs(doc.fabric_qty),
                "t_warehouse": doc.set_warehouse,
                "uom": frappe.db.get_value("Item", doc.fabric_item, "stock_uom"),
                "allow_zero_valuation_rate": 1
            })

            stock_entry.custom_delivery_note_no = doc.name
            stock_entry.insert()
            stock_entry.submit()
        else:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.set_posting_time = 1
            stock_entry.stock_entry_type = "Fabric Delivered"
            stock_entry.posting_date = doc.posting_date
            stock_entry.posting_time = doc.posting_time
            stock_entry.company = doc.company

            # Add item row
            stock_entry.append("items", {
                "item_code": doc.fabric_item,
                "qty": doc.fabric_qty,
                "s_warehouse": doc.set_warehouse,
                "uom": frappe.db.get_value("Item", doc.fabric_item, "stock_uom"),
                "allow_zero_valuation_rate": 1
            })

            # Link to Delivery Note
            stock_entry.custom_delivery_note_no = doc.name

            stock_entry.insert()
            stock_entry.submit()


@frappe.whitelist()
def create_dn(weaving_contract):
    # Fetch the Weaving Contract document
    contract = frappe.get_doc("Weaving Contract", weaving_contract)

    # Check if a Delivery Note already exists and is not canceled
    # existing_dn = frappe.db.get_value("Delivery Note", {"weaving_contract": weaving_contract}, "name")
    # if existing_dn:
    #     existing_dn_doc = frappe.get_doc("Delivery Note", existing_dn)
    #     if existing_dn_doc.docstatus != 2:  # Not canceled
    #         frappe.throw(f"Delivery Note already exists for Weaving Contract {weaving_contract}: {existing_dn}")

    # Create a new Delivery Note
    delivery_note = frappe.new_doc("Delivery Note")
    delivery_note.posting_date = contract.date
    delivery_note.posting_time = contract.time
    delivery_note.currency = "PKR"
    delivery_note.customer = contract.weaver  # Ensure 'weaver' is set in Weaving Contract
    delivery_note.fabric_item = contract.construction
    delivery_note.weaving_contract = weaving_contract
    delivery_note.custom_non_conversion = 0

    # Add BOM items if available
    
    delivery_note.append("items", {
        "item_code": "Sizing / Weaving Charges",
        "item_name":"Sizing / Weaving Charges",
        "description":"Sizing / Weaving Charges",
        "qty": 0,
        "rate": contract.total_charges_per_meter,
        "uom": "Meter",
        "stock_uom": "Meter",
        "fabric_item": contract.construction

    })
    
    if contract.get("bom_items"):
        for item in contract.bom_items:
            delivery_note.append("bom_items_dn", {
                "for": item.get("for"),
                "yarn_count": item.get("yarn_count"),
                "consumption": item.get("consumption"),
                "yarn_qty": 0,
                "uom": item.uom,
                "brand": item.brand,
                "weaving_contract": weaving_contract
            })

    # Save and submit the Delivery Note

    return delivery_note  # Return the name to open in form view

