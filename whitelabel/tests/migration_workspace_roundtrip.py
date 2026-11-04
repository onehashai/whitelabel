"""Full migration regression. Run only on a disposable .test site with allow_tests."""

import json

import frappe

from whitelabel import workspace_protection as protection

NAMES = ("_WL Migration Protected A", "_WL Migration Protected B", "_WL Migration Opted Out")
CARD = "_WL Migration Card"
BLOCK = "_WL Migration Block"
PROFILE = "_WL Migration Navigation Profile"


def _connect(site):
	frappe.init(site)
	frappe.connect()
	frappe.set_user("Administrator")


def run():
	site = frappe.local.site
	if not frappe.conf.allow_tests or not (site.endswith(".test") or site.startswith("test_")):
		raise RuntimeError("Use a disposable .test site with allow_tests enabled.")
	if frappe.conf.developer_mode:
		raise RuntimeError("Disable developer_mode to avoid exporting regression fixtures into app source.")
	frappe.set_user("Administrator")
	protection.ensure_protection_field()
	if frappe.db.exists("Whitelabel Navigation Profile", PROFILE):
		frappe.delete_doc("Whitelabel Navigation Profile", PROFILE)
	for name in NAMES:
		if frappe.db.exists("Workspace", name):
			frappe.delete_doc("Workspace", name, force=True)
	for doctype, name in (("Number Card", CARD), ("Custom HTML Block", BLOCK)):
		if frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, force=True)
	frappe.get_doc(
		{
			"doctype": "Number Card",
			"name": CARD,
			"label": CARD,
			"type": "Document Type",
			"document_type": "User",
			"function": "Count",
			"filters_json": "[]",
			"is_public": 1,
		}
	).insert()
	frappe.get_doc(
		{"doctype": "Custom HTML Block", "name": BLOCK, "html": "<p>Preserve this block</p>", "private": 0}
	).insert()
	for name in NAMES:
		frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": name,
				"title": name,
				"module": "Core",
				"public": 1,
				"content": json.dumps(
					[
						{"id": "title", "type": "header", "data": {"text": name, "col": 12}},
						{"id": "card", "type": "number_card", "data": {"number_card_name": CARD, "col": 6}},
						{
							"id": "block",
							"type": "custom_block",
							"data": {"custom_block_name": BLOCK, "col": 12},
						},
					]
				),
				"number_cards": [{"number_card_name": CARD, "label": CARD}],
				"custom_blocks": [{"custom_block_name": BLOCK}],
				"roles": [{"role": "Desk User"}],
			}
		).insert()
	opted_out = frappe.get_doc("Workspace", NAMES[2])
	opted_out.set(protection.PROTECTION_FIELD, 0)
	opted_out.save()
	profile = frappe.get_doc(
		{
			"doctype": "Whitelabel Navigation Profile",
			"title": PROFILE,
			"enabled": 1,
			"default_workspace": NAMES[0],
			"assignments": [{"applies_to": "Role", "role": "Desk User"}],
			"workspaces": [{"workspace": NAMES[0]}, {"workspace": NAMES[1], "parent_workspace": NAMES[0]}],
		}
	).insert()
	profile_snapshot = profile.as_dict()
	frappe.db.commit()
	baseline_deletions = {
		name: frappe.db.count("Deleted Document", {"deleted_doctype": "Workspace", "deleted_name": name})
		for name in NAMES[:2]
	}
	snapshot = {
		"records": [frappe.get_doc("Workspace", name).as_dict() for name in NAMES[:2]],
		"dependencies": [
			frappe.get_doc("Number Card", CARD).as_dict(),
			frappe.get_doc("Custom HTML Block", BLOCK).as_dict(),
		],
	}
	from frappe.migrate import SiteMigration

	try:
		for iteration in (1, 2):
			SiteMigration(skip_search_index=True).run(site=site)
			_connect(site)
			protection.verify_snapshot(snapshot)
			profile_after = frappe.get_doc("Whitelabel Navigation Profile", PROFILE).as_dict()
			assert not protection._changed_fields(profile_snapshot, profile_after), (
				"Navigation Profile changed during migration"
			)
			assert not frappe.db.exists("Workspace", NAMES[2]), "Unprotected orphan cleanup did not run"
			for name in NAMES[:2]:
				assert (
					frappe.db.count(
						"Deleted Document", {"deleted_doctype": "Workspace", "deleted_name": name}
					)
					== baseline_deletions[name]
				), "Protected workspace was deleted and restored instead of preserved"
			print(
				f"Migration {iteration}: protected workspaces and dependencies unchanged; unprotected orphan removed."
			)
	finally:
		if not getattr(frappe.local, "site", None):
			_connect(site)
		frappe.flags.in_migrate = False
		if frappe.db.exists("Whitelabel Navigation Profile", PROFILE):
			frappe.delete_doc("Whitelabel Navigation Profile", PROFILE)
		for name in NAMES:
			if frappe.db.exists("Workspace", name):
				frappe.delete_doc("Workspace", name, force=True)
		for doctype, name in (("Number Card", CARD), ("Custom HTML Block", BLOCK)):
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=True)
		frappe.db.commit()
