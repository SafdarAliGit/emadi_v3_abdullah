// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Fabric Production Out Side', {
	refresh: function(frm) {
        frm.set_query('target_warehouse', function() {
            return {
                "filters": [
					["is_group", "=", 0 ]
				]
            };
        });
        
		frm.set_query('yarn_count','fabric_production_out_side_item', function() {
			return {
				"filters": [
					["item_group", "in", ["Yarn","Beam"]]
				]
			}
		});
        frm.set_query('set_no','fabric_production_out_side_item', function() {
            return {
                "filters": [
                    ["item", "=", frm.doc.yarn_count]
                ]
            }
        })
        frm.set_query('set_no', 'fabric_production_out_side_item', function(doc, cdt, cdn) {
			let child = locals[cdt][cdn];
			return {
				filters: {
					item: child.yarn_count
				}
			};
		});
	},
    weaving_charges_per_meter: function(frm, cdt, cdn) {
        weaving_charges_per_meter(frm, cdt, cdn)
        fabric_rate_per_meter(frm, cdt, cdn);
    },
	quality: function(frm) {
        if (frm.doc.quality && frm.doc.qty) {
            frappe.call({
                method: "emadi_v3_abdullah.emadiv3.events.fetch_fabric_construction_items.fetch_fabric_construction_items",
                args: {
                    quality: frm.doc.quality,
                    qty: frm.doc.qty
                },
                callback: function(r) {
                    if (r.message) {
                        frm.clear_table("fabric_production_out_side_item");
                        $.each(r.message, function(_, item) {
                            let row = frm.add_child("fabric_production_out_side_item");
                            row.for = item.for;
                            row.yarn_count = item.yarn_count;
                            row.consumption = item.consumption;
                            row.yarn_qty = item.yarn_qty;
                        });
                        frm.refresh_field("fabric_production_out_side_item");
                    }
                }
            });
        }
    },
    qty: function(frm,cdt,cdn) {
        // Recalculate when qty changes
        frm.trigger("quality");
        weaving_charges_per_meter(frm, cdt, cdn)
        total_charges_per_meter(frm,cdt,cdn);
        fabric_rate_per_meter(frm, cdt, cdn);
    }
});

frappe.ui.form.on('Fabric Production Out Side Item', {
    
    warehouse(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        // Only proceed if essential fields are present
       
        frm.call({
            method: 'emadi_v3_abdullah.emadiv3.events.fetch_current_stock.fetch_current_stock',
            args: {
                item_code: row.yarn_count,
                warehouse: row.warehouse,
                posting_date: frm.doc.posting_date
                
            },
            callback: ({ message }) => {
                const available = message?.current_stock || 0;
                const rate = message?.rate || 0;
                const yarnQty = row.yarn_qty || 0;
            

                frappe.model.set_value(cdt, cdn, 'available_qty', available);
                frappe.model.set_value(cdt, cdn, 'valuation_rate', rate);
                frappe.model.set_value(cdt, cdn, 'rate_per_meter', row.consumption * rate);
                frappe.model.set_value(cdt, cdn, 'amount', rate * yarnQty);

                recalculate_rate(frm);
                fabric_rate_per_meter(frm, cdt, cdn);
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
    const items = frm.doc.fabric_production_out_side_item || [];
    let warp_rate = 0;
    let weft_rate = 0;
   items.forEach(element => {
    if (element['for'] === "Warp") {
        warp_rate += flt(element.rate_per_meter);
    } else if (element['for'] === "Weft") {
        weft_rate += flt(element.rate_per_meter);
    }
    
   });

    let avg_rate = 0;
 
      avg_rate = warp_rate + weft_rate;
      frm.set_value('warp_rate', warp_rate);
      frm.set_value('weft_rate', weft_rate);
      frm.set_value('finish_rate', avg_rate);
    
    
    if (frm.doc.valuation_type === 0 && avg_rate <= 0) {
      frappe.throw(__('Rate must be greater than zero'));
    }
  }
frappe.ui.form.on('Fabric Production Other Charges Item', {
    amount: function (frm, cdt, cdn) {
        total_charges_per_meter(frm, cdt, cdn);
        fabric_rate_per_meter(frm, cdt, cdn);
    }
});


    function total_charges_per_meter(frm, cdt, cdn) {
        let total_charges_per_meter = 0;
        let qty = frm.doc.qty || 1;

        // Ensure child table exists
        if (frm.doc.fabric_production_other_charges_item) {
            frm.doc.fabric_production_other_charges_item.forEach(row => {
                total_charges_per_meter += flt(row.amount);
            });
        }

        // Avoid divide by zero
        let per_meter = qty ? (total_charges_per_meter / qty) : 0;

        frm.set_value('total_charges_per_meter', per_meter);
    }

    function weaving_charges_per_meter(frm, cdt, cdn) {
        var weaving_charges_per_meter = frm.doc.weaving_charges_per_meter;
        var qty = frm.doc.qty || 0;
        var amount = weaving_charges_per_meter * qty;
        frm.set_value("amount", amount);
    }

    function fabric_rate_per_meter(frm, cdt, cdn) {
        var weaving_charges_per_meter = frm.doc.weaving_charges_per_meter || 0;
        var finish_rate = frm.doc.finish_rate || 0;
        var total_charges_per_meter = frm.doc.total_charges_per_meter || 0;
        
        var fabric_rate_per_meter = weaving_charges_per_meter + finish_rate + total_charges_per_meter;
        frm.set_value("fabric_rate_per_meter", fabric_rate_per_meter);
    }
