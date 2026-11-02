import frappe


def get_attendance_dashboard(data: dict) -> dict:
	"""Show Leave Application, Attendance Request, Employee Checkin and Attendance
	Regularization in Attendance connections.

	Reads the link fields available on the Attendance document:
	- employee_checkin -> Employee Checkin
	- leave_application -> Leave Application
	- attendance_request -> Attendance Request
	- attendance_regularization -> Attendance Regularization
	"""
	data = frappe._dict(data)

	data.setdefault("internal_and_external_links", {})
	data["internal_and_external_links"].update(
		{
			"Employee Checkin": "employee_checkin",
			"Leave Application": "leave_application",
			"Attendance Request": "attendance_request",
			"Attendance Regularization": "attendance_regularization",
		}
	)

	items_to_add = ("Leave Application", "Attendance Request", "Attendance Regularization")
	transactions = data.setdefault("transactions", [])

	if transactions:
		items = transactions[0].setdefault("items", [])
		for doctype in items_to_add:
			if doctype not in items:
				items.append(doctype)
	else:
		transactions.append({"label": "", "items": list(items_to_add)})

	return data
