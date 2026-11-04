"""Optional Desk navigation. Website Users always retain native portal routing."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlencode, urlsplit

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.data import get_url_to_workspace
from werkzeug.routing import RequestRedirect

from whitelabel.api import get_whitelabel_settings

DIRECTORY_ROUTE = "/desk/workspace-directory"
DESKTOP_ROUTE = "/desk/desktop"


def is_system_user():
	user = frappe.session.user
	return bool(
		user
		and user != "Guest"
		and frappe.get_cached_value("User", user, "enabled")
		and frappe.get_cached_value("User", user, "user_type") == "System User"
	)


def _is_website_user():
	return bool(
		frappe.session.user not in {None, "Guest"}
		and frappe.get_cached_value("User", frappe.session.user, "enabled")
		and frappe.get_cached_value("User", frappe.session.user, "user_type") == "Website User"
	)


def _is_desk_destination(destination):
	if not destination:
		return False
	parsed = urlsplit(destination)
	# Native Website User login can prefix an absolute Desk path with another '/'.
	if parsed.netloc == "desk":
		return True
	request_host = getattr(getattr(frappe.local, "request", None), "host", None)
	if parsed.netloc and parsed.netloc != request_host:
		return False
	path = parsed.path.strip("/")
	return path in {"desk", "app", "apps"} or path.startswith(("desk/", "app/"))


def _portal_home_route():
	"""Native portal precedence, excluding stale Desk defaults on converted users."""
	from frappe.website.utils import get_home_page_via_hooks

	candidates = [frappe.local.flags.get("home_page")]
	candidates.extend(frappe.get_cached_value("Role", role, "home_page") for role in frappe.get_roles())
	candidates.extend(
		[
			frappe.db.get_single_value("Portal Settings", "default_portal_home"),
			get_home_page_via_hooks(),
			frappe.db.get_single_value("Website Settings", "home_page"),
		]
	)
	for destination in candidates:
		if not destination or _is_desk_destination(destination):
			continue
		path = destination.strip("/")
		if path in {"", "login", "index"}:
			continue
		if path == "me":
			return "/portal"
		return destination if destination.startswith(("/", "https://", "http://")) else "/" + destination
	return "/portal"


def get_settings():
	settings = get_whitelabel_settings()
	return settings if settings and cint(settings.get("enable_workspace_navigation")) else None


def _workspace_url(workspace, sidebar=None):
	url = get_url_to_workspace(workspace["name"], bool(workspace["public"]))
	return f"{url}?{urlencode({'sidebar': sidebar})}" if sidebar else url


def _available_workspaces(pages=None):
	if pages is None:
		from frappe.desk.desktop import get_workspaces

		pages = get_workspaces()["pages"]
	# Even Workspace Managers only see their own private workspaces here.
	return {
		w["name"]: frappe._dict(w)
		for w in pages
		if not w.get("is_hidden")
		and w.get("type", "Workspace") == "Workspace"
		and (w.get("public") or w.get("for_user") == frappe.session.user)
	}


def _available_sidebars(workspaces, sidebars=None):
	if sidebars is None:
		from frappe.boot import get_sidebar_items

		sidebars = get_sidebar_items(list(workspaces))
	private = {
		d.name.lower()
		for d in frappe.get_all("Workspace Sidebar", fields=["name", "for_user"])
		if d.for_user and d.for_user != frappe.session.user
	}
	return {key: value for key, value in sidebars.items() if key not in private}


def _sidebar_for(workspace, sidebars, preferred=None):
	candidates = {
		key: sidebar
		for key, sidebar in sidebars.items()
		if any(i.get("link_type") == "Workspace" and i.get("link_to") == workspace for i in sidebar["items"])
	}
	for name in (preferred, workspace):
		if name and name.lower() in candidates:
			return candidates[name.lower()].get("label") or name
	if candidates:
		key = sorted(candidates)[0]
		return candidates[key].get("label") or key
	return None


def _rules_for_user():
	user = frappe.get_cached_doc("User", frappe.session.user)
	profiles = {row.role_profile for row in user.get("role_profiles", [])}
	if user.get("role_profile_name"):
		profiles.add(user.role_profile_name)
	roles = set(frappe.get_roles())
	rules = frappe.get_all(
		"Whitelabel Workspace Rule",
		filters={"enabled": 1},
		fields=["name", "applies_to", "role", "role_profile", "workspace", "sidebar", "priority"],
	)
	matching = [
		r
		for r in rules
		if (r.applies_to == "Role Profile" and r.role_profile in profiles)
		or (r.applies_to == "Role" and r.role in roles)
	]
	return sorted(matching, key=lambda r: (r.applies_to != "Role Profile", cint(r.priority), r.name))


def _groups(workspaces, sidebars):
	groups = []
	for row in frappe.get_all(
		"Whitelabel Workspace Group",
		filters={"enabled": 1},
		fields=["name", "title", "icon", "sequence", "include_module"],
		order_by="sequence asc, name asc",
	):
		group = frappe.get_cached_doc("Whitelabel Workspace Group", row.name)
		items = []
		seen = set()
		for entry in group.get("workspaces", []):
			if entry.workspace in workspaces and entry.workspace not in seen:
				seen.add(entry.workspace)
				w = workspaces[entry.workspace]
				items.append(
					dict(name=w.name, route=_workspace_url(w, _sidebar_for(w.name, sidebars, entry.sidebar)))
				)
		for w in workspaces.values():
			if row.include_module and w.get("module") == row.include_module and w.name not in seen:
				seen.add(w.name)
				items.append(dict(name=w.name, route=_workspace_url(w, _sidebar_for(w.name, sidebars))))
		if items:
			groups.append(dict(name=row.name, title=row.title, icon=row.icon, items=items))
	return groups


def build_context(pages=None, sidebars=None):
	settings = get_settings()
	if not settings or not is_system_user() or not frappe.is_setup_complete():
		return None
	workspaces = _available_workspaces(pages)
	classic = settings.get("desk_layout") == "Classic"
	tree, profile_homes, profiles = [], [], []
	tree_routes = {}
	if classic:
		from whitelabel.classic_navigation import curate

		workspaces, tree, profile_homes, profiles = curate(workspaces, settings)
		counts = Counter(node["name"] for node in tree)
		for node in tree:
			route = _workspace_url(workspaces[node["name"]])
			if counts[node["name"]] > 1:
				route += "?" + urlencode({"navigation_path": node["id"]})
			node["route"] = route
			tree_routes.setdefault(node["name"], route)
		sidebars = {}
	else:
		sidebars = _available_sidebars(workspaces, sidebars)
	rules = _rules_for_user()
	default = frappe.get_cached_value("User", frappe.session.user, "default_workspace")
	candidates = [(default, None)]
	if classic:
		choices = [
			(rank, priority, name, workspace, None) for rank, priority, name, workspace in profile_homes
		]
		choices.extend(
			(
				1 if rule.applies_to == "Role Profile" else 2,
				cint(rule.priority),
				rule.name,
				rule.workspace,
				rule.sidebar,
			)
			for rule in rules
		)
		candidates.extend(
			(workspace, sidebar)
			for _, _, _, workspace, sidebar in sorted(choices, key=lambda choice: choice[:3])
		)
	else:
		candidates.extend((rule.workspace, rule.sidebar) for rule in rules)
	candidates.append((settings.get("default_workspace"), settings.get("default_workspace_sidebar")))
	if classic:
		candidates.extend((name, None) for name in workspaces)
	home = None
	for name, preferred in candidates:
		if name in workspaces:
			# A user override can still use the configured sidebar for the same workspace.
			preferred = preferred or next(
				(r.sidebar for r in rules if r.workspace == name and r.sidebar), None
			)
			if not preferred and name == settings.get("default_workspace"):
				preferred = settings.get("default_workspace_sidebar")
			home = dict(
				name=name,
				route=tree_routes.get(name)
				or _workspace_url(workspaces[name], _sidebar_for(name, sidebars, preferred)),
			)
			break
	items = [
		dict(
			name=w.name,
			title=w.get("title") or w.name,
			module=w.get("module"),
			icon=w.get("icon"),
			private=not bool(w.public),
			route=tree_routes.get(w.name) or _workspace_url(w, _sidebar_for(w.name, sidebars)),
		)
		for w in workspaces.values()
	]
	return dict(
		enabled=True,
		classic=classic,
		tree=tree,
		navigation_profiles=profiles,
		home=home,
		home_route=home["route"] if home else DIRECTORY_ROUTE,
		directory_route=DIRECTORY_ROUTE,
		desktop_route=DESKTOP_ROUTE,
		allow_user_home=bool(cint(settings.get("allow_user_workspace_home"))),
		can_manage=bool(set(frappe.get_roles()) & {"System Manager", "Workspace Manager"}),
		can_manage_settings="System Manager" in frappe.get_roles(),
		can_create_workspace=frappe.has_permission("Workspace", "create"),
		allow_personal_workspaces=bool(cint(settings.get("show_personal_workspaces"))),
		workspaces=items,
		groups=[] if classic else _groups(workspaces, sidebars),
	)


@frappe.whitelist()
def get_context():
	"""Always resolve for the current authenticated System User; never impersonate."""
	return build_context()


def extend_bootinfo(bootinfo):
	bootinfo.whitelabel_navigation = build_context(
		pages=bootinfo.get("workspaces", {}).get("pages", []),
		sidebars=bootinfo.get("workspace_sidebar_item", {}),
	)
	if context := bootinfo.whitelabel_navigation:
		visible_shortcuts = {f"Workspace Group: {group['name']}" for group in context["groups"]}
		bootinfo.desktop_icons = [
			icon
			for icon in bootinfo.get("desktop_icons", [])
			if not (icon.get("name") or icon.get("label", "")).startswith("Workspace Group: ")
			or (icon.get("name") or icon.get("label")) in visible_shortcuts
		]


def on_session_creation(login_manager=None):
	if not get_settings():
		return
	if _is_website_user():
		frappe.local.flags.whitelabel_portal_home = _portal_home_route()
		return
	if not is_system_user() or not frappe.is_setup_complete():
		return
	context = build_context()
	# Native password login reads this flag before Role/Home Page settings.
	frappe.local.flags.home_page = context["home_route"]
	frappe.local.flags.whitelabel_login_home = context["home_route"]


def before_request():
	request = frappe.local.request
	if request.method not in {"GET", "HEAD"} or frappe.form_dict.get("cmd"):
		return
	path = request.path.rstrip("/") or "/"
	if path not in {"/", "/login", "/desk"}:
		return
	settings = get_settings()
	if not settings:
		return
	if path == "/" and not cint(settings.get("route_root_to_workspace")) and not _is_website_user():
		return
	if frappe.session.user == "Guest":
		if path == "/":
			_redirect("/login")
		return
	if request.args.get("redirect-to") or request.args.get("redirect_to"):
		return
	# Converted Website Users can retain native Desk defaults. Preserve valid portal
	# destinations and repair only destinations which would send them into Desk.
	if _is_website_user():
		if path in {"/", "/login"}:
			from frappe.apps import get_default_path
			from frappe.website.utils import get_home_page

			destination = (get_default_path() or get_home_page()) if path == "/login" else get_home_page()
			if _is_desk_destination(destination):
				_redirect(_portal_home_route())
		return
	if not is_system_user() or not frappe.is_setup_complete():
		return
	_redirect(build_context()["home_route"])


def _redirect(destination):
	# HTTPException works during init_request, before the website renderer is active.
	exception = RequestRedirect(destination)
	exception.code = 302
	raise exception


def after_request(request, response):
	"""Normalize implicit SSO/token-login destinations, preserving explicit links."""
	if not (
		frappe.local.flags.get("whitelabel_login_home") or frappe.local.flags.get("whitelabel_portal_home")
	):
		return
	if not get_settings():
		return
	if _is_website_user():
		if any(frappe.form_dict.get(key) for key in ("redirect-to", "redirect_to")):
			return
		payload = response.get_json(silent=True) if response.is_json else None
		if (
			isinstance(payload, dict)
			and payload.get("message") == "No App"
			and _is_desk_destination(payload.get("home_page"))
		):
			payload["home_page"] = _portal_home_route()
			response.set_data(frappe.as_json(payload))
		elif frappe.local.flags.get("whitelabel_portal_home") and response.status_code in {
			301,
			302,
			303,
			307,
			308,
		}:
			if _is_desk_destination(response.headers.get("Location")):
				response.headers["Location"] = frappe.local.flags.whitelabel_portal_home
		return
	home = frappe.local.flags.get("whitelabel_login_home")
	if (
		not home
		or not get_settings()
		or not is_system_user()
		or response.status_code not in {301, 302, 303, 307, 308}
	):
		return
	if any(frappe.form_dict.get(key) for key in ("redirect-to", "redirect_to")):
		return
	location = urlsplit(response.headers.get("Location", ""))
	if location.netloc and location.netloc != request.host:
		return
	if location.path.rstrip("/") in {"", "/apps", "/desk", "/desk/workspace"}:
		response.headers["Location"] = home


@frappe.whitelist(methods=["POST"])
def set_my_home(workspace):
	context = build_context()
	if not context or not context["allow_user_home"]:
		frappe.throw(_("Choosing a home workspace is not enabled."), frappe.PermissionError)
	if workspace not in {w["name"] for w in context["workspaces"]}:
		frappe.throw(_("This workspace is not available to you."), frappe.PermissionError)
	user = frappe.get_doc("User", frappe.session.user)
	user.default_workspace = workspace
	user.save()
	return build_context()


def validate_workspace(workspace, sidebar=None, public_only=False):
	if not workspace:
		return
	doc = frappe.get_doc("Workspace", workspace)
	if doc.is_hidden or doc.get("type", "Workspace") != "Workspace" or (public_only and not doc.public):
		frappe.throw(_("Choose a visible public workspace."))
	if sidebar:
		sidebar_doc = frappe.get_doc("Workspace Sidebar", sidebar)
		if sidebar_doc.for_user or not any(
			i.link_type == "Workspace" and i.link_to == workspace for i in sidebar_doc.items
		):
			frappe.throw(_("The sidebar must be shared and contain the selected workspace."))
