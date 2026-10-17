import frappe

@frappe.whitelist()
def fetch_current_stock(item_code, warehouse, set_no=None, posting_date=None, posting_time=None):
    """
    Fetch current stock for a given item and warehouse.
    - If set_no (Batch) is provided, fetch batch_qty from Batch (after validating item_code).
    - Otherwise, fetch latest stock from Stock Ledger Entry up to the posting_date.
    """
    try:
        if set_no:
            # Validate that the batch exists and matches the item
            batch_item = frappe.db.get_value("Batch", set_no, "item")
            if batch_item != item_code:
                frappe.throw(f"Batch {set_no} does not belong to item {item_code}")
            
            batch_qty = frappe.db.get_value("Batch", set_no, "batch_qty")
            return batch_qty or 0

        else:
            # Build query based on whether posting_date is provided
            if posting_date and posting_time:
                query = """
                    SELECT qty_after_transaction AS current_stock,
                           valuation_rate as rate
                    FROM `tabStock Ledger Entry`
                    WHERE item_code = %s 
                      AND warehouse = %s 
                      AND is_cancelled = 0
                      AND posting_date <= %s
                      AND posting_time <= %s
                    ORDER BY posting_date DESC, posting_time DESC, creation DESC
                    LIMIT 1
                """
                params = (item_code, warehouse, posting_date, posting_time)
            else:
                query = """
                    SELECT qty_after_transaction AS current_stock,
                           valuation_rate as rate
                    FROM `tabStock Ledger Entry`
                    WHERE item_code = %s 
                      AND warehouse = %s 
                      AND is_cancelled = 0
                    ORDER BY posting_date DESC, posting_time DESC, creation DESC
                    LIMIT 1
                """
                params = (item_code, warehouse)
            
            result = frappe.db.sql(query, params, as_dict=True)
            
            if result:
                return {
                    "current_stock": result[0].get("current_stock", 0),
                    "rate": result[0].get("rate", 0)
                }
            else:
                return {
                    "current_stock": 0,
                    "rate": 0
                }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in fetch_current_stock")
        frappe.throw(f"Failed to fetch stock: {str(e)}")