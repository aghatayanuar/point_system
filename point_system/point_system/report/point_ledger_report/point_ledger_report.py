import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Point In"), "fieldname": "point_in", "fieldtype": "Float", "width": 100},
        {"label": _("Point Out"), "fieldname": "point_out", "fieldtype": "Float", "width": 100},
        {"label": _("Balance After Transaction"), "fieldname": "balance_after_transaction", "fieldtype": "Float", "width": 180},
        {"label": _("Reference Doctype"), "fieldname": "reference_doctype", "fieldtype": "Data", "width": 180},
        {
            "label": _("Reference Name"),
            "fieldname": "reference_name",
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 180,
        },
        {
            "label": _("Reference Sales Invoice"),
            "fieldname": "reference_sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 200,
        },
        {"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 250},
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        values["customer"] = filters["customer"]

    condition_str = " and ".join(conditions)
    if condition_str:
        condition_str = " where " + condition_str

    query = f"""
        select
            date,
            customer,
            point_in,
            point_out,
            balance_after_transaction,
            reference_doctype,
            reference_name,
            remarks
        from
            `tabPoint Ledger`
        {condition_str}
        order by date asc
    """

    data = frappe.db.sql(query, values, as_dict=True)

    for row in data:
        if row.reference_doctype == "Reduce Point" and row.reference_name:
            row.reference_sales_invoice = frappe.db.get_value(
                "Reduce Point",
                row.reference_name,
                "reference_sales_invoice"
            )
        else:
            row.reference_sales_invoice = None

    return data
