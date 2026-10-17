import frappe
from frappe.model.document import Document

@frappe.whitelist()
def open_weaving_contract(weaving_contract):
    """
    Open the Weaving Contract
    """
    doc = frappe.get_doc("Weaving Contract", weaving_contract)
    doc.custom_status = "Open"
    doc.save()
    
    return doc  # Send updated doc back to client
