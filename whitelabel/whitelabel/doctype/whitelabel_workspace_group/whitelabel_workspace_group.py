from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document

from whitelabel.navigation import DIRECTORY_ROUTE, validate_workspace


class WhitelabelWorkspaceGroup(Document):
	def validate(self):
		seen = set()
		for row in self.workspaces:
			if row.workspace in seen:
				frappe.throw(_("A workspace can appear only once in a group."))
			seen.add(row.workspace)
			validate_workspace(row.workspace, row.sidebar, public_only=True)

	def on_update(self):
		frappe.clear_cache()

	def on_trash(self):
		frappe.clear_cache()


@frappe.whitelist(methods=["POST"])
def publish_shortcut(group):
	"""Publish an explicitly requested, shared native Desktop Icon and sidebar."""
	frappe.only_for("System Manager")
	doc = frappe.get_doc("Whitelabel Workspace Group", group)
	doc.check_permission("write")
	if not doc.enabled:
		frappe.throw(_("Enable the group before publishing its shortcut."))
	label = f"Workspace Group: {doc.name}"
	if frappe.db.exists("Desktop Icon", label) or frappe.db.exists("Workspace Sidebar", label):
		frappe.throw(_("This shortcut already exists. Manage it in Desktop Icon and Workspace Sidebar."))
	sidebar = frappe.get_doc(
		{
			"doctype": "Workspace Sidebar",
			"title": label,
			"app": "whitelabel",
			"standard": 0,
			"items": [
				{
					"type": "Link",
					"label": doc.title,
					"link_type": "Page",
					"link_to": "workspace-directory",
					"route_options": frappe.as_json({"group": doc.name}),
				}
			],
		}
	).insert()
	# Standard makes it shared. No app means no source-file export on developer sites.
	icon = frappe.get_doc(
		{
			"doctype": "Desktop Icon",
			"label": label,
			"icon_type": "Link",
			"standard": 1,
			"link_type": "Workspace Sidebar",
			"link_to": sidebar.name,
			"sidebar": sidebar.name,
			"icon": doc.icon or "layout-dashboard",
			"bg_color": "blue",
		}
	).insert()
	frappe.clear_cache()
	return {"icon": icon.name, "route": f"{DIRECTORY_ROUTE}?{urlencode({'group': doc.name})}"}
