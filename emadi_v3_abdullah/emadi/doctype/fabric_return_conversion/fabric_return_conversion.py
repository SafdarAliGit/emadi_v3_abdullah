
import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from emadi_v3_abdullah.emadi.doctype.utils_functions import get_doctype_by_field

class FabricReturnConversion(Document):
	
	def on_submit(self):
		if self.fabric_return_conversion_item:
			doc = frappe.new_doc("Stock Entry")
			doc.stock_entry_type = "Material Receipt"
			doc.purpose = "Material Receipt"
			doc.set_posting_time = 1
			doc.posting_date = self.posting_date
			doc.posting_time = self.posting_time
			doc.custom_fabric_return_conversion = self.name
			target_warehouse = self.target_warehouse
		
			# Append source item
			it = doc.append("items", {})
			it.t_warehouse = target_warehouse
			it.item_code = self.fabric_item
			it.qty = self.qty
			it.allow_zero_valuation_rate = 1		

			try:
				doc.save()
				doc.submit()
			except Exception as e:
				frappe.throw("Error submitting Stock Entry: {0}".format(str(e)))	


	def on_cancel(self):
		current_je = get_doctype_by_field('Stock Entry', 'custom_fabric_return_conversion', self.name)
		if current_je:
			if current_je.docstatus != 2:  # Ensure the document is in the "Submitted" state
				current_je.cancel()
				frappe.db.commit()
			else:
				frappe.throw("Document is not in the 'Submitted' state.")
			if current_je.amended_from:
				new_name = int(current_je.name.split("-")[-1]) + 1
			else:
				new_name = f"{current_je.name}-{1}"
			make_autoname(new_name, 'Stock Entry')
		
        
        