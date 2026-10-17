frappe.ui.form.on('Sales Invoice', {
    cost_center: function(frm) {
        // When the header cost_center changes
        if (frm.doc.items && frm.doc.items.length) {
            frm.doc.items.forEach(function(item) {
                // set the child row’s cost_center
                frappe.model.set_value(item.doctype, item.name, 'cost_center', frm.doc.cost_center);
            });
            frm.refresh_field('items');
        }
    }
});
