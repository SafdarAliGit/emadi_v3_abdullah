import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    columns = [
        {"label": "Transaction #", "fieldname": "stock_entry_name", "fieldtype": "Data", "width": 150},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Fabric Item", "fieldname": "fabric_item", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label":"Consumption", "fieldname": "consumption", "fieldtype": "Float", "width": 120, "precision": 4},
        {"label": "For", "fieldname": "about", "fieldtype": "Data", "width": 120},
        {"label": "Target Warehouse", "fieldname": "t_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"label": "Fabric Qty", "fieldname": "fabric_qty", "fieldtype": "Data", "width": 120},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Data", "width": 120},
        {"label": "Bags", "fieldname": "bags", "fieldtype": "Data", "width": 120},
        {"label": "Customer Brand", "fieldname": "brand", "fieldtype": "Data", "width": 120}
    ]
    return columns


def get_conditions_se(filters, doctype):
    conditions = []

    if filters.get("from_date"):
        conditions.append(f"`{doctype}`.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append(f"`{doctype}`.posting_date <= %(to_date)s")
    if filters.get("brand"):
        conditions.append(f"`sed`.brand = %(brand)s")
    if filters.get("item_code"):
        conditions.append(f"`sed`.item_code = %(item_code)s")
    return " AND ".join(conditions) if conditions else "1=1"

def get_conditions_dn(filters, doctype):
    conditions = []

    if filters.get("from_date"):
        conditions.append(f"`{doctype}`.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append(f"`{doctype}`.posting_date <= %(to_date)s")
    if filters.get("brand"):
        conditions.append(f"`dni`.brand = %(brand)s")
    if filters.get("item_code"):
        conditions.append(f"`dni`.yarn_count = %(item_code)s")
    return " AND ".join(conditions) if conditions else "1=1"

def get_conditions_return(filters):
    return_conditions = ["frc.docstatus = 1"]

    if filters.get("from_date"):
        return_conditions.append("frc.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        return_conditions.append("frc.posting_date <= %(to_date)s")
    if filters.get("customer"):
        return_conditions.append("frc.customer = %(customer)s")
    if filters.get("item_code"):
        return_conditions.append("frci.yarn_count = %(item_code)s")

    # Return same way as first function — as SQL-safe condition string and value dict
    return " AND ".join(return_conditions) if return_conditions else "1=1"



def get_opening_qty(filters):
    from_date = filters.get("from_date")
    yarn_count = filters.get("item_code")  # previously item_code

    # 1. Stock Entry Detail
    opening_stock = frappe.db.sql("""
        SELECT
            COALESCE(SUM(CASE WHEN se.stock_entry_type = 'Material Receipt' THEN sed.qty ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN se.stock_entry_type = 'Material Issue' THEN sed.qty ELSE 0 END), 0) AS qty_receipt
        FROM
            `tabStock Entry Detail` sed
        JOIN
            `tabStock Entry` se ON se.name = sed.parent
        WHERE
            sed.item_code = %(yarn_count)s
            AND se.posting_date < %(from_date)s
            AND se.docstatus = 1
    """, {
        "yarn_count": yarn_count,
        "from_date": from_date
    }, as_dict=1)

    qty_receipt = opening_stock[0].qty_receipt if opening_stock else 0

    # 2. BOM Items Dn (child of Delivery Note)
    total_yarn_qty = frappe.db.sql("""
        SELECT COALESCE(SUM(bom.yarn_qty), 0) AS total_yarn_qty
        FROM `tabBOM Items Dn` bom
        JOIN `tabDelivery Note` dn ON dn.name = bom.parent
        WHERE
            bom.yarn_count = %(yarn_count)s
            AND dn.posting_date < %(from_date)s
            AND dn.docstatus = 1
    """, {
        "yarn_count": yarn_count,
        "from_date": from_date
    }, as_dict=1)
    consumption = total_yarn_qty[0].total_yarn_qty if total_yarn_qty else 0
    final_opening_qty = qty_receipt - consumption
    return final_opening_qty



# def get_opening_qty(filters):
#     from_date = filters.get("from_date")
#     brand = filters.get("brand")
#     yarn_count = filters.get("item_code")  # previously item_code

#     if not (from_date and yarn_count and brand):
#         return 0

#     # 1. Stock Entry Detail
#     opening_stock = frappe.db.sql("""
#         SELECT
#             COALESCE(SUM(CASE WHEN se.stock_entry_type = 'Material Receipt' THEN sed.qty ELSE 0 END), 0) -
#             COALESCE(SUM(CASE WHEN se.stock_entry_type = 'Material Issue' THEN sed.qty ELSE 0 END), 0) AS qty_receipt
#         FROM
#             `tabStock Entry Detail` sed
#         JOIN
#             `tabStock Entry` se ON se.name = sed.parent
#         WHERE
#             sed.item_code = %(yarn_count)s
#             AND sed.brand = %(brand)s
#             AND se.posting_date < %(from_date)s
#             AND se.docstatus = 1
#     """, {
#         "yarn_count": yarn_count,
#         "brand": brand,
#         "from_date": from_date
#     }, as_dict=1)

#     qty_receipt = opening_stock[0].qty_receipt if opening_stock else 0

#     # 2. BOM Items Dn (child of Delivery Note)
#     total_yarn_qty = frappe.db.sql("""
#         SELECT COALESCE(SUM(bom.yarn_qty), 0) AS total_yarn_qty
#         FROM `tabBOM Items Dn` bom
#         JOIN `tabDelivery Note` dn ON dn.name = bom.parent
#         WHERE
#             bom.yarn_count = %(yarn_count)s
#             AND bom.brand = %(brand)s
#             AND dn.posting_date < %(from_date)s
#             AND dn.docstatus = 1
#     """, {
#         "yarn_count": yarn_count,
#         "brand": brand,
#         "from_date": from_date
#     }, as_dict=1)
#     consumption = total_yarn_qty[0].total_yarn_qty if total_yarn_qty else 0
#     final_opening_qty = qty_receipt - consumption
#     return final_opening_qty


def get_data(filters):
    data = []
    opening_qty = get_opening_qty(filters)
    opening_row = [{"posting_date": "", "stock_entry_name": "<span style='font-weight: bold;'>Opening Stock</span>", "item_code": "", "qty": opening_qty, "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": "", "consumption": ""}]
    data.extend(opening_row)
    weaving_stock = """SELECT 
            se.posting_date,
            se.name AS stock_entry_name,
            sed.item_code,
            (CASE WHEN se.stock_entry_type = 'Material Receipt' THEN sed.qty ELSE sed.qty * -1 END) AS qty,
            sed.for AS about,
            sed.t_warehouse,
            '' AS fabric_item,
            '' AS fabric_qty,
            '' AS consumption,
            sed.qty_pcs AS bags,
            sed.custom_customer_brand AS brand

        FROM 
            `tabStock Entry` se
        LEFT JOIN 
            `tabStock Entry Detail` sed ON se.name = sed.parent
        WHERE 
            se.docstatus = 1
            AND
            se.stock_entry_type IN ('Material Receipt', 'Material Issue')
            AND
            {conditions}
        ORDER BY 
            se.posting_date
    """.format(conditions=get_conditions_se(filters, "se"))
    
    weaving_stock_result = frappe.db.sql(weaving_stock, filters, as_dict=1)


    total_qty_se = 0
    for i in weaving_stock_result:
        total_qty_se += i.get('qty',0)

    opening_qty = get_opening_qty(filters)

    weaving_stock_heading = [{"posting_date": "", "stock_entry_name": "<span style='font-size: 14px;font-weight: bold;'>Stock Entry</span>", "item_code": "", "qty": "", "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": "", "consumption": ""}]
    weaving_stock_result = weaving_stock_heading + weaving_stock_result
    weaving_stock_total = [{"posting_date": "", "stock_entry_name": "<span style='font-weight: bold;'>Total Qty</span>", "item_code": "", "qty": total_qty_se + opening_qty, "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": "", "consumption": ""}]

    weaving_stock_result.extend(weaving_stock_total)
    

    dn_stock = """SELECT 
            dn.posting_date,
            dn.name AS stock_entry_name,
            dn.fabric_item,
            dn.fabric_qty,
            dni.yarn_count AS item_code,
            dni.consumption,
            dni.yarn_qty AS qty,
            dni.for AS about,
            '' AS t_warehouse,
            '' AS bags,
            '' AS brand

        FROM 
            `tabDelivery Note` dn
        LEFT JOIN 
            `tabBOM Items Dn` dni ON dn.name = dni.parent
        WHERE 
            dn.docstatus = 1
            AND
            {conditions}
        ORDER BY 
            dn.posting_date
    """.format(conditions=get_conditions_dn(filters, "dn"))

    dn_stock_result = frappe.db.sql(dn_stock, filters, as_dict=1)
    total_qty_dn = 0
    for i in dn_stock_result:
        total_qty_dn += i.get('qty',0)

    dn_stock_heading = [{"posting_date": "", "stock_entry_name": "<span style='font-size: 14px;font-weight: bold;'>Delivery Note</span>", "item_code": "", "qty": "", "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": "", "consumption": ""}]
    dn_stock_result = dn_stock_heading + dn_stock_result
    dn_stock_total = [{"posting_date": "", "stock_entry_name": "<span style='font-weight: bold;'>Total Qty</span>", "item_code": "", "qty": total_qty_dn, "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": '', "consumption": ""}]
    dn_stock_result.extend(dn_stock_total)

    fabric_return = [{"posting_date": "", "stock_entry_name": "<span style='font-size: 14px;font-weight: bold;'>Fabric Return</span>", "item_code": "", "qty": "", "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": "", "consumption": ""}]
    dn_stock_result.extend(fabric_return)

    stock_balance_row = [{"posting_date": "", "stock_entry_name": "<span style='font-size: 12px;font-weight: bold;'>Stock Balance</span>", "item_code": "", "qty":  (total_qty_se + opening_qty) - total_qty_dn , "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": "", "consumption": ""}]

    fabric_return_query = """
    SELECT
        frc.name AS stock_entry_name,
        frc.posting_date,
        frc.customer,
        frc.fabric_item,
        frc.qty AS fabric_qty,
        frci.yarn_count AS item_code,
        frci.yarn_qty AS qty
    FROM
        `tabFabric Return Conversion` AS frc
    INNER JOIN
        `tabFabric Return Conversion Item` AS frci
        ON frci.parent = frc.name
    WHERE
        {conditions_return}
    ORDER BY
        frc.posting_date DESC
    """.format(conditions_return=get_conditions_return(filters))

    fabric_return_result = frappe.db.sql(
        fabric_return_query,
        filters,
        as_dict=1
    )


    total_qty_fabric_return = 0
    total_qty = 0
    for i in fabric_return_result:
        total_qty_fabric_return += i.get('fabric_qty',0)
        total_qty += i.get('qty',0)

    fabric_return_total = [{"posting_date": "", "stock_entry_name": "<span style='font-weight: bold;'>Total Qty</span>", "item_code": "", "qty": total_qty, "about": "", "t_warehouse": "", "fabric_item": "", "fabric_qty": total_qty_fabric_return, "consumption": ""}]
    fabric_return_result.extend(fabric_return_total)
    
    stock_balance_row[0]['qty'] += total_qty
    data.extend(weaving_stock_result)
    data.extend(dn_stock_result)
    data.extend(fabric_return_result)
    data.extend(stock_balance_row)  
    return data


