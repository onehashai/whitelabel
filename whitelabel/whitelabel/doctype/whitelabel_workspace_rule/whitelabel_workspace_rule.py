import frappe
from frappe import _
from frappe.model.document import Document

from whitelabel.navigation import validate_workspace


class WhitelabelWorkspaceRule(Document):
	def validate(self):
		if self.applies_to == "Role":
			if not self.role:
				frappe.throw(_("Select a Role."))
			self.role_profile = None
		elif self.applies_to == "Role Profile":
			if not self.role_profile:
				frappe.throw(_("Select a Role Profile."))
			self.role = None
		else:
			frappe.throw(_("Choose Role or Role Profile."))
		validate_workspace(self.workspace, self.sidebar, public_only=True)

	def on_update(self):
		frappe.clear_cache()

	def on_trash(self):
		frappe.clear_cache()
