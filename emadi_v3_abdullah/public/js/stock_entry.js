frappe.ui.form.on('Stock Entry', {
    refresh: function(frm) {
        // calculate_total_qty(frm)
    }
});


function calculate_total_qty(frm) {
    let total_qty = 0;
    
    $.each(frm.doc.items || [], function(_, row) {
        total_qty += row.qty || 0;
    });

    frm.set_value('total_qty', total_qty);
}