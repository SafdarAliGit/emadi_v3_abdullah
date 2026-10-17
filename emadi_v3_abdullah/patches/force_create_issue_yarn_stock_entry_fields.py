import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# 2026-09-28 - "In Material Transfer of Issue Yarn from Weaving Contract,
# create a field of Weaver (Linked to supplier, fetch from weaving
# contract), Weaving Contract Ref ..., Driver Name (Linked to Driver
# Doctype), Vehicle No (Linked to Vehicle Doctype) and Remarks (Data)"
# (your words).
#
# Stock Entry already has "weaver" (Link Customer - wrong target, fixed
# below), "weaving_contract" (already correct), "driver_name" and
# "vehicle_no" (both plain Data - now converted to Link) from emadi_v3_abdullah and
# mjfsd_v3_abdullah's existing custom/stock_entry.json fixtures. Rather than trust
# that fixture-sync (already shown unreliable on this bench - see the
# Weaving Contract layout / Sales Order Item GSM fixes) to pick up these
# changes, this force-creates/updates them directly via Frappe's Custom
# Field API, same pattern as garments_app_v3_abdullah's
# force_create_v3_custom_fields patch. Safe to re-run (update=True).
#
# Depends on the standard ERPNext Driver and Vehicle doctypes being
# installed (HR / Fleet Management) - if your bench doesn't have them,
# tell me and I'll point Driver Name / Vehicle No at something else.


def execute():
	create_custom_fields(
		{
			"Stock Entry": [
				{
					"fieldname": "weaver",
					"fieldtype": "Link",
					"label": "Weaver",
					"options": "Supplier",
					"insert_after": "weaving_contract",
				},
				{
					"fieldname": "driver_name",
					"fieldtype": "Link",
					"label": "Driver Name",
					"options": "Driver",
					"insert_after": "transporter_detail",
				},
				{
					"fieldname": "vehicle_no",
					"fieldtype": "Link",
					"label": "Vehicle No",
					"options": "Vehicle",
					"insert_after": "driver_contact_no",
				},
				{
					"fieldname": "custom_remarks",
					"fieldtype": "Data",
					"label": "Remarks",
					"insert_after": "vehicle_no",
				},
			]
		},
		update=True,
	)
