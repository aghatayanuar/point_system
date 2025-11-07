frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
        frm.set_df_property("custom_redeem_amount", "read_only", 1);
    },

    custom_redeem_point: function(frm) {
        if(frm.doc.custom_redeem_point) {
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Point System Settings",
                    name: "Point System Settings"
                },
                callback: function(r) {
                    let conversion_rate = r.message.conversion_rate || 0;
                    let redeem_amount = frm.doc.custom_redeem_point * conversion_rate;

                    frm.set_value("custom_redeem_amount", redeem_amount);

                    frm.set_value("discount_amount", redeem_amount);
                    frm.refresh_field("discount_amount");
                }
            });
        } else {
            frm.set_value("custom_redeem_amount", 0);
            frm.set_value("discount_amount", 0);
            frm.refresh_field("discount_amount");
        }
    }
});
