frappe.query_reports["Quality Wise Consumption"] = {
    "filters": [
        {
            "fieldname": "fabric_item",
            "label": "Quality",
            "fieldtype": "MultiSelectList",
            "options": "Item",
            "reqd": 1,
            "get_data": function(txt) {
                return frappe.db.get_link_options('Item', txt, {
                    is_stock_item: 1,
                    item_group: 'Fabric'
                });
            }
        }
    ]
};
