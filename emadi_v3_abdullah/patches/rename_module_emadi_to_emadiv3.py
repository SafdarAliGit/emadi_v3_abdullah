import frappe


def execute():
	"""Rename this app's Module Def "Emadi" to "Emadiv3" on sites installed before the rename."""
	if frappe.db.exists("Module Def", "Emadiv3"):
		return

	if frappe.db.get_value("Module Def", "Emadi", "app_name") == "emadi_v3_abdullah":
		frappe.rename_doc("Module Def", "Emadi", "Emadiv3", force=True)
	else:
		frappe.get_doc(
			{"doctype": "Module Def", "module_name": "Emadiv3", "app_name": "emadi_v3_abdullah"}
		).insert(ignore_permissions=True)
