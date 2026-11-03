"""Preserve explicitly site-managed public workspaces during native migration cleanup."""

from __future__ import annotations

import json
import os
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

PROTECTION_FIELD = "custom_whitelabel_protect_migration"


class ProtectedWorkspaceError(frappe.ValidationError):
	pass


class ProtectedWorkspaceMixin:
	def on_trash(self):
		# Run before the core controller can remove a sidebar or private-workspace link.
		protected_names = frappe.flags.get("whitelabel_protected_workspaces") or []
		if frappe.flags.in_migrate and (
			(self.public and cint(self.get(PROTECTION_FIELD))) or self.name in protected_names
		):
			raise ProtectedWorkspaceError(
				_("Skipping migration deletion of protected workspace {0}.").format(self.name)
			)
		return super().on_trash()


def ensure_protection_field():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	existing = frappe.db.get_value(
		"Custom Field",
		{"dt": "Workspace", "fieldname": PROTECTION_FIELD},
		["name", "fieldtype"],
		as_dict=True,
	)
	if existing:
		if existing.fieldtype != "Check":
			frappe.throw(_("The workspace migration protection field must be a Check field."))
		return
	create_custom_fields(
		{
			"Workspace": [
				{
					"fieldname": PROTECTION_FIELD,
					"label": "Protect During Migration",
					"fieldtype": "Check",
					"default": "0",
					"insert_after": "is_hidden",
					"description": "Preserve this site-managed public workspace during migration. Do not use for app-shipped workspaces.",
					"depends_on": "public",
				}
			]
		}
	)


def _source_workspaces(refresh=False):
	if refresh or frappe.flags.get("whitelabel_workspace_sources") is None:
		from frappe.model.sync import create_entity_file_map

		frappe.flags.whitelabel_workspace_sources = create_entity_file_map(["Workspace"])["Workspace"]
	return frappe.flags.whitelabel_workspace_sources


def mark_new_site_workspace(doc, method=None):
	# Imports/developer-mode workspaces belong to app source and its normal lifecycle.
	if (
		doc.public
		and frappe.get_meta("Workspace").has_field(PROTECTION_FIELD)
		and not any(
			(frappe.flags.in_import, frappe.flags.in_install, frappe.flags.in_patch, frappe.flags.in_migrate)
		)
		and not frappe.conf.developer_mode
		and doc.name not in _source_workspaces()
		and doc.title not in _source_workspaces()
	):
		doc.set(PROTECTION_FIELD, 1)


def validate_protection(doc, method=None):
	if not cint(doc.get(PROTECTION_FIELD)):
		return
	if not doc.public:
		frappe.throw(
			_(
				"Migration protection is for public workspaces. Private workspaces are excluded from native cleanup."
			)
		)
	if doc.name in _source_workspaces() or doc.title in _source_workspaces():
		frappe.throw(
			_(
				"This workspace is shipped by an app. Manage its definition in app source instead of marking it site-managed."
			)
		)


def _snapshot_path():
	directory = Path(frappe.get_site_path("private", "backups", "whitelabel-workspaces"))
	directory.mkdir(mode=0o700, parents=True, exist_ok=True)
	return directory / f"{now_datetime():%Y%m%d-%H%M%S-%f}.json"


def _references(workspace):
	for table, field, doctype in (
		("number_cards", "number_card_name", "Number Card"),
		("charts", "chart_name", "Dashboard Chart"),
		("custom_blocks", "custom_block_name", "Custom HTML Block"),
	):
		for row in workspace.get(table, []):
			if row.get(field):
				yield doctype, row[field]


