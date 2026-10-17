import frappe


def before_validate(doc, method=None):
    """Stock Entry made from a Material Request (e.g. Material Receipt) keeps the
    Weaving Contract of that Material Request, on the header and on each row."""
    mr_names = {row.material_request for row in doc.get("items") or [] if row.get("material_request")}
    if not mr_names:
        return

    if not doc.get("weaving_contract"):
        contracts = {
            frappe.db.get_value("Material Request", mr, "weaving_contract") for mr in mr_names
        } - {None, ""}
        if len(contracts) == 1:
            doc.weaving_contract = contracts.pop()

    for row in doc.get("items") or []:
        if row.get("weaving_contract") or not row.get("material_request"):
            continue
        contract = None
        if row.get("material_request_item"):
            contract = frappe.db.get_value(
                "Material Request Item", row.material_request_item, "weaving_contract"
            )
        row.weaving_contract = contract or frappe.db.get_value(
            "Material Request", row.material_request, "weaving_contract"
        )
