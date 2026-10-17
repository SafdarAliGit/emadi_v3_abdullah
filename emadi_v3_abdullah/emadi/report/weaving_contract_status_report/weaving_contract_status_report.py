
import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	columns = [
		{"label": "Contract No", "fieldname": "contract_name", "fieldtype": "Link", "options": "Weaving Contract", "width": 120},
        {"label": "Weaver", "fieldname": "weaver", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": "Construction", "fieldname": "construction", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Fabric Qty", "fieldname": "fabric", "fieldtype": "Data", "width": 100},
        {"label": "Yarn Count", "fieldname": "yarn_count", "fieldtype": "Data", "width": 100},
        {"label": "Consumption Per LbS", "fieldname": "consumption", "fieldtype": "Data", "width": 140},
        {"label": "Yarn Required", "fieldname": "required", "fieldtype": "Data", "width": 120},
        {"label": "Yarn Received", "fieldname": "received", "fieldtype": "Data", "width": 120},
        {"label": "Yarn Consumed", "fieldname": "consumed", "fieldtype": "Data", "width": 120},
        {"label": "Balance Yarn", "fieldname": "balance_yarn", "fieldtype": "Data", "width": 120},
        {"label": "Balance Fabric", "fieldname": "balance_fabric", "fieldtype": "Data", "width": 120}
    ]
	return columns

def get_conditions(filters):
    conditions = ""
    if filters.get("weaver"):
        conditions += " AND wc.weaver = %(weaver)s"
    if filters.get("construction"):
        conditions += " AND wc.construction = %(construction)s"
    if filters.get("weaving_contract"):
        conditions += " AND wc.name = %(weaving_contract)s"
    if filters.get("date_from"):
        conditions += " AND wc.date >= %(date_from)s"
    if filters.get("date_to"):
        conditions += " AND wc.date <= %(date_to)s"
    return conditions


def get_data(filters):
    conditions = get_conditions(filters)
    data = []

    query = f"""
        SELECT 
    wc.name AS contract_name,
    wc.weaver,
    wc.construction,    
    wc.fabric_qty AS fabric,
    bom_item.yarn_count,
    bom_item.consumption,
    bom_item.yarn_qty AS required,
    sed.qty AS received,
    bom_item_dn.consumed,
    (IFNULL(sed.qty, 0) - IFNULL(dni.qty, 0)) AS balance_yarn,
    (IFNULL(wc.fabric_qty, 0) - IFNULL(dni.qty, 0)) AS balance_fabric
    FROM `tabWeaving Contract` AS wc
    JOIN `tabBOM Items` AS bom_item ON bom_item.parent = wc.name
    LEFT JOIN ( 
        SELECT weaving_contract, SUM(IFNULL(yarn_qty, 0)) AS consumed 
        FROM `tabBOM Items Dn` 
        GROUP BY weaving_contract  
    ) bom_item_dn ON bom_item_dn.weaving_contract = wc.name
    LEFT JOIN ( 
        SELECT sed.weaving_contract, SUM(IFNULL(sed.qty, 0)) AS qty 
        FROM `tabStock Entry Detail` AS sed
        JOIN `tabStock Entry` AS se ON se.name = sed.parent
        WHERE se.docstatus = 1 
        GROUP BY sed.weaving_contract
    ) sed ON sed.weaving_contract = wc.name
    LEFT JOIN ( 
        SELECT custom_weaving_contract, SUM(IFNULL(qty, 0)) AS qty 
        FROM `tabDelivery Note Item` 
        GROUP BY custom_weaving_contract  
    ) dni ON dni.custom_weaving_contract = wc.name
    WHERE 
    wc.docstatus = 1
    {conditions}

    """

    data = frappe.db.sql(query, filters, as_dict=True)
    # TO REMOVE DUPLICATES
    keys_to_check = ['contract_name', 'weaver', 'construction','fabric']
    seen_values = []

    for entry in data:
        key_values = tuple(entry[key] for key in keys_to_check)

        if key_values in seen_values:
            for key in keys_to_check:
                entry[key] = None
        else:
            seen_values.append(key_values)

    # END
    return data