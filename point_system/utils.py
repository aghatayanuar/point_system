import frappe

from frappe.utils import flt, nowdate


def after_install():
    create_sales_invoice_custom_fields()
    hide_loyalty_section()
    set_loyalty_restricted_permissions()

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
            "date": doc.posting_date,
            "reference_sales_invoice": doc.name 
        })
        reduce_point.insert()
        reduce_point.submit()

def cancel_redeem_points(doc, method):
    if doc.custom_redeem_point and doc.custom_redeem_point > 0:
        rp_list = frappe.get_all(
            "Reduce Point",
            filters={"reference_sales_invoice": doc.name},
            fields=["name", "docstatus"]
        )
        for rp in rp_list:
            rp_doc = frappe.get_doc("Reduce Point", rp.name)
            if rp_doc.docstatus == 1:
                rp_doc.cancel()

def hide_loyalty_section():
    try:
        ps = frappe.get_all(
            "Property Setter",
            filters={
                "doc_type": "Sales Invoice",
                "field_name": "loyalty_points_redemption",
                "property": "hidden"
            },
            fields=["name"]
        )

        if ps:
            print("Property Setter untuk hide section 'loyalty_points_redemption' sudah ada.")
        else:
            doc = frappe.get_doc({
                "doctype": "Property Setter",
                "doc_type": "Sales Invoice",
                "field_name": "loyalty_points_redemption",
                "property": "hidden",
                "value": 1,
                "property_type": "Check",
                "doctype_or_field": "DocField"  
            })
            doc.insert(ignore_permissions=True)
            print("Section 'Loyalty Points Redemption' di-hide via Property Setter.")

        frappe.clear_cache(doctype="Sales Invoice")

    except Exception as e:
        frappe.log_error(message=str(e), title="Error hide Section 'Loyalty Points Redemption'")
        print("Gagal hide Section 'Loyalty Points Redemption'.")

def set_loyalty_restricted_permissions():
    
    role_name = "Loyalty Restricted"
    doctypes = ["Loyalty Program", "Loyalty Point Entry"]

    if not frappe.db.exists("Role", role_name):
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name})
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Role '{role_name}' dibuat")

    for dt in doctypes:
        frappe.db.sql(
            """
            DELETE FROM `tabCustom DocPerm`
            WHERE parent=%s AND role=%s
            """,
            (dt, role_name),
        )

        frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": dt,
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": role_name,
            "read": 0,
            "write": 0,
            "create": 0,
            "delete": 0,
        }).insert(ignore_permissions=True)

    frappe.db.commit()
    print("Permissions untuk 'Loyalty Restricted' di-set")

    users = frappe.get_all("User", filters={"enabled": 1, "name": ("!=","Guest")})
    for u in users:
        try:
            if role_name not in frappe.get_roles(u.name):
                frappe.get_doc("User", u.name).add_roles(role_name)
        except Exception as e:
            frappe.log_error(f"Error assign {role_name} ke {u.name}: {str(e)}")

    frappe.db.commit()
    print(f"Role '{role_name}' diassign ke semua user aktif")
