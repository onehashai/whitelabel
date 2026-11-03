import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from whitelabel import workspace_protection as protection


class TestWorkspaceProtection(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.savepoint("workspace_protection_fixture")
		self.addCleanup(self._rollback_fixture)
		previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, previous_user)
		flags = patch.dict(
			frappe.flags,
			{
				"in_migrate": False,
				"in_import": False,
				"in_patch": False,
				"in_install": False,
				"whitelabel_protected_workspaces": [],
				"whitelabel_workspace_snapshot": None,
				"whitelabel_workspace_sources": None,
			},
		)
		flags.start()
		self.addCleanup(flags.stop)
		mode = patch.dict(frappe.conf, {"developer_mode": 0})
		mode.start()
		self.addCleanup(mode.stop)
		self.directory = TemporaryDirectory(prefix="whitelabel-protection-test-")
		self.addCleanup(self.directory.cleanup)

	def _rollback_fixture(self):
		frappe.db.rollback(save_point="workspace_protection_fixture")
		frappe.clear_cache()

	def workspace(self, name="_WL Protected Test", **values):
		return frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": name,
				"title": name,
				"public": 1,
				"type": "Workspace",
				"module": "Core",
				"content": '[{"id":"kept","type":"paragraph","data":{"text":"Preserve me","col":12}}]',
				"roles": [{"role": "Desk User"}],
				**values,
			}
		).insert()

	def snapshot_path(self):
		return patch.object(
			protection, "_snapshot_path", return_value=Path(self.directory.name) / "snapshot.json"
		)

	def test_new_site_public_workspaces_are_protected(self):
		workspace = self.workspace()
		self.assertEqual(workspace.get(protection.PROTECTION_FIELD), 1)
		workspace.set(protection.PROTECTION_FIELD, 0)
		workspace.save()
		self.assertEqual(frappe.get_value("Workspace", workspace.name, protection.PROTECTION_FIELD), 0)

	def test_private_and_imported_workspaces_are_not_auto_protected(self):
		private = self.workspace("_WL Protection Private", public=0, for_user="Administrator")
		self.assertFalse(private.get(protection.PROTECTION_FIELD))
		with patch.dict(frappe.flags, {"in_import": True}):
			imported = self.workspace("_WL Protection Imported")
		self.assertFalse(imported.get(protection.PROTECTION_FIELD))

	def test_guard_runs_before_core_controller_cleanup(self):
		workspace = self.workspace()
		with patch.dict(frappe.flags, {"in_migrate": True}):
			with patch("frappe.desk.doctype.workspace.workspace.Workspace.on_trash") as core:
				with self.assertRaises(protection.ProtectedWorkspaceError):
					frappe.delete_doc("Workspace", workspace.name, force=True)
				core.assert_not_called()
		self.assertTrue(frappe.db.exists("Workspace", workspace.name))
		self.assertFalse(
			frappe.db.exists(
				"Deleted Document", {"deleted_doctype": "Workspace", "deleted_name": workspace.name}
			)
		)

	def test_native_orphan_cleanup_preserves_protected_and_removes_opted_out(self):
		from frappe.model.sync import remove_orphan_entities

		kept = self.workspace()
		removed = self.workspace("_WL Protection Opted Out")
		removed.set(protection.PROTECTION_FIELD, 0)
		removed.save()
		with patch.dict(frappe.flags, {"in_migrate": True}), patch.object(frappe.db, "commit"):
			remove_orphan_entities("Workspace")
		self.assertTrue(frappe.db.exists("Workspace", kept.name))
		self.assertFalse(frappe.db.exists("Workspace", removed.name))

	def test_normal_intentional_deletion_is_not_blocked(self):
		workspace = self.workspace()
		frappe.delete_doc("Workspace", workspace.name, force=True)
		self.assertFalse(frappe.db.exists("Workspace", workspace.name))

	def test_snapshot_is_private_and_verifies_semantic_content(self):
		workspace = self.workspace()
		with self.snapshot_path():
			protection.before_migrate()
		path = Path(self.directory.name) / "snapshot.json"
		self.assertEqual(path.stat().st_mode & 0o777, 0o600)
		snapshot = json.loads(path.read_text())
		protection.verify_snapshot(snapshot)
		workspace.content = '[{"id":"kept","type":"paragraph","data":{"text":"Changed","col":12}}]'
		workspace.save()
		with self.assertRaises(protection.ProtectedWorkspaceError):
			protection.verify_snapshot(snapshot)

	def test_snapshot_failure_aborts_before_cleanup(self):
		workspace = self.workspace()
		with patch.object(protection, "_snapshot_path", side_effect=OSError("not writable")):
			with self.assertRaises(OSError):
				protection.before_migrate()
		self.assertTrue(frappe.db.exists("Workspace", workspace.name))

	def test_snapshot_detects_changed_widget_content(self):
		block = frappe.get_doc(
			{
				"doctype": "Custom HTML Block",
				"name": "_WL Protection Snapshot Block",
				"private": 0,
				"html": "<p>Original</p>",
			}
		).insert()
		self.workspace(custom_blocks=[{"custom_block_name": block.name}])
		with self.snapshot_path():
			protection.before_migrate()
		block.html = "<p>Changed</p>"
		block.save()
		with self.assertRaises(protection.ProtectedWorkspaceError):
			protection.verify_snapshot(frappe.flags.whitelabel_workspace_snapshot)

	def test_source_collision_stops_before_import(self):
		workspace = self.workspace()
		with patch.object(
			protection, "_source_workspaces", return_value={workspace.name: "/fake/workspace.json"}
		):
			with self.assertRaises(frappe.ValidationError):
				protection.before_migrate()
		self.assertTrue(frappe.db.exists("Workspace", workspace.name))

	def test_snapshot_names_still_protect_if_a_patch_clears_the_marker(self):
		workspace = self.workspace()
		with self.snapshot_path():
			protection.before_migrate()
		workspace.set(protection.PROTECTION_FIELD, 0)
		workspace.save()
		with patch.dict(frappe.flags, {"in_migrate": True}):
			with self.assertRaises(protection.ProtectedWorkspaceError):
				frappe.delete_doc("Workspace", workspace.name, force=True)

	def test_api_uses_native_permissions(self):
		workspace = self.workspace()
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			protection.set_protection([workspace.name])
