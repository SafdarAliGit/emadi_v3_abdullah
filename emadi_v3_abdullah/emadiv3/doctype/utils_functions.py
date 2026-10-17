import frappe

# FOR SINGLE LINKED DOCTYPE
def get_doctype_by_field(doctype_name, field_name, field_value):
    query = frappe.get_all(doctype_name, filters={field_name: field_value}, fields=["name", "docstatus","amended_from"])

    if query:
        docname = query[0].name
        doc = frappe.get_doc(doctype_name, docname)
        return doc
    else:
        return None


