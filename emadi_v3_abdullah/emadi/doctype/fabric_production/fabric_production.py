# Copyright (c) 2025, Safdar Ali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from emadi_v3_abdullah.emadi.doctype.utils_functions import get_doctype_by_field

class FabricProduction(Document):
	
	# def on_update(self):
	# 	for item in self.fabric_production_item:
	# 		if item.get("for") == "Weft":
	# 			item.warehouse = "Stores - ET"
	# 		elif item.get("for") == "Warp":
	# 			item.warehouse = "Beem Store - ET"
		

	def on_submit(self):
		if self.fabric_production_item:
			doc = frappe.new_doc("Stock Entry")
			doc.stock_entry_type = "Manufacture"
			doc.purpose = "Manufacture"
			doc.set_posting_time = 1
			doc.posting_date = self.posting_date
			doc.posting_time = self.posting_time
			doc.fabric_production = self.name
			target_warehouse = self.target_warehouse
		
			# Append source item
			it = doc.append("items", {})
			it.t_warehouse = target_warehouse
			it.item_code = self.fabric_item
			it.qty = self.qty
			it.is_finished_item = 1
			if self.valuation_type == 1:
				it.allow_zero_valuation_rate = 1
			# else:
				# it.allow_zero_valuation_rate = 0
				# it.set_basic_rate_manually = 1
				# it.basic_rate = self.finish_rate
				# it.basic_amount = self.finish_rate * self.qty
			
				
			# Append target items using a loop
			for item in self.fabric_production_item:
				it = doc.append("items", {})
				it.s_warehouse = item.warehouse
				it.item_code = item.yarn_count
				if item.set_no:
					it.batch_no = item.set_no
				if item.beam_length:
					it.qty = item.beam_length
				else:
					it.qty = item.yarn_qty
				if self.valuation_type == 1:
					it.allow_zero_valuation_rate = 1
				else:
					it.allow_zero_valuation_rate = 0
					

			try:
				# if self.valuation_type == 0 and self.finish_rate > 0:
					# doc.save()
				# elif self.valuation_type == 1:
				doc.save()  #backwarded  remov issue
				# else:
					# frappe.throw("Rate must be greater than zero")
					
				doc.submit()
			except Exception as e:
				frappe.throw("Error submitting Stock Entry: {0}".format(str(e)))	


	def on_cancel(self):
		current_je = get_doctype_by_field('Stock Entry', 'fabric_production', self.name)
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
		
        
        