def before_migrate():
	# This runs before schema sync/patches on the FIRST deployment too. Existing
	# markers can be created through Customize Form without migrating this app.
	ensure_protection_field()
	sources = _source_workspaces(refresh=True)
	names = frappe.get_all("Workspace", filters={PROTECTION_FIELD: 1, "public": 1}, pluck="name")
	conflicts = sorted(set(names) & set(sources))
	if conflicts:
		frappe.throw(
			_(
				"Protected workspace names now collide with app source: {0}. Resolve ownership before migrating."
			).format(", ".join(conflicts))
		)
	frappe.flags.whitelabel_protected_workspaces = names
	frappe.flags.whitelabel_workspace_snapshot = None
	if not names:
		return
	records = [frappe.get_doc("Workspace", name).as_dict() for name in sorted(names)]
	references = sorted({reference for record in records for reference in _references(record)})
	dependencies = [
		frappe.get_doc(doctype, name).as_dict()
		for doctype, name in references
		if frappe.db.exists(doctype, name)
	]
	snapshot = dict(
		site=frappe.local.site,
		created_at=now_datetime().isoformat(),
		records=records,
		dependencies=dependencies,
	)
	path = _snapshot_path()
	# An incomplete/unwritable backup must abort before the destructive cleanup.
	fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
	with os.fdopen(fd, "w") as file:
		file.write(frappe.as_json(snapshot))
	frappe.flags.whitelabel_workspace_snapshot = snapshot
	print(
		f"Protected {len(names)} site-managed workspace(s); snapshot: private/backups/whitelabel-workspaces/{path.name}"
	)


_CHILD_METADATA = {
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"idx",
	"parent",
	"parentfield",
	"parenttype",
	"doctype",
	"docstatus",
}
_TOP_METADATA = {"modified", "modified_by", "creation"}


def _normalize(value, child_rows=False, child=False):
	if isinstance(value, list):
		return [_normalize(row, child=child_rows) for row in value]
	if isinstance(value, dict):
		return {
			key: _normalize(item)
			for key, item in value.items()
			if not child or (key not in _CHILD_METADATA and not key.startswith("_"))
		}
	return value


def _content(value):
	try:
		return json.loads(value) if isinstance(value, str) else value
	except ValueError, TypeError:
		return value


def _changed_fields(record, current):
	return [
		key
		for key in record
		if key not in _TOP_METADATA
		and not key.startswith("_")
		and frappe.as_json(
			_normalize(
				_content(record[key]) if key == "content" else record[key], child_rows=key != "content"
			)
		)
		!= frappe.as_json(
			_normalize(
				_content(current.get(key)) if key == "content" else current.get(key),
				child_rows=key != "content",
			)
		)
	]


def verify_snapshot(snapshot):
	problems = []
	for record in snapshot["records"]:
		if not frappe.db.exists("Workspace", record["name"]):
			problems.append(record["name"] + " (missing)")
			continue
		current = frappe.get_doc("Workspace", record["name"]).as_dict()
		changed = _changed_fields(record, current)
		if changed:
			problems.append(record["name"] + " (changed: " + ", ".join(changed) + ")")
	for record in snapshot.get("dependencies", []):
		if not frappe.db.exists(record["doctype"], record["name"]):
			problems.append(record["doctype"] + ": " + record["name"] + " (missing)")
		else:
			current = frappe.get_doc(record["doctype"], record["name"]).as_dict()
			if changed := _changed_fields(record, current):
				problems.append(
					record["doctype"] + ": " + record["name"] + " (changed: " + ", ".join(changed) + ")"
				)
	if problems:
		raise ProtectedWorkspaceError(
			_(
				"Protected workspace verification failed: {0}. A private pre-migration snapshot is available for recovery."
			).format("; ".join(problems))
		)


def after_migrate():
	if snapshot := frappe.flags.get("whitelabel_workspace_snapshot"):
		verify_snapshot(snapshot)
		print(f"Verified {len(snapshot['records'])} protected workspace(s) after migration.")


@frappe.whitelist(methods=["POST"])
def set_protection(workspaces, enabled=1):
	frappe.only_for(["System Manager", "Workspace Manager"])
	workspaces = frappe.parse_json(workspaces) if isinstance(workspaces, str) else workspaces
	if not isinstance(workspaces, list) or not all(isinstance(name, str) for name in workspaces):
		frappe.throw(_("Provide a list of workspace names."))
	if not frappe.get_meta("Workspace").has_field(PROTECTION_FIELD):
		frappe.throw(_("Migrate the Whitelabel app before configuring workspace protection."))
	for name in dict.fromkeys(workspaces):
		doc = frappe.get_doc("Workspace", name)
		doc.set(PROTECTION_FIELD, cint(enabled))
		doc.save()
	return {"workspaces": list(dict.fromkeys(workspaces)), "protected": bool(cint(enabled))}
