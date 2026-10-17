// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Weaving Contract', {
	refresh: function(frm) {

		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Sales Order'), function() {
				get_items_from_sales_order(frm)
			}, __('Get Items From'))
		}

		// 2026-09-16 - "same workflow like issue fabric in dyeing contract
		// is needed in Weaving Contract named 'Issue Yarn'" (your words).
		// Shown purely on docstatus, same as Issue Fabric on Dyeing
		// Contract (which has no Type/status gate either) - not
		// restricted to Internal/Outsourced or to custom_status == Open;
		// flag if you actually want it narrower.
		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__('Issue Yarn'), function() {
				open_issue_yarn_dialog(frm)
			});
			sync_yarn_issued_totals(frm);
		}

		if (frm.doc.docstatus == 1 && frm.doc.custom_status == "Close") {
			frm.add_custom_button(__('OPEN'), function() {

						frappe.call({
							method: "emadi_v3_abdullah.emadi.events.open_weaving_contract.open_weaving_contract",
							args: {
								weaving_contract: frm.doc.name
							},
							callback: function(r) {
								if (!r.exc) {
									frappe.model.sync(r.message);
									frappe.set_route("Form", r.message.doctype, r.message.name);
								}
							}
						});


			}).css('background-color', 'green')
			  .css('color', '#ffffff')
			  .css('font-weight', 'bold');
		}

		if (frm.doc.docstatus == 1 && frm.doc.custom_status == "Open") {
			frm.add_custom_button(__('CLOSE'), function() {
				frappe.confirm(
					'Are you sure you want to CLOSE this weaving contract?',
					function() {
						// OK pressed
						frappe.call({
							method: "emadi_v3_abdullah.emadi.events.close_weaving_contract.close_weaving_contract",
							args: {
								weaving_contract: frm.doc.name
							},
							callback: function(r) {
								if (!r.exc) {
									frappe.model.sync(r.message);
									frappe.set_route("Form", r.message.doctype, r.message.name);
								}
							}
						});
					},
					function() {
						// Cancel pressed - do nothing
					}
				);
			}).css('background-color', 'red')
			  .css('color', '#ffffff')
			  .css('font-weight', 'bold');
		}

		// 2026-09-15 (feature v3) - "In Weaving Contract, remove other
		// buttons and only display 2 buttons; Weaving Receipt, Sizing
		// Program" (your words). Fabric Return Conversion / Create DO /
		// the old "Stock Entry" button / Material Request are gone.
		// Sizing Program only shows when Type is Internal, Weaving Receipt
		// only when Type is Outsourced ("if it is internal then only
		// sizing program button will be displayed. and if outsourced
		// weaving receipt button will be displayed" - your words).
		//
		// Flagged assumption: Type is a Link to Weaving Type, so this
		// compares its value against the literal names "Internal" /
		// "Outsourced" - only correct if your Weaving Type records are
		// actually named exactly that. Tell me if they're named
		// differently and I'll adjust the comparison.
		if (frm.doc.docstatus == 1 && frm.doc.custom_status == "Open") {
			if (frm.doc.type == "Internal") {
				frm.add_custom_button(__('Sizing Program'), function() {
					open_sizing_program_dialog(frm)
				}).css('background-color', '#2490EF').css('color', '#ffffff','font-weight','bold');
			}

			if (frm.doc.type == "Outsourced") {
				frm.add_custom_button(__('Weaving Receipt'), function() {
					frappe.call({
						method: "emadi_v3_abdullah.emadi.events.create_weaving_receipt_from_weaving_contract.create_weaving_receipt_from_weaving_contract",
						args: {
							weaving_contract: frm.doc.name
						},
						freeze: true,
						callback: function(r) {
							if (!r.exc && r.message) {
								frappe.model.sync(r.message);
								frappe.set_route("Form", r.message.doctype, r.message.name);
							}
						}
					});
				}).css('background-color', '#ff9800').css('color', '#ffffff','font-weight','bold');
			}
		}

		// Fabric Qty is derived from the yarn lbs when linked to a Sales Order
		// (only when the rows came from the Towel Costing Sheet yarn balance)
		let yarn_driven = frm.doc.sales_order && (frm.doc.bom_items || []).some((r) => flt(r.so_yarn_balance) > 0);
		frm.set_df_property('fabric_qty', 'read_only', yarn_driven ? 1 : 0);

		frm.set_query('construction', function() {
			return {
				"filters": {
					"item_group": "Fabric"
				}
			}
		});
		frm.set_query('yarn_count','bom_items', function() {
			return {
				"filters": {
					"item_group": ["in", ["Yarn", "Beam"]]
				}
			}
		})

	},

	// 2026-09-28 (feature v3) - "yarn qty will be recalculated upon
	// changing Order Qty. yarn qty = yarn reqd per lbs (from TCS) *
	// order qty" (your words). Only fires when the field is actually
	// editable - it's read-only whenever this contract is yarn-driven
	// (see the read_only toggle in refresh above), so this only applies
	// to a contract where you're typing Order Qty in yourself.
	fabric_qty: function(frm) {
		if (!(frm.doc.sales_order && frm.doc.construction)) {
			return;
		}
		frm.call({
			method: "recalc_yarn_from_order_qty",
			doc: frm.doc,
			freeze: true
		}).then(() => {
			frm.dirty();
			frm.refresh_field("bom_items");
			frm.refresh_fields(["total_yarn", "total_bags", "total_consumption", "fabric_qty"]);
		});
	}
});

