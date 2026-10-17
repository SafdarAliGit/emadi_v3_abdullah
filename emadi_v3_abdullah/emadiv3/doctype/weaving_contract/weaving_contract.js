// Copyright (c) 2025, Safdar Ali and contributors
// For license information, please see license.txt

frappe.ui.form.on('Weaving Contract', {
	refresh: function(frm) {
		toggle_multi_item(frm);

		// 2026-09-28 (feature v3) - fill GSM on load too (not just on
		// Finish Item / Sales Order change), so it shows immediately on an
		// existing draft that was saved before this field existed, without
		// needing to touch those fields first.
		if (frm.doc.construction && !frm.doc.gsm) {
			fetch_gsm(frm);
		}

		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Sales Order'), function() {
				get_items_from_sales_order(frm)
			}, __('Get Items From'))
		}

		// 2026-09-16 - "same workflow like issue fabric in dyeing contract
		// is needed in Weaving Contract named 'Issue Yarn'" (your words).
		// 2026-09-28 - now gated to Weaving Type "External" only (see the
		// type-gated block below) - moved out of this always-shown block.
		if (frm.doc.docstatus == 1) {
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
		// 2026-09-28 - "if Weaving Type is Internal then ... Create Sizing
		// Program button should occur. If Weaving Type is External, then
		// Issue Yarn Button should occur" (your words) - renamed from
		// "Outsourced" to "External" to match your Weaving Type records,
		// and Issue Yarn moved in here alongside Weaving Receipt (both are
		// the External-only steps: send yarn out, receive fabric back).
		if (frm.doc.docstatus == 1 && frm.doc.custom_status == "Open") {
			if (["Internal", "Commercial"].includes(frm.doc.type)) {
				frm.add_custom_button(__('Sizing Program'), function() {
					open_sizing_program_dialog(frm)
				}).css('background-color', '#2490EF').css('color', '#ffffff','font-weight','bold');
			}

			if (frm.doc.type == "External") {
				frm.add_custom_button(__('Issue Yarn'), function() {
					open_issue_yarn_dialog(frm)
				}).css('background-color', '#2490EF').css('color', '#ffffff','font-weight','bold');

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

		// 2026-09-30 - Customer Provided yarn request, only for Commercial
		// contracts woven by Paul Textiles (the case where Customer is mandatory).
		if (frm.doc.docstatus == 1 && frm.doc.type == "Commercial" && (frm.doc.weaver || "").trim().toLowerCase() == "paul textiles") {
			frm.add_custom_button(__('Create Material Request for Yarn'), function() {
				frappe.call({
					method: "emadi_v3_abdullah.emadiv3.events.customer_yarn_material_request.make_customer_yarn_material_request",
					args: { weaving_contract: frm.doc.name },
					freeze: true,
					callback: function(r) {
						if (!r.exc && r.message) {
							frappe.model.sync(r.message);
							frappe.set_route("Form", r.message.doctype, r.message.name);
						}
					}
				});
			}).css('background-color', '#2490EF').css('color', '#ffffff');
		}

		// Fabric Qty is derived from the yarn lbs when linked to a Sales Order
		// (only when the rows came from the Towel Costing Sheet yarn balance)
		let yarn_driven = frm.doc.type != "Commercial" && frm.doc.sales_order && (frm.doc.bom_items || []).some((r) => flt(r.so_yarn_balance) > 0);
		frm.set_df_property('fabric_qty', 'read_only', yarn_driven ? 1 : 0);

		frm.set_query('construction', function() {
			return {
				"filters": {
					"item_group": "Fabric"
				}
			}
		});
		frm.set_query('finish_item', 'bom_items', function() {
			return { filters: { name: ["in", get_finish_item_names(frm)] } };
		});
		frm.set_query('finish_item', 'finish_items', function() {
			return { filters: { item_group: "Fabric" } };
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
	},

	type: function(frm) {
		// Multi Item only exists for Commercial contracts
		if (frm.doc.type != "Commercial" && frm.doc.multi_item_weaving_contract) {
			frm.set_value("multi_item_weaving_contract", 0);
		}
		toggle_multi_item(frm);
	},
	multi_item_weaving_contract: function(frm) {
		toggle_multi_item(frm);
	},
	// Each Finish Item's yarn Ratio % must add up to 100
	validate: function(frm) {
		if (!is_multi_item(frm)) {
			return;
		}
		let totals = {};
		(frm.doc.finish_items || []).forEach(function(r) {
			if (r.finish_item) {
				totals[r.finish_item] = 0;
			}
		});
		(frm.doc.bom_items || []).forEach(function(r) {
			if (!r.finish_item || !(r.finish_item in totals)) {
				frappe.throw(__("BOM Items row {0}: select a Finish Item from the Finish Items table.", [r.idx]));
			}
			totals[r.finish_item] += flt(r.ratio);
		});
		Object.keys(totals).forEach(function(item) {
			if (Math.abs(totals[item] - 100) > 0.01) {
				frappe.throw(__("Ratio % of the yarn rows for {0} adds up to {1}, it must be 100.", [item, flt(totals[item], 2)]));
			}
		});
	},

	// 2026-09-28 (feature v3) - "gsm field ... in Weaving contract" (your
	// words). Live preview only - the server's validate() recalculates
	// this fresh on every save regardless (see sync_gsm in
	// weaving_contract.py), same pattern as Sales Order Item's GSM.
	construction: function(frm) {
		fetch_gsm(frm);
	},
	sales_order: function(frm) {
		fetch_gsm(frm);
	}
});

function is_multi_item(frm) {
	return frm.doc.type == "Commercial" && frm.doc.multi_item_weaving_contract;
}

function get_finish_item_names(frm) {
	let names = (frm.doc.finish_items || []).map((r) => r.finish_item).filter(Boolean);
	return names.length ? names : [""];
}

// Multi Item: BOM Items rows get a Finish Item column.
function toggle_multi_item(frm) {
	const grid = frm.fields_dict.bom_items && frm.fields_dict.bom_items.grid;
	if (!grid) {
		return;
	}
	const multi = is_multi_item(frm) ? 1 : 0;
	grid.update_docfield_property('finish_item', 'hidden', multi ? 0 : 1);
	grid.update_docfield_property('finish_item', 'reqd', multi);
	frm.refresh_field('bom_items');
}

frappe.ui.form.on('Weaving Contract Finish Item', {
	finish_item: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (!row.finish_item) {
			return;
		}
		frappe.call({
			method: "emadi_v3_abdullah.emadiv3.doctype.weaving_contract.weaving_contract.get_contract_gsm",
			args: { construction: row.finish_item },
			callback: (r) => {
				frappe.model.set_value(cdt, cdn, "gsm", r.message || 0);
			}
		});
	}
});

function fetch_gsm(frm) {
	if (!frm.doc.construction) {
		return;
	}
	frappe.call({
		method: "emadi_v3_abdullah.emadiv3.doctype.weaving_contract.weaving_contract.get_contract_gsm",
		args: {
			sales_order: frm.doc.sales_order,
			sales_order_item: frm.doc.sales_order_item,
			construction: frm.doc.construction
		},
		callback: (r) => {
			frm.set_value("gsm", r.message || 0);
		}
	});
}

frappe.ui.form.on('BOM Items', {
	bom_items_add: function(frm, cdt, cdn) {
		// only one Finish Item: no need to pick it on every row
		let items = get_finish_item_names(frm).filter(Boolean);
		if (is_multi_item(frm) && items.length == 1) {
			frappe.model.set_value(cdt, cdn, "finish_item", items[0]);
		}
	},
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
	// The server adds up rows of the same yarn and drops any yarn whose full
	// LBS already has a Sizing Program.
	frappe.call({
		method: "emadi_v3_abdullah.emadi.events.create_sizing_program_from_weaving_contract.get_sizing_program_items",
		args: { weaving_contract: frm.doc.name },
		callback: function(r) {
			let rows = r.message || []

			if (!rows.length) {
				frappe.msgprint(__("No Pile/Ground yarn is left to create a Sizing Program for."))
				return
			}

			let by_label = {}
			let options = rows.map(function(row) {
				let label = `${row.for} - ${row.yarn_count} (${format_number(row.pending)} lbs)`
				by_label[label] = row
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
	})
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
					if (items.length > 1) {
						// several unique items: straight into a Commercial Multi Item contract
						fetch_multi_item(frm, values.sales_order)
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

function fetch_multi_item(frm, sales_order) {
	frappe.call({
		method: "emadi_v3_abdullah.emadi.events.get_items_from_sales_order.get_multi_item_weaving_data",
		args: { sales_order: sales_order },
		freeze: true,
		callback: function(r) {
			let data = r.message
			if (!data) return

			frm.set_value('sales_order', sales_order)
			frm.set_value('sales_order_item', data.sales_order_item)
			frm.set_value('type', 'Commercial')
			frm.set_value('multi_item_weaving_contract', 1)

			frm.clear_table('finish_items')
			;(data.finish_items || []).forEach(function(row) {
				let child = frm.add_child('finish_items')
				Object.assign(child, row)
			})
			frm.clear_table('bom_items')
			;(data.bom_items || []).forEach(function(row) {
				let child = frm.add_child('bom_items')
				Object.assign(child, row)
			})
			frm.refresh_fields()
			calculate_total(frm)
		}
	})
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