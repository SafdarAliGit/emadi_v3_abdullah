import frappe

def sync_item_enabled(doc, method=None):
    """
    Sync Fabric Construction.enabled → Item.enabled
    """

    if not doc.quality:
        return

    frappe.db.set_value(
        "Item",
        doc.quality,
        "enabled",
        doc.enabled
    )
