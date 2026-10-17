// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Daily Fabric Production', {
	refresh: function(frm) {
		frm.set_query("fabric_item","daily_fabric_production_item", function() {
			return {
				filters: {
					item_group: "Fabric"
				}
			}
		});
		
	},
	fetch_all_fabric_items: function(frm) {
		frappe.call({
			method: "emadi_v3_abdullah.emadi.events.get_fabric_items.get_fabric_items",
			callback: function(r) {
				if (r.message && r.message.length) {
					// Clear existing rows (optional)
					frm.clear_table('daily_fabric_production_item');

					r.message.forEach(item => {
						let row = frm.add_child('daily_fabric_production_item');
						row.fabric_item = item.item_code;  // child table field
					});

					frm.refresh_field('daily_fabric_production_item');
					frappe.msgprint(__('Fabric items have been fetched and added.'));
				} else {
					frappe.msgprint(__('No fabric items found.'));
				}
			}
		});
	}
});

