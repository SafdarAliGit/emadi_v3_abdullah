import frappe
from frappe import _


def create_fabric_construction_records(towel_costing_sheet):
	"""Called from Towel Costing Sheet's on_submit. One Fabric Construction
	record per Article (Finish Item Towel Costing row), built from that
	Article's own rows in the Materials table (Towel Costing Sheet Raw
	Material):

	  Fabric Construction.quality      = Article
	  Fabric Construction.fabric_item  = Article
	  Fabric Construction Item.for         = Towel Costing Sheet Raw Material.for
	  Fabric Construction Item.yarn_count  = Towel Costing Sheet Raw Material.raw_material
	  Fabric Construction Item.consumption = Towel Costing Sheet Raw Material.yarn_required_in_lbs

	"for" is copied through as-is (Pile/Weft/Fancy/Ground) per your call on
	the mapping question - Fabric Construction Item's Select options were
	widened to include all four alongside the existing Warp/Weft (see the
	doctype JSON). Flagging again since it's a real downstream effect, not
	just a schema note: Daily Fabric Production's existing
	get_target_warehouse-style routing only recognises "Warp"/"Weft" - a
	Pile/Fancy/Ground row created here won't get a warehouse picked for it
	by that flow unless it's updated separately to handle the other two
	categories.

	Never blocks submission - an Article that already has a Fabric
	Construction (matched by quality) is skipped and just reported, not
	overwritten, since Fabric Construction is a pre-existing doctype with
	its own real usage elsewhere (Daily Fabric Production) and may already
	be submitted - safer to leave an existing record alone than silently
	rewrite it. Say the word if you want existing records updated in place
	instead.
	"""
	created = []
	existing = []
	skipped_no_materials = []

	articles = [d.article for d in (towel_costing_sheet.finish_item_towel_costing or []) if d.article]

	for article in articles:
		if frappe.db.exists("Fabric Construction", {"quality": article}):
			existing.append(article)
			continue

		rows = [m for m in (towel_costing_sheet.materials or []) if m.item == article]
		if not rows:
			skipped_no_materials.append(article)
			continue

		fc = frappe.new_doc("Fabric Construction")
		fc.name_prefix = "FC"
		fc.quality = article
		fc.fabric_item = article

		for m in rows:
			fc.append(
				"fabric_construction_item",
				{
					"for": m.get("for"),
					"yarn_count": m.raw_material,
					"consumption": m.yarn_required_in_lbs,
				},
			)

		fc.insert(ignore_permissions=True)
		created.append(fc.name)

	if created:
		frappe.msgprint(
			_("Fabric Construction created: {0}").format(", ".join(created)),
			alert=True,
			indicator="green",
		)
	if existing:
		frappe.msgprint(
			_("Fabric Construction already exists for: {0}").format(", ".join(existing)),
			alert=True,
			indicator="blue",
		)
	if skipped_no_materials:
		frappe.msgprint(
			_("No Raw Material rows found for: {0} - no Fabric Construction created.").format(
				", ".join(skipped_no_materials)
			),
			alert=True,
			indicator="orange",
		)
