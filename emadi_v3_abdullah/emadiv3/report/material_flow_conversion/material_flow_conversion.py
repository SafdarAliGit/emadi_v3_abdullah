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
    delivery_note_conditions = ""

    p = filters.get("p")
    warp_opening = filters.get("warp_opening") or 0
    weft_opening = filters.get("weft_opening") or 0

    if filters.get("brand"):
        conditions += " AND sed.brand = %(brand)s"
    if filters.get("yarn_count"):
        conditions += " AND sed.`for` = 'Warp' AND sed.item_code IN %(yarn_count)s"
    if filters.get("from_date"):
        conditions += " AND se.posting_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND se.posting_date <= %(to_date)s"

    if filters.get("brand"):
        conditions2 += " AND sed.brand = %(brand)s"
    if filters.get("yarn_count_weft"):
        conditions2 += " AND sed.`for` = 'Weft' AND sed.item_code IN %(yarn_count_weft)s"
    if filters.get("from_date"):
        conditions2 += " AND se.posting_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions2 += " AND se.posting_date <= %(to_date)s"
    
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
    if filters.get("from_date"):
        delivery_conditions += " AND dn.posting_date >= %(from_date)s"
    if filters.get("to_date"):
        delivery_conditions += " AND dn.posting_date <= %(to_date)s"

    if filters.get("customer"):
        delivery_conditions_master += " AND dn.customer = %(customer)s"
    if filters.get("fabric_item"):
        delivery_conditions_master += " AND dn.fabric_item IN %(fabric_item)s"

    if filters.get("fabric_item"):
        delivery_note_conditions += " AND dn.fabric_item IN %(fabric_item)s"
    if filters.get("from_date"):
        delivery_note_conditions += " AND dn.posting_date >= %(from_date)s"
    if filters.get("to_date"):
        delivery_note_conditions += " AND dn.posting_date <= %(to_date)s"
    if filters.get("customer"):
        delivery_note_conditions += " AND dn.customer = %(customer)s"

    
    data = []

    # Warp Data
    data_warp = frappe.db.sql(f"""
    SELECT
        se.posting_date,
        se.manual_sr_no AS gate_pass,
        sed.item_code AS yarn_item,
        sed.brand,
        sed.qty_pcs AS bags,
        ROUND(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Lbs' THEN sed.qty ELSE 0 END, 5) AS lbs,
        ROUND(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Meter' THEN sed.qty ELSE 0 END, 5) AS meter,
        sed.`for` AS purpose,
        sed.item_code AS yarn_count,
        ROUND(CASE WHEN se.stock_entry_type = 'Material Issue' THEN sed.qty ELSE 0 END, 5) AS `return`
    FROM
        `tabStock Entry` se
    LEFT JOIN
        `tabStock Entry Detail` sed ON se.name = sed.parent
    WHERE
        se.docstatus = 1 
        {conditions}
    ORDER BY
        se.posting_date DESC
    """, filters, as_dict=True)
    
    # Calculate total lbs for warp
    total_received = sum(row["lbs"] or 0 for row in data_warp)
    total_received_meter_warp = sum(row["meter"] or 0 for row in data_warp)
    total_return = sum(row["return"] or 0 for row in data_warp)
    total_received_warp = sum(row["lbs"] or 0 for row in data_warp if row["purpose"] == "Warp")

    # Add total row for warp
    if data_warp:
        data_warp.append({
        "posting_date": "<b>Total Warp Received</b>",
        "gate_pass": "Warp: " + "<b>" + str(round(total_received_warp, 2)) + "</b>",
        "yarn_item": "",
        "brand": "",
        "bags": "",
        "lbs": "<b>" + str(round(total_received, 2)) + "</b>",
        "meter": "<b>" + str(round(total_received_meter_warp, 2)) + " Mtr</b>",
        "purpose": "",
        "yarn_count": "",
        "return": "<b>" + str(round(total_return, 2)) + "</b>"
    })

    # Weft Data
    data_weft = frappe.db.sql(f"""
        SELECT
            se.posting_date,
            se.manual_sr_no AS gate_pass,
            sed.item_code AS yarn_item,
            sed.brand,
            sed.qty_pcs AS bags,
            ROUND(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Lbs' THEN sed.qty ELSE 0 END, 5) AS lbs,
            ROUND(CASE WHEN se.stock_entry_type = 'Material Receipt' AND sed.uom = 'Meter' THEN sed.qty ELSE 0 END, 5) AS meter,
            sed.`for` AS purpose,
            sed.item_code AS yarn_count,
            ROUND(CASE WHEN se.stock_entry_type = 'Material Issue' THEN sed.qty ELSE 0 END, 5) AS `return`
        FROM
            `tabStock Entry` se
        LEFT JOIN
            `tabStock Entry Detail` sed ON se.name = sed.parent
        WHERE
            se.docstatus = 1 
            {conditions2}
        ORDER BY
            se.posting_date DESC
    """, filters, as_dict=True)

    # Calculate total lbs for weft
    total_received = sum(row["lbs"] or 0 for row in data_weft)
    total_received_meter = sum(row["meter"] or 0 for row in data_weft)
    total_return = sum(row["return"] or 0 for row in data_weft)
    total_received_weft = sum(row["lbs"] or 0 for row in data_weft if row["purpose"] == "Weft")
    total_received_weft_meter = sum(row["meter"] or 0 for row in data_weft if row["purpose"] == "Weft")

    # Add total row for weft
    if data_weft:
        data_weft.append({
            "posting_date": "<b>Total Weft Received</b>",
            "gate_pass": "",
            "yarn_item": "Weft: " + str(round(total_received_weft, 2)),
            "brand": "",
            "bags": "",
            "lbs": "<b>" + str(round(total_received, 2)) + "</b>",
            "meter": "<b>" + str(round(total_received_meter, 2)) + " Mtr</b>",
            "purpose": "",
            "yarn_count": "",
            "return": "<b>" + str(round(total_return, 2)) + "</b>"
        })
      
    data.extend(data_warp)
    data.extend(data_weft)


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
        "posting_date": "<b>Delivery Note </b>",
        "gate_pass": "",
        "yarn_item": "",
        "brand": "",
        "bags": "",
        "lbs": "",
        "purpose": "",
        "yarn_count": ""
    })
    delivery_note_data = frappe.db.sql(f"""
        SELECT
            dn.posting_date,
            dn.name as gate_pass,
            dn.fabric_item AS yarn_item,
            dni.qty AS meter
        FROM
            `tabDelivery Note` dn
        LEFT JOIN
            `tabDelivery Note Item` dni
        ON dn.name = dni.parent
        WHERE
            dn.docstatus = 1
            {delivery_note_conditions}
        ORDER BY
            dn.name, dni.idx
        """, filters, as_dict=True)
    
    if delivery_note_data:
        delivery_note_data.append({
            "posting_date": "<b>Total</b>",
            "gate_pass": "",
            "yarn_item": "",
            "brand": "",
            "bags": "",
            "lbs": "",
           "meter": "<b>" + str(sum(row["meter"] or 0 for row in delivery_note_data)) + "</b>"
        })

    data.extend(delivery_note_data)
	  # Warp Weft Detail
    data.append({
        "posting_date": "",
        "gate_pass": "Fabric Item",
        "yarn_item": "",
        "brand": "",
        "bags": "Warp Qty",
        "lbs": "Weft Qty",
        "purpose": "",
        "yarn_count": ""
    })

    delivery_data = frappe.db.sql(f"""
        SELECT
            "" as posting_date,
            "" as gate_pass,
            dn.fabric_item as gate_pass,
            "" as yarn_item,
            SUM(CASE WHEN bid.for = 'Warp' THEN bid.yarn_qty ELSE 0 END) as bags,
            SUM(CASE WHEN bid.for = 'Weft' THEN bid.yarn_qty ELSE 0 END) as lbs
        FROM
            `tabDelivery Note` dn
        LEFT JOIN
            `tabBOM Items Dn` bid ON dn.name = bid.parent
        WHERE
            dn.docstatus = 1 {delivery_conditions}
        GROUP BY
            dn.fabric_item
    """, filters, as_dict=True)

    total_warp = sum(row["bags"] or 0 for row in delivery_data)
    total_weft = sum(row["lbs"] or 0 for row in delivery_data)
    if delivery_data:
        # delivery_data.append({
        #         "posting_date": "<b>Warp + Weft(Customer Ratio)</b>",
        #         "yarn_item": "",
        #         "purpose": "",
        #         "brand": "",
        #         "bags": "",
        #         "lbs": "<b>" + str(round((total_warp) + (total_weft), 2)) + "</b>",
        #         "gate_pass": ""
        #     })
    
        delivery_data.append({
            "posting_date": "<b>Yarn Balance(Customer)</b>",
            "yarn_item": "",
            "purpose": "",
            "brand": "",
            "bags": "<b>" + str(round(warp_opening + total_received_warp - total_warp, 2) if total_received_warp > 0 else 0) + "</b>",
            "lbs": "<b>" + str(round(weft_opening + total_received_weft - total_weft, 2)) + "</b>",
            "meter": "<b>" + str(
        round(
            total_received_meter_warp - round(
                delivery_fabric_qty[0].yarn_item if (delivery_fabric_qty and delivery_fabric_qty[0].yarn_item) else 0,
                2
            ),
            2
        ) if total_received_meter_warp > 0 else 0
    ) + " Mtr</b>",
    "gate_pass": ""
        })
        

    data.extend(delivery_data)
    return columns, data





