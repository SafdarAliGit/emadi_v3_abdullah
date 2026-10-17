import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def make_customer_yarn_material_request(weaving_contract):
    """Weaving Contract > "Create Material Request for Yarn".

    Returns an unsaved Customer Provided Material Request for the contract's
    Customer, one row per BOM Items row: Item Code = Yarn Count, Qty = Yarn Qty.
    """
    contract = frappe.get_doc("Weaving Contract", weaving_contract)
    if contract.docstatus != 1:
        frappe.throw(_("Weaving Contract {0} must be submitted first.").format(weaving_contract))
    if not contract.customer:
        frappe.throw(_("Set Customer on Weaving Contract {0} first.").format(weaving_contract))

    mr = frappe.new_doc("Material Request")
    mr.material_request_type = "Customer Provided"
    mr.transaction_date = frappe.utils.nowdate()
    mr.schedule_date = frappe.utils.nowdate()
    mr.customer = contract.customer
    mr.weaving_contract = contract.name

    for row in contract.bom_items or []:
        if not row.yarn_count:
            continue
        stock_uom = frappe.db.get_value("Item", row.yarn_count, "stock_uom")
        mr.append(
            "items",
            {
                "item_code": row.yarn_count,
                "description": row.yarn_count,
                "qty": flt(row.yarn_qty),
                "uom": stock_uom,
                "stock_uom": stock_uom,
                "conversion_factor": 1,
                "schedule_date": mr.schedule_date,
                "weaving_contract": contract.name,
                "for": row.get("for"),
                "construction": contract.construction,
                "bags": row.required_bags,
                "brand": row.get("brand"),
            },
        )

    if not mr.items:
        frappe.throw(_("No yarn rows found on Weaving Contract {0}.").format(weaving_contract))

    set_total_bags(mr)
    return mr


def set_total_bags(doc):
    """custom_total_bags = qty / 100 per row, total qty / 100 on the parent."""
    total_qty = 0.0
    for row in doc.get("items") or []:
        row.custom_total_bags = flt(row.qty) / 100
        total_qty += flt(row.qty)
    doc.custom_total_bags = total_qty / 100


def validate(doc, method=None):
    set_total_bags(doc)