frappe.ui.form.on('BOM Items', {
	// 2026-09-26 - contracts are split by yarn lbs: Yarn Qty is editable,
	// Required Bags follows it (Yarn Qty / Lbs per Bag). Fabric Qty is
	// recalculated from the lbs on save (server-side).
	yarn_qty: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (flt(row.lbs_per_bag)) {
			frappe.model.set_value(cdt, cdn, "required_bags", flt(row.yarn_qty) / flt(row.lbs_per_bag));
		}
		if (flt(row.so_yarn_balance) && flt(row.yarn_qty) > flt(row.so_yarn_balance) + 0.001) {
			frappe.show_alert({
				message: __("{0}: {1} lbs is more than the {2} lbs left on the Sales Order", [row.yarn_count, format_number(row.yarn_qty), format_number(row.so_yarn_balance)]),
				indicator: "orange"
			});
		}
		calculate_total(frm);
	},
	lbs_per_bag: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (flt(row.lbs_per_bag)) {
			frappe.model.set_value(cdt, cdn, "required_bags", flt(row.yarn_qty) / flt(row.lbs_per_bag));
		}
	},
	required_bags: function(frm) {
		calculate_total(frm);
	},
	bom_items_remove: function(frm) {
		calculate_total(frm);
	}
});


function calculate_total(frm) {
	let yarn_qty = 0;
	let required_bags = 0;
	$.each(frm.doc.bom_items || [], function (i, d) {
		yarn_qty += flt(d.yarn_qty);
		required_bags += flt(d.required_bags);
	});
	frm.set_value("total_yarn", yarn_qty);
	frm.set_value("total_bags", required_bags);
	// Total Consumption = sum of the table's Yarn Qty
	frm.set_value("total_consumption", yarn_qty);
}

