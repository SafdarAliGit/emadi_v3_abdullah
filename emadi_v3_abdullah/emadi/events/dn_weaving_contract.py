import json

import frappe
from frappe import _
from frappe.utils import flt

KG_TO_LBS = 2.2046


@frappe.whitelist()
def get_weaving_contract_dn_data(weaving_contracts):
    """For the Delivery Note's "Fetch Items from Weaving Contract" button.

    Returns, per contract, the Finish Item (construction) and its BOM Items
    rows (For, Yarn Count, Ratio, ...). Yarn Qty is worked out on the
    Delivery Note from the row's Weight LBS."""
    if isinstance(weaving_contracts, str):
        weaving_contracts = json.loads(weaving_contracts)

    out = []
    for name in weaving_contracts:
        contract = frappe.get_doc("Weaving Contract", name)
        if contract.docstatus != 1:
            frappe.throw(_("Weaving Contract {0} is not submitted.").format(name))
        out.append(
            {
                "weaving_contract": contract.name,
                "construction": contract.construction,
                "bom_items": [
                    {
                        "for": r.get("for"),
                        "yarn_count": r.yarn_count,
                        "ratio": flt(r.ratio),
                        "uom": r.get("uom"),
                        "brand": r.get("brand"),
                    }
                    for r in contract.bom_items or []
                ],
            }
        )
    return out


def validate(doc, method=None):
    for row in doc.get("items") or []:
        row.custom_weight_lbs = flt(row.get("custom_weight_kg")) * KG_TO_LBS
        row.custom_pieces = flt(row.get("stock_qty")) or flt(row.qty) * (flt(row.conversion_factor) or 1)

    # Yarn Qty = Weight LBS of the matching DN item row(s) * Ratio %
    for bom in doc.get("bom_items_dn") or []:
        if not (flt(bom.get("ratio")) and bom.get("fabric_item") and bom.get("weaving_contract")):
            continue
        lbs = sum(
            flt(i.custom_weight_lbs)
            for i in doc.get("items") or []
            if i.item_code == bom.fabric_item and i.get("custom_weaving_contract_reference") == bom.weaving_contract
        )
        bom.yarn_qty = lbs * flt(bom.ratio) / 100
