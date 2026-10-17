import frappe

def execute(filters=None):
    data = []
    columns = [
        {"label": "Quality", "fieldname": "quality", "fieldtype": "Data", "width": 120},
        {"label": "Yarn Count", "fieldname": "yarn_count", "fieldtype": "Data", "width": 120},
         {"label": "Meter", "fieldname": "yarn_qty", "fieldtype": "Float", "width": 120},
        {"label": "Lbs", "fieldname": "yarn", "fieldtype": "Float", "width": 120}
    ]
     # Return empty data if no filters are applied
    if not filters or not filters.get("fabric_item"):
        return columns, []

    quality_filters = ""
    if filters.get("fabric_item"):
        qualities = ", ".join([f"'{q}'" for q in filters.get("fabric_item")])
        quality_filters += f" AND fp.fabric_item IN ({qualities})"
    sizing_program_conditions = ""
    if filters.get("fabric_item"):
        sizing_program_conditions += f" AND spi.fabric_construction IN ({qualities})"
    opening_qty_filter = ""
    if filters.get("fabric_item"):
        opening_qty_filter += f" AND sri.item_code IN ({qualities})"

 # opening qty
    data.append({
        "quality": "Opening Qty",
        "yarn_count": "",
        "yarn": "",
        "yarn_qty": ""
    })
    opening_qty_yarn = frappe.db.sql(f"""
    SELECT 
        sri.item_code as quality,
        SUM(sri.qty) as yarn_qty
    FROM `tabStock Reconciliation Item` sri
    LEFT JOIN `tabStock Reconciliation` sr ON sri.parent = sr.name
    WHERE
        sr.docstatus = 1
        {opening_qty_filter}
    GROUP BY
        sri.item_code
    """, filters, as_dict=True)
    opening_qty_yarn_total = sum(row["yarn_qty"] or 0 for row in opening_qty_yarn)
    data.append({
        "quality": "Total",
        "yarn_count": "",
        "yarn_qty": round(opening_qty_yarn_total, 2)
    })

    #__Sizing Program__
    data.append({
        "quality": "Sizing Program",
        "yarn_count": "",
        "yarn": "",
        "yarn_qty": ""
    })

    sizing_program_data = frappe.db.sql(f"""
        SELECT
            spi.fabric_construction AS quality,
            spi.item AS yarn_count,
            ROUND(SUM(spi.lbs), 5) AS yarn,
            ROUND(SUM(spi.length), 5) AS yarn_qty
        FROM
            `tabSizing Program` AS sp
        LEFT JOIN
            `tabSizing Program Item` AS spi ON sp.name = spi.parent
        WHERE
            sp.docstatus = 1
            {sizing_program_conditions}
        GROUP BY
            spi.item,
            spi.fabric_construction
    """, filters, as_dict=True)

    total_warp = sum(row["yarn"] or 0 for row in sizing_program_data)
    total_production_length = sum(row["yarn_qty"] or 0 for row in sizing_program_data)
    ratio = total_warp / total_production_length if total_production_length else 0

    if sizing_program_data:
        sizing_program_data.append({
            "quality": "<b>Total Warp</b>",
            "yarn_count": f"Ratio: {ratio}",
            "yarn": "<b>" + str(round(total_warp, 2)) + "</b>",
            "yarn_qty":"<b>" + str(round(total_production_length, 2)) + " Mtr</b>"
        })

    data.extend(sizing_program_data)

    # ── Fetch Data CLOTH ─────────────────────────────
    cloth_data = frappe.db.sql(f"""
        SELECT
            SUM(fpi.yarn_qty) as yarn_qty,
            fp.fabric_item AS quality,
            fpi.yarn_count,
            SUM(fpi.yarn_qty) * {ratio} as yarn

        FROM
            `tabFabric Production Item` fpi
        INNER JOIN
            `tabFabric Production` fp
            ON fpi.parent = fp.name
        LEFT JOIN
            `tabItem` i
            ON i.name = fp.fabric_item
        WHERE
            fp.docstatus = 1
            AND fpi.`for` = 'Warp'
            {quality_filters}
        GROUP BY
            fp.fabric_item
        ORDER BY
            fp.posting_date DESC, fpi.name ASC
    	""", filters, as_dict=True)
 	
    # Totals
    total_yarn_qty_cloth = sum((row.get("yarn_qty") or 0) for row in cloth_data)

    # ── Prepare Data ─────────────────────────────
  

    # Header row
    data.append({
        "quality": "CLOTH",
        "yarn_count": "",
        "yarn_qty": ""
    })

    # Main data
    data.extend(cloth_data)

    data.append({
        "quality": "Total",
        "yarn_count": "",
        "yarn_qty": round(total_yarn_qty_cloth, 2)
    })


    # ── Fetch Data YARN ─────────────────────────────
    yarn_data = frappe.db.sql(f"""
        SELECT
            SUM(fpi.yarn_qty) as yarn,
            fp.fabric_item AS quality,
            fpi.yarn_count
        FROM
            `tabFabric Production Item` fpi
        INNER JOIN
            `tabFabric Production` fp
            ON fpi.parent = fp.name
        LEFT JOIN
            `tabItem` i
            ON i.name = fp.fabric_item
        WHERE
            fp.docstatus = 1
            AND fpi.`for` = 'Weft'
            {quality_filters}
        GROUP BY
            fpi.yarn_count,
            fp.fabric_item
        ORDER BY
            fp.posting_date DESC, fpi.name ASC
          
    	""", filters, as_dict=True)
 	
    # # Totals
    total_meter_yarn = sum((row.get("yarn") or 0) for row in yarn_data)

    # ── Prepare Data ─────────────────────────────

    #Header row
    data.append({
        "quality": "YARN",
        "yarn_count": "",
        "yarn_qty": ""
    })

    # Main data
    data.extend(yarn_data)

    data.append({
        "quality": "Total",
        "yarn_count": "",
        "yarn_qty": round(total_meter_yarn, 2)
    })

    return columns, data