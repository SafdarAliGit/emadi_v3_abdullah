import frappe
from frappe.model.document import Document

@frappe.whitelist()
def close_weaving_contract(weaving_contract):
    """
    Close the Weaving Contract
    """
    doc = frappe.get_doc("Weaving Contract", weaving_contract)
    doc.custom_status = "Close"
    doc.save()
    
    return doc  # Send updated doc back to client
