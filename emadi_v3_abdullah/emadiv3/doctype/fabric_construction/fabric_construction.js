// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fabric Construction', {
	refresh: function(frm) {

		frm.set_query('quality', function () {
			return {
				filters: [
					["item_group", "=", "Fabric"]
				]
			};
		});

		frm.set_query('fabric_item', function() {
			return {
				"filters": {
					"item_group": "Fabric"
				}
			}
		});

		frm.set_query('yarn_count','fabric_construction_item', function() {
			return {
				"filters": [
					["item_group", "IN", ["Yarn", "Beam"]]
				]
			}
		})

	}
});
