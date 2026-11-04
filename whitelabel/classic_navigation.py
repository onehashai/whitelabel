"""Curated navigation is a presentation layer, never an access grant."""

import hashlib
import json

import frappe
from frappe.utils import cint


def select_profiles(settings):
	user = frappe.get_cached_doc("User", frappe.session.user)
	roles = set(frappe.get_roles())
	role_profiles = {row.role_profile for row in user.get("role_profiles", [])}
	if user.get("role_profile_name"):
		role_profiles.add(user.role_profile_name)
	matched = []
	for row in frappe.get_all(
		"Whitelabel Navigation Profile",
		filters={"enabled": 1},
		fields=["name", "priority"],
		order_by="priority asc, name asc",
	):
		profile = frappe.get_cached_doc("Whitelabel Navigation Profile", row.name)
		ranks = []
		for assignment in profile.assignments:
			if assignment.applies_to == "User" and assignment.user == user.name:
				ranks.append(0)
			elif assignment.applies_to == "Role Profile" and assignment.role_profile in role_profiles:
				ranks.append(1)
			elif assignment.applies_to == "Role" and assignment.role in roles:
				ranks.append(2)
		if ranks:
			matched.append((min(ranks), cint(row.priority), row.name, profile))
	# An explicit user view replaces the combined role-based view.
	if any(rank == 0 for rank, *_ in matched):
		matched = [match for match in matched if match[0] == 0]
	if not matched and settings.get("default_navigation_profile"):
		profile = frappe.get_cached_doc("Whitelabel Navigation Profile", settings.default_navigation_profile)
		if profile.enabled:
			matched = [(3, cint(profile.priority), profile.name, profile)]
	return sorted(matched, key=lambda match: match[:3])


def curate(workspaces, settings):
	profiles = select_profiles(settings)
	visible = {}
	tree = {}
	homes = []

	def node_id(path):
		encoded = json.dumps(path, ensure_ascii=False, separators=(",", ":")).encode()
		return hashlib.sha256(encoded).hexdigest()[:24]

	def add_tree(placements, private=False):
		for workspace in placements:
			if workspace not in workspaces or bool(workspaces[workspace].public) == private:
				continue
			path = []
			seen = set()
			current = workspace
			while current and current in placements and current not in seen:
				seen.add(current)
				if current in workspaces and bool(workspaces[current].public) != private:
					path.append(current)
				current = placements.get(current, {}).get("parent")
			path.reverse()
			# A placement is identified by its full visible branch. Identical
			# branches merge; the same workspace under another parent stays visible.
			for index, name in enumerate(path):
				visible.setdefault(name, workspaces[name])
				placement = placements.get(name, {})
				identifier = node_id(path[: index + 1])
				tree.setdefault(
					identifier,
					dict(
						id=identifier,
						name=name,
						parent=path[index - 1] if index else None,
						parent_id=node_id(path[:index]) if index else None,
						label=placement.get("label") or workspaces[name].get("title") or name,
						icon=placement.get("icon") or workspaces[name].get("icon") or "folder",
						private=private,
					),
				)

	for rank, priority, name, profile in profiles:
		if profile.default_workspace:
			homes.append((rank, priority, name, profile.default_workspace))
		add_tree(
			{
				item.workspace: dict(parent=item.parent_workspace, label=item.label, icon=item.icon)
				for item in profile.workspaces
			}
		)

	if cint(settings.get("show_personal_workspaces")):
		private = {name: workspace for name, workspace in workspaces.items() if not workspace.public}
		by_title = {workspace.get("title"): name for name, workspace in private.items()}
		add_tree(
			{
				name: dict(
					parent=(
						workspace.get("parent_page")
						if workspace.get("parent_page") in private
						else by_title.get(workspace.get("parent_page"))
					)
				)
				for name, workspace in private.items()
			},
			private=True,
		)

	return visible, list(tree.values()), homes, [profile.name for *_, profile in profiles]
