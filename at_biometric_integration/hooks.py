app_name = "at_biometric_integration"
app_title = "At Biometric Integration"
app_publisher = "Assimilate Technologies"
app_description = "Frappe App For Sync Attendance from Biometric device"
app_email = "info@assimilatetechnologies.com"
app_license = "mit"

# Apps
# -----------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "at_biometric_integration",
# 		"logo": "/assets/at_biometric_integration/logo.png",
# 		"title": "At Biometric Integration",
# 		"route": "/at_biometric_integration",
# 		"has_permission": "at_biometric_integration.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/at_biometric_integration/css/at_biometric_integration.css"
# app_include_js = [
#     "/assets/at_biometric_integration/js/employee_checkin.js"
# ]

# include js, css files in header of web template
# web_include_css = "/assets/at_biometric_integration/css/at_biometric_integration.css"
# web_include_js = "/assets/at_biometric_integration/js/at_biometric_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "at_biometric_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_list_js = {
    "Employee Checkin": [
        "public/js/employee_checkin.js"
    ],
    "Employee": [
        "public/js/employee.js"
    ]
}


# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "at_biometric_integration/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "at_biometric_integration.utils.jinja_methods",
# 	"filters": "at_biometric_integration.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "at_biometric_integration.install.before_install"
# after_install = "at_biometric_integration.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "at_biometric_integration.uninstall.before_uninstall"
# after_uninstall = "at_biometric_integration.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "at_biometric_integration.utils.before_app_install"
# after_app_install = "at_biometric_integration.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "at_biometric_integration.utils.before_app_uninstall"
# after_app_uninstall = "at_biometric_integration.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "at_biometric_integration.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"at_biometric_integration.tasks.all"
# 	],
# 	"daily": [
# 		"at_biometric_integration.tasks.daily"
# 	],
# 	"hourly": [
# 		"at_biometric_integration.tasks.hourly"
# 	],
# 	"weekly": [
# 		"at_biometric_integration.tasks.weekly"
# 	],
# 	"monthly": [
# 		"at_biometric_integration.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "at_biometric_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#   "sync_biometric_attendance": "at_biometric_integration.api.trigger_biometric_sync"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "at_biometric_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["at_biometric_integration.utils.before_request"]
# after_request = ["at_biometric_integration.utils.after_request"]

# Job Events
# ----------
# before_job = ["at_biometric_integration.utils.before_job"]
# after_job = ["at_biometric_integration.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"at_biometric_integration.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# scheduler_events for hooks
scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "at_biometric_integration.api.fetch_and_upload_attendance"
        ],
        "*/5 * * * *": [
            "at_biometric_integration.scheduler.run_attendance_scheduler"
        ],
        "*/10 * * * *": [
            "at_biometric_integration.utils.attendance_processing.auto_submit_due_attendances"
        ],
        # "*/10 * * * *": [
        #     "at_biometric_integration.api.mark_attendance"
        # ]
    },
    "hourly": [
        "at_biometric_integration.api.mark_attendance"
    ],
    "daily": [
        "at_biometric_integration.utils.cleanup.cleanup_old_attendance_logs"
    ]
}


# scheduler_events = {
#     "cron": {
#         "*/16 * * * *": [
#             "at_biometric_integration.utils.fetch_and_upload_attendance",
#             "at_biometric_integration.utils.process_attendance"
#         ]
#     },
#     "daily": [
#           "at_biometric_integration.utils.fetch_and_upload_attendance",
#         #   "at_biometric_integration.at_biometric_integration.doctype.attendance_regularization.attendance_regularization.check_missing_checkins",
#           "at_biometric_integration.utils.mark_daily_attendance"
#     ]
# }

fixtures = [
    {
        "doctype": "Workflow",
        "filters": [["workflow_name", "=", "Attendance Regularization Approval"]]
    }
    # ,
    # { 
    #  "doctype": "Workspace",
    #  "filters": [["name", "=", "Biometric Workspace"]]
    # }
    
]
after_migrate = ["at_biometric_integration.patches.workflow_state_action.execute","at_biometric_integration.patches.create_biometric_roles_and_permissions.execute"]

