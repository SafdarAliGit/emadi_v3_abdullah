// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Weaving Stock Report"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": "From Date",
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_start_date"),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": "To Date",
			"fieldtype": "Date",
			"default": frappe.defaults.get_user_default("year_end_date"),
			"reqd": 1
		},
		 {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer"
        },
		{
			"fieldname": "brand",
			"label": "Brand",
			"fieldtype": "Link",
			"options": "Brand",
			// "reqd": 1
		},
		{
			"fieldname": "item_code",	
			"label": "Yarn Item",
			"fieldtype": "Link",
			"options": "Item",
			"reqd": 1,
			"get_query": function() {
				return {
					"filters": {
						"item_group": "Yarn"
					}
				};
			}
		}
	]
};
