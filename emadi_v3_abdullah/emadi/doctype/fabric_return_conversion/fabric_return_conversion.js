// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fabric Return Conversion', {
	refresh: function(frm) {
        frm.set_query('target_warehouse', function() {
            return {
                "filters": [
					["is_group", "=", 0 ]
				]
            };
        });
        
		frm.set_query('yarn_count','fabric_return_conversion_item', function() {
			return {
				"filters": [
					["item_group", "in", ["Yarn","Beam"]]
				]
			}
		});
        frm.set_query('set_no','fabric_return_conversion_item', function() {
            return {
                "filters": [
                    ["item", "=", frm.doc.yarn_count]
                ]
            }
        })
        frm.set_query('set_no', 'fabric_return_conversion_item', function(doc, cdt, cdn) {
			let child = locals[cdt][cdn];
			return {
				filters: {
					item: child.yarn_count
				}
			};
		});
	},
	weaving_contract: function(frm) {
        if (frm.doc.qty) {
            frappe.call({
                method: "emadi_v3_abdullah.emadi.events.fetch_weaving_contract_items.fetch_weaving_contract_items",
                args: {
                    weaving_contract: frm.doc.weaving_contract,
                    qty: frm.doc.qty
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table("fabric_return_conversion_item");
                        $.each(r.message, function(_, item) {
                            let row = frm.add_child("fabric_return_conversion_item");
                            row.for = item.for;
                            row.yarn_count = item.yarn_count;
                            row.consumption = item.consumption;
                            row.uom = item.uom;
                            row.brand = item.brand;
                            row.yarn_qty = item.yarn_qty;
                        });
                        frm.refresh_field("fabric_return_conversion_item");
                    }
                }
            });
        }
    },
    qty: function(frm) {
        // Recalculate when qty changes
        frm.trigger("weaving_contract");
    }
});

frappe.ui.form.on('Fabric Return Conversion Item', {
    
    warehouse(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        // Only proceed if essential fields are present
       
        frm.call({
            method: 'emadi_v3_abdullah.emadi.events.fetch_current_stock.fetch_current_stock',
            args: {
                item_code: row.yarn_count,
                warehouse: row.warehouse
            },
            callback: ({ message }) => {
                const available = message?.current_stock || 0;
                const rate = message?.rate || 0;
                const yarnQty = row.yarn_qty || 0;
            

                frappe.model.set_value(cdt, cdn, 'available_qty', available);
                frappe.model.set_value(cdt, cdn, 'valuation_rate', rate);
                frappe.model.set_value(cdt, cdn, 'rate_per_meter', row.consumption * rate);

                recalculate_rate(frm);
            },
            error: err => {
                frappe.msgprint({
                    title: __('Stock Fetch Error'),
                    message: __('Could not load stock data for row {0}', [row.idx]),
                    indicator: 'red'
                });
            }
        });
    },
    yarn_count: function(frm) {
        // Recalculate when qty changes
        row.trigger("warehouse");
    }
})


// Shared logic to total up amounts and calculate rate
function recalculate_rate(frm) {
    const items = frm.doc.fabric_return_conversion_item || [];
    let warp_rate = 0;
    let weft_rate = 0;
   items.forEach(element => {
    if (element['for'] === "Warp") {
        warp_rate += flt(element.valuation_rate);
    } else if (element['for'] === "Weft") {
        weft_rate += flt(element.rate_per_meter);
    }
    
   });

    
  }
  
  