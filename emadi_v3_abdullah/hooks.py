from . import __version__ as app_version

app_name = "emadi_v3_abdullah"
app_title = "Emadi V3 Abdullah"
app_publisher = "Safdar Ali"
app_description = "this is app for emadi weaving (v3)"
app_email = "safdar211@gmail.com"
app_license = "mit"


# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/emadi_v3_abdullah/css/emadi_v3_abdullah.css"
# app_include_js = "/assets/emadi_v3_abdullah/js/emadi_v3_abdullah.js"

# include js, css files in header of web template
# web_include_css = "/assets/emadi_v3_abdullah/css/emadi_v3_abdullah.css"
# web_include_js = "/assets/emadi_v3_abdullah/js/emadi_v3_abdullah.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "emadi_v3_abdullah/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Delivery Note" : "public/js/dn.js","Stock Entry" : "public/js/stock_entry.js",
"Sales Invoice" : "public/js/sales_invoice.js",
"Material Request" : "public/js/material_request.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "emadi_v3_abdullah.utils.jinja_methods",
#	"filters": "emadi_v3_abdullah.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "emadi_v3_abdullah.install.before_install"
# after_install = "emadi_v3_abdullah.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "emadi_v3_abdullah.uninstall.before_uninstall"
# after_uninstall = "emadi_v3_abdullah.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "emadi_v3_abdullah.utils.before_app_install"
# after_app_install = "emadi_v3_abdullah.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "emadi_v3_abdullah.utils.before_app_uninstall"
# after_app_uninstall = "emadi_v3_abdullah.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "emadi_v3_abdullah.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Delivery Note": {
        "validate": "emadi_v3_abdullah.emadiv3.events.dn_weaving_contract.validate",
        "on_submit": "emadi_v3_abdullah.emadiv3.events.create_dn.onsubmit"
    },
    "Stock Entry": {
        "before_validate": "emadi_v3_abdullah.emadiv3.events.stock_entry_weaving_contract.before_validate"
    },
    "Material Request": {
        "validate": "emadi_v3_abdullah.emadiv3.events.customer_yarn_material_request.validate"
    },
    # "Fabric Construction": {
    #     "on_update": "emadi_v3_abdullah.emadiv3.events.sync_item_enabled.sync_item_enabled"
    # }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"emadi_v3_abdullah.tasks.all"
#	],
#	"daily": [
#		"emadi_v3_abdullah.tasks.daily"
#	],
#	"hourly": [
#		"emadi_v3_abdullah.tasks.hourly"
#	],
#	"weekly": [
#		"emadi_v3_abdullah.tasks.weekly"
#	],
#	"monthly": [
#		"emadi_v3_abdullah.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "emadi_v3_abdullah.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "emadi_v3_abdullah.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "emadi_v3_abdullah.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["emadi_v3_abdullah.utils.before_request"]
# after_request = ["emadi_v3_abdullah.utils.after_request"]

# Job Events
# ----------
# before_job = ["emadi_v3_abdullah.utils.before_job"]
# after_job = ["emadi_v3_abdullah.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"emadi_v3_abdullah.auth.validate"
# ]
