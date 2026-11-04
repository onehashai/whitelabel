import frappe
from frappe import _
from frappe.model.document import Document

from whitelabel.navigation import validate_workspace


class WhitelabelNavigationProfile(Document):
	def validate(self):
		parents = {}
		for item in self.workspaces:
			if item.workspace in parents:
				frappe.throw(_("Workspace {0} appears more than once.").format(item.workspace))
			validate_workspace(item.workspace, public_only=True)
			parents[item.workspace] = item.parent_workspace
		for workspace, parent in parents.items():
			if parent and parent not in parents:
				frappe.throw(_("Include parent workspace {0} in this profile.").format(parent))
			seen = {workspace}
			while parent:
				if parent in seen:
					frappe.throw(_("Workspace parents cannot form a cycle."))
				seen.add(parent)
				parent = parents.get(parent)
		if self.default_workspace and self.default_workspace not in parents:
			frappe.throw(_("Home Workspace must be included in the profile."))
		for assignment in self.assignments:
			field = {"User": "user", "Role": "role", "Role Profile": "role_profile"}.get(
				assignment.applies_to
			)
			if not field or not assignment.get(field):
				frappe.throw(_("Select a User, Role, or Role Profile for every assignment."))
			for other in {"user", "role", "role_profile"} - {field}:
				assignment.set(other, None)
			if (
				field == "user"
				and frappe.get_cached_value("User", assignment.user, "user_type") != "System User"
			):
				frappe.throw(_("Navigation Profiles can only be assigned to System Users."))

	def on_update(self):
		frappe.clear_cache()

	def on_trash(self):
		frappe.clear_cache()
