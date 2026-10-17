import frappe


@frappe.whitelist()
def get_sizing_receipts_for_supplier(supplier):
	"""Called by the "Get Charges From Sizing Receipt" button on Purchase
	Invoice. Returns every submitted Sizing Receipt whose Sizing Program
	was raised against this supplier, excluding any Sizing Receipt already
	pulled into another (non-cancelled) Purchase Invoice - matched via the
	custom_sizing_receipt field on Purchase Invoice Item rather than any
	field on Sizing Receipt itself, so nothing needs to be written back
	onto Sizing Receipt to track this.
	"""
	if not supplier:
		return []

	return frappe.db.sql(
		"""
		SELECT
			sr.name,
			sr.item AS beam_item,
			sr.yarn_item,
			sr.lbs,
			sr.sizing_rate,
			sr.sizing_program
		FROM `tabSizing Receipt` sr
		INNER JOIN `tabSizing Program` sp ON sp.name = sr.sizing_program
		WHERE sp.supplier = %(supplier)s
			AND sr.docstatus = 1
			AND sr.name NOT IN (
				SELECT pii.custom_sizing_receipt
				FROM `tabPurchase Invoice Item` pii
				INNER JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
				WHERE pii.custom_sizing_receipt IS NOT NULL
					AND pii.custom_sizing_receipt != ''
					AND pi.docstatus < 2
			)
		ORDER BY sr.creation DESC
		""",
		{"supplier": supplier},
		as_dict=True,
	)