// ---------------------------------------------------------------------
// Issue Yarn
// ---------------------------------------------------------------------
function open_issue_yarn_dialog(frm) {
	let rows = (frm.doc.bom_items || []).map((row) => {
		let remaining = flt(row.yarn_qty) - flt(row.yarn_issued);
		return {
			row_name: row.name,
			yarn_count: row.yarn_count,
			yarn_qty: row.yarn_qty,
			yarn_issued: row.yarn_issued,
			remaining: remaining
		};
	});

	if (!rows.length) {
		frappe.msgprint(__("No yarn rows on this Weaving Contract."));
		return;
	}

	let dialog = new frappe.ui.Dialog({
		title: __("Issue Yarn"),
		size: "large",
		fields: [
			{
				fieldname: "items_html",
				fieldtype: "HTML"
			}
		],
		primary_action_label: __("Issue"),
		primary_action: () => {
			// Scoped to this dialog's own wrapper, not a global id lookup -
			// same reasoning as Issue Fabric's dialog (dyeing_contract.js).
			let entries = rows
				.map((r) => {
					let $row = dialog.$wrapper.find(`[data-row-name="${r.row_name}"]`);
					return {
						row_name: r.row_name,
						qty: flt($row.find('[data-field="qty"]').val())
					};
				})
				.filter((e) => e.qty > 0);

			if (!entries.length) {
				frappe.msgprint(__("Enter a qty to issue for at least one yarn."));
				return;
			}

			frappe.call({
				method: "emadi_v3_abdullah.emadi.events.issue_yarn.issue_yarn",
				args: {
					weaving_contract: frm.doc.name,
					rows: entries
				},
				freeze: true,
				callback: (r) => {
					if (!r.message) {
						return;
					}
					dialog.hide();
					// Draft only, not submitted - "user will submit the
					// entry himself" (your words), same as Issue Fabric.
					frappe.model.sync(r.message);
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			});
		}
	});

	let rows_html = rows
		.map(
			(r) => `
		<tr data-row-name="${frappe.utils.escape_html(r.row_name)}">
			<td>${frappe.utils.escape_html(r.yarn_count)}</td>
			<td class="text-right">${format_number(r.yarn_qty)}</td>
			<td class="text-right">${format_number(r.yarn_issued)}</td>
			<td class="text-right">${format_number(r.remaining)}</td>
			<td><input type="number" step="any" class="form-control" data-field="qty" value="0"></td>
		</tr>`
		)
		.join("");

	dialog.fields_dict.items_html.$wrapper.html(`
		<div style="overflow-x:auto">
		<table class="table table-bordered">
			<thead>
				<tr>
					<th>${__("Yarn Count")}</th>
					<th class="text-right">${__("Yarn Qty (Lbs)")}</th>
					<th class="text-right">${__("Issued So Far")}</th>
					<th class="text-right">${__("Remaining")}</th>
					<th>${__("Qty To Issue (Lbs)")}</th>
				</tr>
			</thead>
			<tbody>${rows_html}</tbody>
		</table>
		</div>
	`);

	dialog.show();
}

function sync_yarn_issued_totals(frm) {
	frappe.call({
		method: "emadi_v3_abdullah.emadi.events.issue_yarn.sync_yarn_issued_totals",
		args: { weaving_contract: frm.doc.name },
		callback: (r) => {
			if (r.message && r.message.changed) {
				frm.reload_doc();
			}
		}
	});
}

// ---------------------------------------------------------------------
// Sizing Program (round 10, popup restored 2026-09-16 - your traceback
// showed the OLD pre-round-10 create_sizing_program_from_weaving_contract.py
// still live on your site, matching `for == "Warp"` - dropped in favor of
// Weft/Pile/Ground/Fancy - and crashing on `float(None[:2])`. My own local
// copy of this file had also lost round 10's picker popup somewhere along
// the way (it was only ever delivered as a JS patch, not a full file, back
// then) - restoring it here so re-deploying both files together fixes the
// crash AND lets you actually pick which Pile/Ground row, instead of the
// method silently defaulting to the first one.
// ---------------------------------------------------------------------
function open_sizing_program_dialog(frm) {
	let rows = (frm.doc.bom_items || []).filter(function(r) {
		return (r.for == "Pile" || r.for == "Ground") && r.yarn_count
	})

	if (!rows.length) {
		frappe.msgprint(__("No Pile/Ground item with a Yarn Count found in this Weaving Contract's BOM Items."))
		return
	}

	let by_label = {}
	let options = rows.map(function(r) {
		let label = `${r.for} - ${r.yarn_count}`
		by_label[label] = r
		return label
	})

	frappe.prompt(
		[{
			fieldname: 'row',
			label: __('Pile/Ground Item'),
			fieldtype: 'Select',
			options: options,
			reqd: 1
		}],
		function(values) {
			let selected = by_label[values.row]
			frappe.call({
				method: "emadi_v3_abdullah.emadi.events.create_sizing_program_from_weaving_contract.create_sizing_program_from_weaving_contract",
				args: {
					weaving_contract: frm.doc.name,
					item: selected.yarn_count,
					beam_for: selected.for
				},
				freeze: true,
				callback: function(r) {
					if (!r.exc && r.message) {
						frappe.model.sync(r.message);
						frappe.set_route("Form", r.message.doctype, r.message.name);
					}
				}
			})
		},
		__('Select Pile/Ground Item'),
		__('Create')
	)
}

// ---------------------------------------------------------------------
// Get Items From > Sales Order
// ---------------------------------------------------------------------
function get_items_from_sales_order(frm) {
	frappe.prompt(
		[{
			fieldname: 'sales_order',
			label: __('Sales Order'),
			fieldtype: 'Link',
			options: 'Sales Order',
			reqd: 1,
			get_query: function() {
				return { filters: { docstatus: 1 } }
			}
		}],
		function(values) {
			frappe.call({
				method: "emadi_v3_abdullah.emadi.events.get_items_from_sales_order.get_sales_order_items",
				args: { sales_order: values.sales_order },
				callback: function(r) {
					let items = r.message || []
					if (!items.length) {
						frappe.msgprint(__('No items with a pending weaving balance were found in {0}', [values.sales_order]))
						return
					}
					pick_sales_order_item(frm, values.sales_order, items)
				}
			})
		},
		__('Get Items From Sales Order'),
		__('Next')
	)
}

function pick_sales_order_item(frm, sales_order, items) {
	// 2026-09-14 update: items are now grouped by item_code (one entry
	// per Item, balance combined across every Color row of that Item -
	// see get_sales_order_items' own note), so this keys off item_code
	// instead of a single Sales Order Item row name.
	let by_label = {}
	let options = items.map(function(d) {
		let label = flt(d.yarn_balance_lbs)
			? `${d.item_code} (Yarn balance: ${format_number(d.yarn_balance_lbs)} lbs)`
			: `${d.item_code} (Balance: ${d.balance_qty})`
		by_label[label] = d
		return label
	})

	frappe.prompt(
		[{
			fieldname: 'item',
			label: __('Item'),
			fieldtype: 'Select',
			options: options,
			reqd: 1
		}],
		function(values) {
			let selected = by_label[values.item]
			frappe.call({
				method: "emadi_v3_abdullah.emadi.events.get_items_from_sales_order.get_weaving_items_from_sales_order",
				args: {
					sales_order: sales_order,
					item_code: selected.item_code
				},
				callback: function(r) {
					apply_sales_order_item(frm, sales_order, r.message)
				}
			})
		},
		__('Select Item'),
		__('Fetch')
	)
}

function apply_sales_order_item(frm, sales_order, data) {
	if (!data) return

	frm.set_value('construction', data.item_code)
	frm.set_value('fabric_qty', data.order_qty)
	frm.set_value('finish_weight', data.finish_weight)
	frm.set_value('gross_weight', data.gross_weight)
	frm.set_value('sales_order', sales_order)
	frm.set_value('sales_order_item', data.sales_order_item)

	frm.clear_table('bom_items')
	;(data.bom_items || []).forEach(function(row) {
		let child = frm.add_child('bom_items')
		child.for = row.for
		child.yarn_count = row.yarn_count
		child.ratio = row.ratio
		child.weaving_wastage = row.weaving_wastage
		child.yarn_qty = row.yarn_qty
		child.so_yarn_balance = row.so_yarn_balance
		child.lbs_per_bag = row.lbs_per_bag
		child.required_bags = row.required_bags
	})
	frm.refresh_field('bom_items')
	calculate_total(frm)
}