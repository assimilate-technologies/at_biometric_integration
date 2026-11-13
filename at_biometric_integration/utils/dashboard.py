import frappe


def get_attendance_dashboard(data: dict) -> dict:
	"""Show Leave Application, Attendance Request, Employee Checkin and Attendance
	Regularization in Attendance connections.

	employee_checkin is now a Table field (child doctype 'checkin') with a Link
	field 'checkin' pointing to Employee Checkin.  Frappe resolves child-table
	links via internal_links: {"DocType": ["child_table_fieldname", "link_field"]}.

	Direct Link fields on Attendance:
	- leave_application -> Leave Application
	- attendance_request -> Attendance Request
	- attendance_regularization -> Attendance Regularization
	"""
	data = frappe._dict(data)

	# ----- internal_and_external_links (direct Link fields) -----
	data.setdefault("internal_and_external_links", {})
	data["internal_and_external_links"].update(
		{
			"Leave Application": "leave_application",
			"Attendance Request": "attendance_request",
			"Attendance Regularization": "attendance_regularization",
		}
	)

	# ----- non_standard_fieldnames (for clicking badge to open list) -----
	data.setdefault("non_standard_fieldnames", {})
	data["non_standard_fieldnames"]["Employee Checkin"] = "attendance"

	# ----- internal_links (child-table based links) -----
	# employee_checkin = Table field (parentfield), checkin = Link field inside child row
	data.setdefault("internal_links", {})
	data["internal_links"].update(
		{
			"Employee Checkin": ["employee_checkin", "checkin"],
		}
	)

	# ----- transactions (items shown in Connections tab) -----
	items_to_add = ("Employee Checkin", "Leave Application", "Attendance Request", "Attendance Regularization")
	transactions = data.setdefault("transactions", [])

	if transactions:
		items = transactions[0].setdefault("items", [])
		for doctype in items_to_add:
			if doctype not in items:
				items.append(doctype)
	else:
		transactions.append({"label": "", "items": list(items_to_add)})

	return data
