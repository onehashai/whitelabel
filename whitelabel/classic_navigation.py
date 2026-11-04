"""Curated navigation is a presentation layer, never an access grant."""

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
	placements = {}
	homes = []
	for rank, priority, name, profile in profiles:
		if profile.default_workspace:
			homes.append((rank, priority, name, profile.default_workspace))
		for item in profile.workspaces:
			placements.setdefault(
				item.workspace,
				dict(
					parent=item.parent_workspace,
					label=item.label,
					icon=item.icon,
				),
			)
	visible = {
		name: workspace
		for name, workspace in workspaces.items()
		if (workspace.public and name in placements)
		or (not workspace.public and cint(settings.get("show_personal_workspaces")))
	}
	parents = {}
	for name, workspace in visible.items():
		if not workspace.public:
			parent = workspace.get("parent_page")
			parents[name] = parent if parent in visible and not visible[parent].public else None
			continue
		parent = placements[name]["parent"]
		seen = {name}
		while parent and parent not in seen:
			seen.add(parent)
			if parent in visible:
				break
			parent = placements.get(parent, {}).get("parent")
		parents[name] = parent if parent in visible and parent != name else None
	# Independently valid profiles may introduce a cycle when merged. Break the
	# first conflicting parent deterministically without losing a visible workspace.
	for name in parents:
		seen = {name}
		parent = parents[name]
		while parent:
			if parent in seen:
				parents[name] = None
				break
			seen.add(parent)
			parent = parents.get(parent)
	order = [name for name in placements if name in visible]
	order.extend(name for name in visible if name not in placements)
	return (
		{name: visible[name] for name in order},
		[
			dict(
				name=name,
				parent=parents[name],
				label=placements.get(name, {}).get("label") or visible[name].get("title") or name,
				icon=placements.get(name, {}).get("icon") or visible[name].get("icon") or "folder",
				private=not bool(visible[name].public),
			)
			for name in order
		],
		homes,
		[profile.name for *_, profile in profiles],
	)
