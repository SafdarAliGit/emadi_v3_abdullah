import frappe
from frappe.model.document import Document


@frappe.whitelist()
def fetch_fabric_construction_items(quality, qty):
    """
    Fetch Fabric Construction Item rows where:
    - parent = quality
    - parent Fabric Construction is enabled
    Calculate yarn_qty as consumption * qty
    """

    items = frappe.db.sql("""
        SELECT
            fci.`for`,
            fci.yarn_count,
            fci.consumption
        FROM
            `tabFabric Construction Item` fci
        INNER JOIN
            `tabFabric Construction` fc
        ON
            fci.parent = fc.name
        WHERE
            fci.parent = %s
            AND fc.enabled = 1
    """, (quality,), as_dict=True)

    for item in items:
        item["yarn_qty"] = (item.get("consumption") or 0) * float(qty)

    return items

