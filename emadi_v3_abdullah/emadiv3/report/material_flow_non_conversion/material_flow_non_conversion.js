// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Material Flow Non Conversion"] = {
	filters: [
		{
			fieldname: "p",
			label: "Waste %",
			fieldtype: "Float",
			default: 10
		},
		{
			fieldname: "brand",
			label: "Brand",
			fieldtype: "Link",
			options: "Brand"
		},
		{
			fieldname: "yarn_count",
			label: "Yarn Count Warp",
			fieldtype: "MultiSelectList",
			options: "Item",
			get_data: function (txt) {
				return frappe.db.get_link_options("Item", txt, {
					is_stock_item: 1,
					item_group: ["in", ["Yarn", "Beam"]]
				});
			}
		},
		{
			fieldname: "yarn_count_weft",
			label: "Yarn Count Weft",
			fieldtype: "MultiSelectList",
			options: "Item",
			get_data: function (txt) {
				return frappe.db.get_link_options("Item", txt, {
					is_stock_item: 1,
					item_group: "Yarn"
				});
			}
		},
		{
			fieldname: "fabric_item",
			label: "Fabric Item",
			fieldtype: "MultiSelectList",
			options: "Item",
			get_data: function (txt) {
				return frappe.db.get_link_options("Item", txt, {
					is_stock_item: 1,
					item_group: "Fabric"
				});
			}
		}
	]
};
