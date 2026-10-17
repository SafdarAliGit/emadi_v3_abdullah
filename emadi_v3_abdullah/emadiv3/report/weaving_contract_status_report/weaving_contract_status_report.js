// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Weaving Contract Status Report"] = {
	"filters": [
		{"fieldname": "weaver", "label": "Customer", "fieldtype": "Link", "options": "Customer"},
	{"fieldname": "construction", "label": "Item", "fieldtype": "Link", "options": "Item"},
	{"fieldname": "weaving_contract", "label": "Weaving Contract", "fieldtype": "Link", "options": "Weaving Contract"},
	{"fieldname": "date_from", "label": "Date From", "fieldtype": "Date"},
	{"fieldname": "date_to", "label": "Date To", "fieldtype": "Date"}
	]
};
