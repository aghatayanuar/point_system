# Copyright (c) 2025, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class AddPoint(Document):
    def validate(self):
        if self.point <= 0:
            frappe.throw("Point harus lebih dari 0")

    def get_current_balance(self):
        result = frappe.db.sql("""
            SELECT COALESCE(SUM(point_in) - SUM(point_out), 0)
            FROM `tabPoint Ledger`
            WHERE customer = %s
        """, self.customer)
        return result[0][0] if result else 0

    def on_submit(self):
        balance = self.get_current_balance()
        new_balance = balance + self.point

        ledger_entry = frappe.get_doc({
            "doctype": "Point Ledger",
            "date": self.date,
            "customer": self.customer,
            "reference_doctype": "Add Point",
            "reference_name": self.name,
            "point_in": self.point,
            "point_out": 0,
            "balance_after_transaction": new_balance,
            "remarks": self.reason,
            "is_cancel": 0
        })
        ledger_entry.insert()
        frappe.db.commit()

    def on_cancel(self):
        balance = self.get_current_balance()
        new_balance = balance - self.point

        ledger_entry = frappe.get_doc({
            "doctype": "Point Ledger",
            "date": nowdate(),
            "customer": self.customer,
            "reference_doctype": "Add Point",
            "reference_name": self.name,
            "point_in": 0,
            "point_out": self.point,
            "balance_after_transaction": new_balance,
            "remarks": f"Cancel: {self.reason}",
            "is_cancel": 1
        })
        ledger_entry.insert()
        frappe.db.commit()
