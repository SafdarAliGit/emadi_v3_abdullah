frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Fetch Items from Weaving Contract'), function() {
                fetch_items_from_weaving_contract(frm);
            });
        }
    },
    fabric_qty: function(frm) {
        if (frm.doc.custom_non_conversion==0) {
            if (frm.doc.fabric_qty) {
            $.each(frm.doc.items || [], function(index, row) {
                frappe.model.set_value(row.doctype, row.name, "qty", frm.doc.fabric_qty);
            });
            frm.refresh_field("items");

            $.each(frm.doc.bom_items_dn|| [], function(index, row) {
                frappe.model.set_value(row.doctype, row.name, "yarn_qty", frm.doc.fabric_qty * row.consumption);
            });
            frm.refresh_field("bom_items_dn");
        }
        }
        
    },
    // fabric_item: function(frm) {
    //     // When the fabric_item is changed, fetch the item doc
    //     if (frm.doc.fabric_item) {
    //         frappe.db.get_doc("Item", frm.doc.fabric_item)
    //             .then(item_doc => {
    //                 // Check the custom field and set custom_non_conversion accordingly
    //                 if (item_doc.custom_conversion === 1) {
    //                     frm.set_value("custom_non_conversion", 1);
    //                 } else {
    //                     frm.set_value("custom_non_conversion", 0);
    //                 }
    //             });
    //     } else {
    //         // No item selected, default
    //         frm.set_value("custom_non_conversion", 0);
    //     }
    // }
});

frappe.ui.form.on('BOM Items Dn', {
    ratio: function(frm) {
        update_bom_yarn_qty(frm);
    },
    weaving_wastage: function(frm) {
        update_bom_yarn_qty(frm);
    }
});

frappe.ui.form.on('Delivery Note Item', {
    custom_weight_kg: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, "custom_weight_lbs", flt(row.custom_weight_kg) * 2.2046);
    },
    custom_weight_lbs: function(frm) {
        update_bom_yarn_qty(frm);
    },
    stock_qty: function(frm, cdt, cdn) {
        set_pieces(cdt, cdn);
    },
    qty: function(frm, cdt, cdn) {
        set_pieces(cdt, cdn);
    },
    conversion_factor: function(frm, cdt, cdn) {
        set_pieces(cdt, cdn);
    },
    items_remove: function(frm) {
        update_bom_yarn_qty(frm);
    }
});

// Pieces = Qty as per Stock UOM
function set_pieces(cdt, cdn) {
    let row = locals[cdt][cdn];
    let pieces = flt(row.stock_qty) || flt(row.qty) * (flt(row.conversion_factor) || 1);
    frappe.model.set_value(cdt, cdn, "custom_pieces", pieces);
}

// Yarn Qty = Weight LBS of the matching Delivery Note Item row(s) * Ratio % * (1 + Weaving Wastage %)
function update_bom_yarn_qty(frm) {
    (frm.doc.bom_items_dn || []).forEach(function(bom) {
        if (!(flt(bom.ratio) && bom.fabric_item && bom.weaving_contract)) {
            return;
        }
        let lbs = 0;
        (frm.doc.items || []).forEach(function(item) {
            if (item.item_code === bom.fabric_item && item.custom_weaving_contract_reference === bom.weaving_contract) {
                lbs += flt(item.custom_weight_lbs);
            }
        });
        let yarn_qty = lbs * flt(bom.ratio) / 100 * (1 + flt(bom.weaving_wastage) / 100);
        if (flt(bom.yarn_qty) !== yarn_qty) {
            frappe.model.set_value(bom.doctype, bom.name, "yarn_qty", yarn_qty);
        }
    });
}

function fetch_items_from_weaving_contract(frm) {
    new frappe.ui.form.MultiSelectDialog({
        doctype: "Weaving Contract",
        target: frm,
        setters: {
            weaver: null,
            construction: null
        },
        add_filters_group: 1,
        primary_action_label: __("Fetch"),
        get_query: function() {
            return { filters: { docstatus: 1 } };
        },
        action: function(selections) {
            if (!selections || !selections.length) {
                return;
            }
            frappe.call({
                method: "emadi_v3_abdullah.emadiv3.events.dn_weaving_contract.get_weaving_contract_dn_data",
                args: { weaving_contracts: selections },
                freeze: true,
                callback: function(r) {
                    add_weaving_contract_rows(frm, r.message || []);
                }
            });
            cur_dialog && cur_dialog.hide();
        }
    });
}

function add_weaving_contract_rows(frm, contracts) {
    // The fabric is delivered straight from the items table, so the extra
    // "Fabric Delivered" Stock Entry (header Fabric Item/Qty) must not run.
    frm.set_value("custom_non_conversion", 1);
    // drop the empty starter row, if that's all there is
    if ((frm.doc.items || []).length === 1 && !frm.doc.items[0].item_code) {
        frm.clear_table("items");
    }
    let already = (frm.doc.items || []).map(d => d.custom_weaving_contract_reference);

    contracts.forEach(function(c) {
        if (already.includes(c.weaving_contract)) {
            frappe.show_alert({ message: __("{0} is already in the items table", [c.weaving_contract]), indicator: "orange" });
            return;
        }
        let row = frm.add_child("items");
        row.custom_weaving_contract_reference = c.weaving_contract;
        frappe.model.set_value(row.doctype, row.name, "item_code", c.construction);

        (c.bom_items || []).forEach(function(b) {
            let bom = frm.add_child("bom_items_dn");
            bom.for = b.for;
            bom.yarn_count = b.yarn_count;
            bom.ratio = b.ratio;
            bom.weaving_wastage = b.weaving_wastage;
            bom.uom = b.uom;
            bom.brand = b.brand;
            bom.fabric_item = c.construction;
            bom.weaving_contract = c.weaving_contract;
            bom.yarn_qty = 0;
        });
    });
    frm.refresh_field("items");
    frm.refresh_field("bom_items_dn");
}
