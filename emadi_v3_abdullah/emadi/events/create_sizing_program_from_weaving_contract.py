import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def create_sizing_program_from_weaving_contract(weaving_contract, item=None, beam_for=None):
	"""Called by the "Sizing Program" button on a submitted, Open Weaving
	Contract. The button first shows the user a popup listing every
	Pile/Ground row in that contract's BOM Items (client-side, from the
	already-loaded form) and asks them to pick one; `item` is that row's
	Yarn Count (an Item link) and `beam_for` is that row's "for" value
	(Pile or Ground) - sent back here just to disambiguate two rows that
	happen to share the same yarn item.

	Returns a brand-new, unsaved Sizing Program - same "server pre-fills,
	user reviews and saves" pattern used everywhere else in this app - with
	the Weaving Contract and Sales Order references set, ready to flow on
	to Sizing Receipt when it's eventually created from this Sizing
	Program via the existing "Create > Sizing Receipt" button.
	"""
	wc = frappe.get_doc("Weaving Contract", weaving_contract)

	row = _pick_bom_row(wc, item, beam_for)
	if not row:
		frappe.throw(
			_("No Pile/Ground item with a Yarn Count found in this Weaving Contract's BOM Items.")
		)

	# Sizing Program covers the whole pending LBS of this Pile/Ground yarn:
	# every BOM row of the same yarn is added together, minus what earlier
	# Sizing Programs already took.
	pending = _get_pending(wc, row.get("for"), row.get("yarn_count"))
	if pending["pending"] <= 0.001:
		frappe.throw(
			_("A Sizing Program has already been created for the full LBS of {0} ({1}).").format(
				row.get("yarn_count"), row.get("for")
			)
		)

	sizing_program = frappe.new_doc("Sizing Program")
	sizing_program.weaving_contract = wc.name
	sizing_program.sales_order = wc.get("sales_order")
	sizing_program.weaver = _get_weaver(wc)
	sizing_program.fabric_construction = wc.get("construction")
	# "Quality" mirrors Fabric Construction here, same as the Quality/Article
	# pairing used when Fabric Construction records are auto-created from the
	# Towel Costing Sheet (see towel-costing-multi-article.md) - flagged as a
	# judgment call, not an explicit spec.
	sizing_program.quality = wc.get("construction")
	# "Brand" - the yarn item picked in the popup.
	sizing_program.item = row.get("yarn_count")
	sizing_program.lbs_issue = pending["pending"]
	# "Item Name" (item_returnable) - the Beam item this same Weaving Contract
	# already auto-created on its own submit (create_beam_items in
	# weaving_contract.py uses the identical BEAM-{for}-{yarn_count} naming),
	# so it's guaranteed to exist by the time this button is clickable
	# (docstatus == 1). Flagged as a judgment call.
	beam_item_code = _beam_item_code(row.get("for"), row.get("yarn_count"))
	if frappe.db.exists("Item", beam_item_code):
		sizing_program.item_returnable = beam_item_code

	return sizing_program


def _beam_item_code(beam_for, yarn_count):
	return f"BEAM-{beam_for}-{yarn_count}"


def _get_pending(wc, beam_for, yarn_count):
	"""Total LBS of this (Pile/Ground, yarn) across the contract's BOM Items,
	how much existing Sizing Programs already issued, and what is left."""
	total = sum(
		flt(r.get("yarn_qty"))
		for r in wc.bom_items or []
		if r.get("for") == beam_for and (r.get("yarn_count") or "").strip() == (yarn_count or "").strip()
	)
	issued = frappe.db.sql(
		"""
		select coalesce(sum(lbs_issue), 0)
		from `tabSizing Program`
		where weaving_contract = %s and item = %s and item_returnable = %s and docstatus != 2
		""",
		(wc.name, yarn_count, _beam_item_code(beam_for, yarn_count)),
	)[0][0]
	return {"total": total, "issued": flt(issued), "pending": max(0.0, total - flt(issued))}


@frappe.whitelist()
def get_sizing_program_items(weaving_contract):
	"""Pile/Ground yarns that still need a Sizing Program, for the popup. The
	same yarn on several BOM rows is listed once with the rows' LBS added
	together; a yarn drops out once its full LBS has a Sizing Program."""
	wc = frappe.get_doc("Weaving Contract", weaving_contract)
	seen = []
	out = []
	for r in wc.bom_items or []:
		key = (r.get("for"), (r.get("yarn_count") or "").strip())
		if r.get("for") not in ("Pile", "Ground") or not key[1] or key in seen:
			continue
		seen.append(key)
		data = _get_pending(wc, *key)
		if data["pending"] > 0.001:
			out.append({"for": key[0], "yarn_count": key[1], **data})
	return out


def _pick_bom_row(wc, item, beam_for):
	rows = [r for r in (wc.bom_items or []) if r.get("for") in ("Pile", "Ground") and r.get("yarn_count")]

	if item:
		for r in rows:
			if r.get("yarn_count") == item and (not beam_for or r.get("for") == beam_for):
				return r

	return rows[0] if rows else None


def _get_weaver(wc):
	"""Weaving Contract doesn't carry an explicit "weaver"/"customer" field
	in the schema seen so far, so this falls back to the Customer on the
	linked Sales Order. Flagged - if Weaving Contract does have its own
	weaver/customer field under a different name, say so and this can read
	straight from that instead.
	"""
	weaver = wc.get("weaver") or wc.get("customer")
	if weaver:
		return weaver
	if wc.get("sales_order"):
		return frappe.db.get_value("Sales Order", wc.sales_order, "customer")
	return None
