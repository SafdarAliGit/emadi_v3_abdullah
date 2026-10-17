import frappe
from frappe import _

@frappe.whitelist()
def get_fabric_items():
    """
    Fetch all Item Codes where item_group='Fabric' and disabled=0
    Returns a list of dicts with item_code
    """
    fabric_items = frappe.get_all(
        "Item",
        filters={
            "item_group": "Fabric",
            "disabled": 0
        },
        fields=["item_code"]
    )
    return fabric_items
