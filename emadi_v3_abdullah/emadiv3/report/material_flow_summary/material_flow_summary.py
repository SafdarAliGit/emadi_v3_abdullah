import frappe

def execute(filters=None):
    columns = [
        
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Data", "width": 140},
        {"label": "Gate Pass", "fieldname": "gate_pass", "fieldtype": "Data", "width": 120},
        {"label": "Yarn Item", "fieldname": "yarn_item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Brand", "fieldname": "brand", "fieldtype": "Link", "options": "Brand", "width": 100},
         {"label": "Purpose", "fieldname": "purpose", "fieldtype": "Data", "width": 120},
        {"label": "Yarn Count", "fieldname": "yarn_count", "fieldtype": "Data", "width": 100},
        {"label": "Bags/Length", "fieldname": "bags", "fieldtype": "Data", "width": 80},
        {"label": "Lbs", "fieldname": "lbs", "fieldtype": "Data", "width": 120},
        {"label": "Meter", "fieldname": "meter", "fieldtype": "Data", "width": 120},
        {"label": "Return", "fieldname": "return", "fieldtype": "Data", "width": 120}
       
    ]

    conditions = ""
    conditions2 = ""
    weft_production_conditions = ""
    sizing_program_conditions = ""
    warp_production_conditions = ""
    delivery_conditions_master = ""
    delivery_conditions = ""

    p = filters.get("p")

    if filters.get("brand"):
        conditions += " AND sed.brand = %(brand)s"
    if filters.get("yarn_count"):
        conditions += " AND sed.`for` = 'Warp' AND sed.item_code IN %(yarn_count)s"

    if filters.get("brand"):
        conditions2 += " AND sed.brand = %(brand)s"
    if filters.get("yarn_count_weft"):
        conditions2 += " AND sed.`for` = 'Weft' AND sed.item_code IN %(yarn_count_weft)s"
        
    if filters.get("yarn_count_weft"):
        weft_production_conditions += " AND fpi.yarn_count IN %(yarn_count_weft)s"
    if filters.get("fabric_item"):
        weft_production_conditions += " AND fp.fabric_item IN %(fabric_item)s"

    if filters.get("fabric_item"):
        warp_production_conditions += " AND fp.fabric_item IN %(fabric_item)s"

    if filters.get("fabric_item"):
        sizing_program_conditions += " AND sp.fabric_construction IN %(fabric_item)s"
    
    if filters.get("fabric_item"):
        delivery_conditions += " AND dn.fabric_item IN %(fabric_item)s"
    if filters.get("brand"):
        delivery_conditions += " AND bid.brand = %(brand)s"

    if filters.get("customer"):
        delivery_conditions_master += " AND dn.customer = %(customer)s"
    if filters.get("fabric_item"):
        delivery_conditions_master += " AND dn.fabric_item IN %(fabric_item)s"

    data = []
    data.append({
        "posting_date": "<b style='font-size: 14px;'>Yarn Received Warp</b>",
        "gate_pass": "",
        "yarn_item": "",
        "brand": "",
        "bags": "",
        "lbs": "",
        "meter": "",
        "purpose": "",
        "yarn_count": ""
    })
    
    yarn_received_warp = frappe.db.sql(f"""
        SELECT
            SUM(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Lbs' THEN sed.qty ELSE 0 END) as lbs,
            SUM(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Meter' THEN sed.qty ELSE 0 END) as meter,
            SUM(CASE WHEN se.stock_entry_type = 'Material Issue' THEN sed.qty ELSE 0 END) as `return`,
            se.manual_sr_no AS gate_pass
        FROM
            `tabStock Entry` se
        LEFT JOIN
            `tabStock Entry Detail` sed ON se.name = sed.parent
        WHERE
            se.docstatus = 1 {conditions}
        ORDER BY
            se.posting_date DESC
    """, filters, as_dict=True)
    data.extend(yarn_received_warp)

    data.append({
        "posting_date": "<b style='font-size: 14px;'>Yarn Received Weft</b>",
        "gate_pass": "",
        "yarn_item": "",
        "brand": "",
        "bags": "",
        "lbs": "",
        "meter": "",
        "purpose": "",
        "yarn_count": ""
    })

    yarn_received_weft = frappe.db.sql(f"""
        SELECT
            SUM(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Lbs' THEN sed.qty ELSE 0 END) as lbs,
            SUM(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Meter' THEN sed.qty ELSE 0 END) as meter,
            SUM(CASE WHEN se.stock_entry_type = 'Material Issue' THEN sed.qty ELSE 0 END) as `return`
        FROM
            `tabStock Entry` se
        LEFT JOIN
            `tabStock Entry Detail` sed ON se.name = sed.parent
        WHERE
            se.docstatus = 1 {conditions2}
        ORDER BY
            se.posting_date DESC
    """, filters, as_dict=True)
    data.extend(yarn_received_weft)

    data.append({
        "posting_date": "<b style='font-size: 14px;'>WEFT Detail</b>",
        "gate_pass": "<b style='font-size: 12px;'>(Fabric Production)</b>",
        "yarn_item": "",
        "brand": "",
        "bags": "",
        "lbs": "",
        "meter": "",
        "purpose": "",
        "yarn_count": ""
    })
    weft_production_data = frappe.db.sql(f"""
        SELECT
            ROUND(SUM(fpi.yarn_qty), 5) AS lbs,
            ROUND(SUM(fpi.beam_length), 5) AS meter
        FROM
            `tabFabric Production` fp
        LEFT JOIN
            `tabFabric Production Item` fpi ON fp.name = fpi.parent
        WHERE
            fp.docstatus = 1 {weft_production_conditions}
			AND fpi.for = 'Weft'
        ORDER BY
            fp.posting_date DESC
    """, filters, as_dict=True)
    # total_weft = sum(row["lbs"] or 0 for row in weft_production_data)
    # if weft_production_data:
    #     weft_production_data.append({
    #         "posting_date": "<b>Total Weft</b>",
    #         "yarn_item": "",
    #         "purpose": "",
    #         "lbs": "<b>" + str(round(total_weft,2)) + "</b>",
    #         "gate_pass": ""
    #     })
    data.extend(weft_production_data)
    data.append({
            "posting_date": "<b style='font-size: 14px;'>Warp Consumption</b>",
            "gate_pass": "<b style='font-size: 12px;'>(Sizing Program)</b>",
            "yarn_item": "",
            "brand": "",
            "bags": "",
            "lbs": "",
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })
    sizing_program_data = frappe.db.sql(f"""
        SELECT
            ROUND(SUM(spi.length), 2) AS bags,
            ROUND(SUM(spi.lbs), 2) AS lbs,
            ROUND(SUM(spi.length), 2) AS meter
        FROM
            `tabSizing Program` AS sp
        LEFT JOIN
            `tabSizing Program Item` AS spi ON sp.name = spi.parent
        WHERE
            sp.docstatus = 1
            {sizing_program_conditions}
        having ROUND(SUM(spi.lbs), 2) > 0
    """, filters, as_dict=True)
    ratio = 0
    total_production_length = 0
    if sizing_program_data:
        # total_warp = sum(row["lbs"] or 0 for row in sizing_program_data)
        total_production_length = sizing_program_data[0].get("bags", 0)
        ratio = (sizing_program_data[0].get("lbs", 0) or 0) / (total_production_length if total_production_length > 0 else 1)
    # if sizing_program_data:
    #     sizing_program_data.append({
    #         "posting_date": "<b>Total Warp</b>",
    #         "yarn_item": "",
    #         "purpose": "Ratio: " + str(ratio),
    #         "bags": "<b>" + str(round(total_production_length,2)) + "</b>",
    #         "lbs": "<b>" + str(round(total_warp,2)) + "</b>",
    #         "gate_pass": ""
    #     })
    data.extend(sizing_program_data)

    data.append({
            "posting_date": "<b style='font-size: 14px;'>WARP Detail</b>",
            "gate_pass": "<b style='font-size: 12px;'>(Fabric Production)</b>",
            "yarn_item": "",
            "brand": "",
            "bags": "",
            "lbs": "",
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })

    warp_production_data = frappe.db.sql(f"""
        SELECT
            ROUND(SUM(fpi.yarn_qty), 5) AS bags,
            ROUND(SUM(fpi.beam_length), 5) AS meter
        FROM
            `tabFabric Production` fp
        LEFT JOIN
            `tabFabric Production Item` fpi ON fp.name = fpi.parent
        WHERE
            fp.docstatus = 1 {warp_production_conditions}
			AND fpi.for = 'Warp'
        ORDER BY
            fp.posting_date DESC
    """, filters, as_dict=True)
    total_warp = sum(row["bags"] or 0 for row in warp_production_data)
    total_warp_meter = sum(row["meter"] or 0 for row in warp_production_data)
    if warp_production_data:
        warp_production_data.append({
            "posting_date": "<b>Total Warp</b>",
            "yarn_item": "",
            "purpose": "",
            "bags":round(total_warp,2),
            "lbs":"LBS : " + "<b>" + str(round(total_warp *(ratio if ratio else 1),2)) + "</b>",
            "meter":"<b>" + str(round(total_warp_meter,2)) + "</b>",
            "gate_pass": ""
        })
    data.extend(warp_production_data)


    # yarn_balance = total_received - (total_weft + total_warp)
    remaining_bags = 0
    if sizing_program_data:
        waste_percentage_bags = float(sizing_program_data[0].get("bags", 1)) * (float(p) / 100)
        remaining_bags = float(sizing_program_data[0].get("bags", 0)) - waste_percentage_bags if waste_percentage_bags else 0
        yarn_balance_data = [{"posting_date": "<b>Yarn Warp Balance(Length)</b>", "gate_pass": "", "yarn_item": "Waste %: " + str(p) + "%", "brand": "Waste: " + str(round(waste_percentage_bags,2)), "bags":str(round(remaining_bags,2)-total_warp if total_warp else 0) , "lbs":str(round(((remaining_bags if remaining_bags else 0)- (total_warp if total_warp else 0)) * (ratio if ratio else 1),2)), "purpose": "Remaining: " + str(round(remaining_bags,2)), "yarn_count": ""}]
        data.extend(yarn_balance_data)
    # Delivery Detail
    delivery_fabric_qty = frappe.db.sql(f"""
        SELECT
            SUM(dn.fabric_qty) as yarn_item
        FROM
            `tabDelivery Note` dn
        WHERE
            dn.docstatus = 1 {delivery_conditions_master} and dn.is_return = 0
    """, filters, as_dict=True)

    delivery_fabric_qty_with_return = frappe.db.sql(f"""
        SELECT
            SUM(dn.fabric_qty) as yarn_item
        FROM
            `tabDelivery Note` dn
        WHERE
            dn.docstatus = 1 {delivery_conditions_master}
    """, filters, as_dict=True)

    data.append({
            "posting_date": "<b style='font-size: 14px;'>Delivery Detail (Fabric)</b>",
            "gate_pass": "",
            "yarn_item": "",
            "brand": "",
            "bags": "",
            "lbs": "",
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })
    data.append({
            "posting_date": "<b>Fabric Qty (With Return)</b>",
            "gate_pass": "",
            "yarn_item":"",
            "brand": "",
            "bags": str(round(delivery_fabric_qty[0].yarn_item if delivery_fabric_qty else 0,2)),
            "lbs": "",
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })
    data.append({
            "posting_date": "<b>Fabric Qty (Without Return)</b>",
            "gate_pass": "",
            "yarn_item": "",
            "brand": "",
            "bags": str(round(delivery_fabric_qty_with_return[0].yarn_item if delivery_fabric_qty_with_return else 0,2)),
            "lbs": "",
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })
    data.append({
            "posting_date": "<b>Fabric Balance</b>",
            "gate_pass": "",
            "yarn_item": "",
            "brand": "",
             "bags":str(round((sizing_program_data[0].bags if sizing_program_data else 0)-(delivery_fabric_qty_with_return[0].yarn_item if delivery_fabric_qty_with_return else 0),2)),
            "lbs":"" ,
            "meter":"",
            "purpose": "",
            "yarn_count": ""
        })
    data.append({
            "posting_date": "<b>Shortage/Gain</b>",
            "gate_pass": "",
            "yarn_item": "",
            "brand": "",
            "bags":str(round(((remaining_bags if remaining_bags else 0)-(delivery_fabric_qty_with_return[0].yarn_item if delivery_fabric_qty_with_return else 0)),2)),
            "lbs": (
                round((
                        (remaining_bags if remaining_bags else 0)-(delivery_fabric_qty_with_return[0].yarn_item if delivery_fabric_qty_with_return else 0)
                    ) * (ratio or 0),
                    2
                )
                ),
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })
    data.append({
            "posting_date": "<b>Shortage/Gain % </b>",
            "gate_pass": "",
            "yarn_item": "",
            "brand": "",
            "bags": str(round((((total_production_length if total_production_length else 0)-(delivery_fabric_qty_with_return[0].yarn_item if delivery_fabric_qty_with_return else 0))/(total_production_length if total_production_length else 1)*100),2)),
            "lbs": "",#str(
#     round(
#             (remaining_bags if remaining_bags else 0)-(delivery_fabric_qty_with_return[0].yarn_item if delivery_fabric_qty_with_return else 0)
#         ) * (ratio or 0),
#         2
#     )
# )
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })
        # ------------- warp weft detail
    data.append({
            "posting_date": "",
            "gate_pass": "Fabric Item",
            "yarn_item": "",
            "brand": "",
            "bags": "Warp Qty",
            "lbs": "Weft Qty",
            "meter": "",
            "purpose": "",
            "yarn_count": ""
        })


    delivery_data = frappe.db.sql(f"""
        SELECT
            SUM(CASE WHEN bid.for = 'Warp' THEN bid.yarn_qty ELSE 0 END) as bags,
            SUM(CASE WHEN bid.for = 'Weft' THEN bid.yarn_qty ELSE 0 END) as lbs
        FROM
            `tabDelivery Note` dn
        LEFT JOIN
            `tabBOM Items Dn` bid ON dn.name = bid.parent
        WHERE
            dn.docstatus = 1 {delivery_conditions}

    """, filters, as_dict=True)
    # total_warp = sum(row["bags"] or 0 for row in delivery_data)
    # total_weft = sum(row["lbs"] or 0 for row in delivery_data)

    if delivery_data:
        delivery_data.append({
        "posting_date": "<b>Yarn Balance(Customer)</b>",
        "yarn_item": "",
        "purpose": "",
        "brand": "",
        "bags": "<b>" + str(
            (
                round(
                    (yarn_received_warp[0].get("lbs") or 0)
                    - round(
                        (delivery_fabric_qty_with_return[0].yarn_item if delivery_fabric_qty_with_return and delivery_fabric_qty_with_return[0].yarn_item is not None else 0),
                        2
                    ),
                    2
                )
                if yarn_received_warp and (yarn_received_warp[0].get("lbs") or 0) > 0
                else 0
            )
        ) + "</b>",
        "lbs": "<b>" + str(
            round(
                ((yarn_received_weft[0].get("lbs") or 0) - (delivery_data[0].get("lbs") or 0)),
                2
            )
        ) + "</b>",
        "meter": "<b>" + str(
            round(
                (
                    ((yarn_received_warp[0].get("meter") or 0) - (delivery_data[0].get("meter") or 0))
                    if yarn_received_warp and delivery_data and (yarn_received_warp[0].get("meter") or 0) > 0
                    else 0
                )
                - (round(delivery_fabric_qty_with_return[0].yarn_item, 2) if delivery_fabric_qty_with_return and delivery_fabric_qty_with_return[0].yarn_item is not None else 0),
                2
            )
        ) + "</b>",
        "gate_pass": ""
        })

        # delivery_data.append({
        #     "posting_date": "<b>Yarn Balance(Customer)</b>",
        #     "yarn_item": "",
        #     "purpose":"",
        #     "brand": "",
        #     "bags":"<b>" + str(round(total_received_warp - total_warp,2)) + "</b>",
        #     "lbs": "<b>" + str(round(total_received_weft - total_weft,2)) + "</b>",
        #     "gate_pass": ""
        # })
        # delivery_data.append({
        #     "posting_date": "<b>Warp + Weft(Customer Ratio)</b>",
        #     "yarn_item": "",
        #     "purpose":"",
        #     "brand": "",
        #     "bags":"",
        #     "lbs":"<b>" + str(round((delivery_data[0].bags if delivery_data else 0)+(delivery_data[0].lbs if delivery_data else 0),2)) + "</b>",
        #     "meter":"",
        #     "gate_pass": ""
        # })
    data.extend(delivery_data)
    return columns, data



