# Copyright (c) 2025, Safdar Ali and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from emadi_v3_abdullah.emadi.doctype.utils_functions import get_doctype_by_field

class FabricProductionOutSide(Document):
	
	# def on_update(self):
	# 	for item in self.fabric_production_item:
	# 		if item.get("for") == "Weft":
	# 			item.warehouse = "Stores - ET"
	# 		elif item.get("for") == "Warp":
	# 			item.warehouse = "Beem Store - ET"
		

	def on_submit(self):
		if self.fabric_production_out_side_item:
			doc = frappe.new_doc("Stock Entry")
			doc.stock_entry_type = "Manufacture"
			doc.purpose = "Manufacture"
			doc.set_posting_time = 1
			doc.posting_date = self.posting_date
			doc.posting_time = self.posting_time
			doc.custom_fabric_production_out_side = self.name
			target_warehouse = self.target_warehouse
			# additional costs
			
			if self.amount and self.expense_account and self.supplier:
				it = doc.append("additional_costs", {})
				it.expense_account = self.expense_account
				it.description = self.supplier or ""
				it.amount = self.amount
			if self.fabric_production_other_charges_item:
				
				for row in self.fabric_production_other_charges_item:
					if not row.amount:
						continue

					it = doc.append("additional_costs", {})
					it.expense_account = row.account
					it.description = row.detail or ""
					it.amount = row.amount

			# Append source item
			it = doc.append("items", {})
			it.t_warehouse = target_warehouse
			it.item_code = self.fabric_item
			it.qty = self.qty
			it.is_finished_item = 1
			if self.valuation_type == 1:
				it.allow_zero_valuation_rate = 1
			else:
				it.allow_zero_valuation_rate = 0
				it.set_basic_rate_manually = 1
				it.basic_rate = self.finish_rate
				it.basic_amount = self.finish_rate * self.qty
			
				
			# Append target items using a loop
			for item in self.fabric_production_out_side_item:
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
				if self.valuation_type == 0 and self.finish_rate > 0:
					doc.save()
				elif self.valuation_type == 1:
					doc.save()
				else:
					frappe.throw("Rate must be greater than zero")
					
					# updat stock entry
					# if self.valuation_type == 0:
					# 	stock_entry = frappe.get_doc("Stock Entry", doc.name)
					# 	total_amount = stock_entry.total_outgoing_value or 0.0
				# 	single_target_row = None

				# 	# pick the first item with a target warehouse set
				# 	for item in stock_entry.items:
				# 		if getattr(item, 't_warehouse', None):
				# 			single_target_row = item
				# 			break

				# 	if single_target_row and single_target_row.qty:
				# 		qty = float(single_target_row.qty) or 0.0
				# 		if qty > 0:
				# 			new_rate = total_amount / qty
				# 			single_target_row.basic_rate = new_rate
				# 			single_target_row.basic_amount = new_rate * qty
				# 		else:
				# 			frappe.throw(f"Invalid quantity {single_target_row.qty} for computing rate")
				# 	# save and submit
				# 	stock_entry.reload()  # Reload before saving
				# 	stock_entry.save()
				# 	frappe.db.commit()  # Commit the rate calculation changes
		
				# doc.reload()
				doc.submit()
			except Exception as e:
				frappe.throw("Error submitting Stock Entry: {0}".format(str(e)))	


	def on_cancel(self):
		current_je = get_doctype_by_field('Stock Entry', 'custom_fabric_production_out_side', self.name)
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
		
        
        