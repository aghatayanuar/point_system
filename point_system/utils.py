import frappe

from frappe.utils import flt, nowdate


def after_install():
    create_sales_invoice_custom_fields()

def create_sales_invoice_custom_fields():
    custom_fields = {
        "Sales Invoice": [
            dict(fieldname="custom_redeem_point", label="Redeem Point", fieldtype="Float", default=0),
            dict(fieldname="custom_redeem_amount", label="Redeem Amount", fieldtype="Currency", read_only=1, default=0),
        ]
    }

    for doctype, fields in custom_fields.items():
        for field in fields:
            if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}):
                cf = frappe.get_doc({
                    "doctype": "Custom Field",
                    "dt": doctype,
                    "label": field["label"],
                    "fieldname": field["fieldname"],
                    "fieldtype": field["fieldtype"],
                    "insert_after": "discount_amount",
                    "read_only": field.get("read_only", 0),
                    "owner": "Administrator"
                })
                cf.insert(ignore_permissions=True)
                print(f"Custom Field '{field['label']}' ditambahkan ke {doctype}")
            else:
                print(f"Custom Field '{field['label']}' sudah ada di {doctype}")

    frappe.db.commit()


@frappe.whitelist()
def get_conversion_rate():
    settings = frappe.get_single("Point System Settings")
    return settings.conversion_rate or 0

def validate_redeem_points(doc, method):
    if doc.custom_redeem_point and doc.custom_redeem_point > 0:
        result = frappe.db.sql("""
            SELECT COALESCE(SUM(point_in) - SUM(point_out), 0)
            FROM `tabPoint Ledger`
            WHERE customer = %s
        """, doc.customer)
        balance = result[0][0] if result else 0

        if doc.custom_redeem_point > balance:
            frappe.throw(f"Customer '{doc.customer}' tidak punya cukup poin. Saldo: {balance}")

def submit_redeem_points(doc, method):
    if doc.custom_redeem_point and doc.custom_redeem_point > 0:
        reduce_point = frappe.get_doc({
            "doctype": "Reduce Point",
            "customer": doc.customer,
            "point": doc.custom_redeem_point,
            "reason": f"Redeem from Sales Invoice {doc.name}",
            "date": doc.posting_date
        })
        reduce_point.insert()
        reduce_point.submit()

def cancel_redeem_points(doc, method):
    if doc.custom_redeem_point and doc.custom_redeem_point > 0:
        rp_list = frappe.get_all("Reduce Point",
            filters={"reason": f"Redeem from Sales Invoice {doc.name}"},
            fields=["name"])
        for rp in rp_list:
            rp_doc = frappe.get_doc("Reduce Point", rp.name)
            rp_doc.cancel()
