frappe.ui.form.on('Material Request', {
    items_remove: function(frm) {
        set_total_bags(frm);
    }
});

frappe.ui.form.on('Material Request Item', {
    qty: function(frm, cdt, cdn) {
        set_total_bags(frm);
    }
});

// custom_total_bags = qty / 100 per row; total qty / 100 on the parent
function set_total_bags(frm) {
    let total_qty = 0;
    (frm.doc.items || []).forEach(function(row) {
        total_qty += flt(row.qty);
        frappe.model.set_value(row.doctype, row.name, "custom_total_bags", flt(row.qty) / 100);
    });
    frm.set_value("custom_total_bags", total_qty / 100);
}
