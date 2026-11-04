from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from werkzeug.routing import RequestRedirect
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request, Response

from whitelabel import navigation


class TestWorkspaceNavigation(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.savepoint("whitelabel_navigation_fixture")
		self.addCleanup(self._rollback_fixture)
		setup_complete = patch("frappe.is_setup_complete", return_value=True)
		setup_complete.start()
		self.addCleanup(setup_complete.stop)
		self.previous_user = frappe.session.user
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, self.previous_user)
		self.addCleanup(frappe.clear_cache)
		self.mode = patch.dict(frappe.conf, {"developer_mode": 0})
		self.mode.start()
		self.addCleanup(self.mode.stop)
		for role in ("_WL Nav A", "_WL Nav B", "_WL Nav Portal"):
			if not frappe.db.exists("Role", role):
				frappe.get_doc(
					{"doctype": "Role", "role_name": role, "desk_access": role != "_WL Nav Portal"}
				).insert()
		for email, roles in (
			("wl-nav-system@example.test", ["_WL Nav A", "_WL Nav B"]),
			("wl-nav-other@example.test", ["_WL Nav B"]),
			("wl-nav-portal@example.test", ["_WL Nav Portal"]),
		):
			if not frappe.db.exists("User", email):
				frappe.get_doc(
					{
						"doctype": "User",
						"email": email,
						"first_name": "Navigation Test",
						"send_welcome_email": 0,
						"roles": [{"role": role} for role in roles],
					}
				).insert()
		for label, roles, hidden in (
			("_WL Nav A", ["_WL Nav A"], 0),
			("_WL Nav B", ["_WL Nav B"], 0),
			("_WL Nav Restricted", ["_WL Nav Portal"], 0),
			("_WL Nav Hidden", ["_WL Nav A"], 1),
		):
			if not frappe.db.exists("Workspace", label):
				frappe.get_doc(
					{
						"doctype": "Workspace",
						"label": label,
						"title": label,
						"public": 1,
						"module": "Core",
						"content": "[]",
						"is_hidden": hidden,
						"roles": [{"role": r} for r in roles],
					}
				).insert()
		self.settings = frappe.get_single("Whitelabel Setting")
		self.settings.update(
			{
				"enable_workspace_navigation": 1,
				"route_root_to_workspace": 1,
				"allow_user_workspace_home": 1,
				"default_workspace": "_WL Nav B",
				"default_workspace_sidebar": None,
			}
		)
		self.settings.save()
		self.addCleanup(self._reset_local_flags)

	def _rollback_fixture(self):
		frappe.db.rollback(save_point="whitelabel_navigation_fixture")
		frappe.clear_cache()

	def _reset_local_flags(self):
		frappe.local.flags.pop("home_page", None)
		frappe.local.flags.pop("whitelabel_login_home", None)
		frappe.local.flags.pop("whitelabel_portal_home", None)

	def rule(self, title, workspace, priority=100, **values):
		return frappe.get_doc(
			{
				"doctype": "Whitelabel Workspace Rule",
				"title": title,
				"enabled": 1,
				"applies_to": "Role",
				"role": "_WL Nav A",
				"workspace": workspace,
				"priority": priority,
				**values,
			}
		).insert()

	def as_system(self):
		frappe.set_user("wl-nav-system@example.test")

	def profile(self, title, workspaces, assignments=None, **values):
		return frappe.get_doc(
			{
				"doctype": "Whitelabel Navigation Profile",
				"title": title,
				"enabled": 1,
				"assignments": assignments or [{"applies_to": "Role", "role": "_WL Nav A"}],
				"workspaces": [{"workspace": item} if isinstance(item, str) else item for item in workspaces],
				**values,
			}
		).insert()

	def classic(self):
		self.settings.desk_layout = "Classic"
		self.settings.show_personal_workspaces = 1
		self.settings.save()

	def test_classic_combines_profiles_and_excludes_unlisted_workspaces(self):
		self.classic()
		self.profile("_WL Profile One", ["_WL Nav A"], default_workspace="_WL Nav A")
		self.profile(
			"_WL Profile Two",
			["_WL Nav A", "_WL Nav B"],
			assignments=[{"applies_to": "Role", "role": "_WL Nav B"}],
		)
		self.as_system()
		context = navigation.build_context()
		self.assertTrue(context["classic"])
		self.assertEqual([node["name"] for node in context["tree"]], ["_WL Nav A", "_WL Nav B"])
		self.assertEqual(context["home"]["name"], "_WL Nav A")
		self.assertEqual(context["groups"], [])
		self.assertNotIn("sidebar=", context["home_route"])
		self.assertEqual(navigation.set_my_home("_WL Nav B")["home"]["name"], "_WL Nav B")

	def test_classic_user_assignment_replaces_role_view(self):
		self.classic()
		self.profile("_WL Role Profile", ["_WL Nav A"])
		self.profile(
			"_WL User Profile",
			["_WL Nav B"],
			assignments=[{"applies_to": "User", "user": "wl-nav-system@example.test"}],
		)
		self.as_system()
		self.assertEqual([w["name"] for w in navigation.build_context()["workspaces"]], ["_WL Nav B"])

	def test_classic_default_profile_and_empty_assignment(self):
		self.classic()
		self.as_system()
		self.assertEqual(navigation.build_context()["tree"], [])
		self.assertEqual(navigation.build_context()["home_route"], navigation.DIRECTORY_ROUTE)
		frappe.set_user("Administrator")
		profile = self.profile(
			"_WL Default Profile",
			["_WL Nav A"],
			assignments=[{"applies_to": "Role", "role": "_WL Nav Portal"}],
		)
		self.settings.default_navigation_profile = profile.name
		self.settings.save()
		self.as_system()
		self.assertEqual(navigation.build_context()["home"]["name"], "_WL Nav A")

	def test_classic_promotes_allowed_children_without_exposing_parent(self):
		self.classic()
		self.profile(
			"_WL Filtered Tree",
			["_WL Nav Restricted", {"workspace": "_WL Nav A", "parent_workspace": "_WL Nav Restricted"}],
		)
		self.as_system()
		tree = navigation.build_context()["tree"]
		self.assertEqual(len(tree), 1)
		self.assertEqual(tree[0]["name"], "_WL Nav A")
		self.assertIsNone(tree[0]["parent"])

	def test_classic_profile_tree_validation(self):
		self.classic()
		with self.assertRaises(frappe.ValidationError):
			self.profile(
				"_WL Cycle",
				[
					{"workspace": "_WL Nav A", "parent_workspace": "_WL Nav B"},
					{"workspace": "_WL Nav B", "parent_workspace": "_WL Nav A"},
				],
			)
		with self.assertRaises(frappe.ValidationError):
			self.profile("_WL Missing Parent", [{"workspace": "_WL Nav A", "parent_workspace": "_WL Nav B"}])
		with self.assertRaises(frappe.ValidationError):
			self.profile("_WL Duplicate", ["_WL Nav A", "_WL Nav A"])
		with self.assertRaises(frappe.ValidationError):
			self.profile("_WL Wrong Home", ["_WL Nav A"], default_workspace="_WL Nav B")
		with self.assertRaises(frappe.ValidationError):
			self.profile(
				"_WL Portal Profile",
				["_WL Nav A"],
				assignments=[{"applies_to": "User", "user": "wl-nav-portal@example.test"}],
			)

	def test_classic_preserves_distinct_parent_branches(self):
		self.classic()
		self.profile(
			"_WL Tree One", [{"workspace": "_WL Nav A", "parent_workspace": "_WL Nav B"}, "_WL Nav B"]
		)
		self.profile(
			"_WL Tree Two",
			["_WL Nav A", {"workspace": "_WL Nav B", "parent_workspace": "_WL Nav A"}],
			priority=200,
		)
		self.as_system()
		tree = navigation.build_context()["tree"]
		self.assertEqual(len(tree), 4)
		self.assertEqual(len({node["id"] for node in tree}), 4)
		self.assertEqual(
			{node["parent"] for node in tree if node["name"] == "_WL Nav A"}, {None, "_WL Nav B"}
		)
		self.assertEqual(
			{node["parent"] for node in tree if node["name"] == "_WL Nav B"}, {None, "_WL Nav A"}
		)

	def test_classic_shared_child_appears_under_each_parent_once(self):
		self.classic()
		shared = frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": "_WL Shared Child",
				"title": "_WL Shared Child",
				"public": 1,
				"module": "Core",
				"content": "[]",
				"roles": [{"role": "_WL Nav A"}],
			}
		).insert()
		for title, parent, priority in (
			("_WL Shared One", "_WL Nav A", 10),
			("_WL Shared Two", "_WL Nav B", 20),
			("_WL Shared Duplicate", "_WL Nav A", 30),
		):
			self.profile(
				title, [parent, {"workspace": shared.name, "parent_workspace": parent}], priority=priority
			)
		self.as_system()
		context = navigation.build_context()
		nodes = [node for node in context["tree"] if node["name"] == shared.name]
		self.assertEqual(len(nodes), 2)
		self.assertEqual({node["parent"] for node in nodes}, {"_WL Nav A", "_WL Nav B"})
		self.assertNotEqual(nodes[0]["route"], nodes[1]["route"])
		self.assertTrue(all("navigation_path=" in node["route"] for node in nodes))
		self.assertEqual(len([item for item in context["workspaces"] if item["name"] == shared.name]), 1)

	def test_classic_personal_home_and_outside_profile_home(self):
		self.classic()
		self.profile("_WL Focused Profile", ["_WL Nav A"])
		self.as_system()
		with self.assertRaises(frappe.PermissionError):
			navigation.set_my_home("_WL Nav B")
		frappe.set_user("Administrator")
		private = frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": "_WL Classic Private",
				"title": "_WL Classic Private",
				"module": "Core",
				"public": 0,
				"for_user": "wl-nav-system@example.test",
				"content": "[]",
			}
		).insert()
		self.as_system()
		self.assertIn(private.name, [w["name"] for w in navigation.build_context()["tree"]])
		context = navigation.set_my_home(private.name)
		self.assertEqual(context["home"]["name"], private.name)
		frappe.set_user("wl-nav-other@example.test")
		self.assertNotIn(private.name, [w["name"] for w in navigation.build_context()["tree"]])

	def test_classic_visibility_does_not_grant_permissions(self):
		self.classic()
		self.profile("_WL Restricted Profile", ["_WL Nav Restricted"])
		self.as_system()
		self.assertEqual(navigation.build_context()["workspaces"], [])
		frappe.set_user("wl-nav-portal@example.test")
		self.assertIsNone(navigation.build_context())

	def test_classic_role_profile_assignment_and_blocked_module(self):
		self.classic()
		role_profile = frappe.get_doc(
			{"doctype": "Role Profile", "role_profile": "_WL Classic Roles", "roles": [{"role": "_WL Nav A"}]}
		).insert()
		user = frappe.get_doc("User", "wl-nav-system@example.test")
		user.append("role_profiles", {"role_profile": role_profile.name})
		user.save()
		self.profile(
			"_WL Role Profile View",
			["_WL Nav A"],
			assignments=[{"applies_to": "Role Profile", "role_profile": role_profile.name}],
		)
		self.as_system()
		self.assertEqual(navigation.build_context()["home"]["name"], "_WL Nav A")
		frappe.set_user("Administrator")
		user = frappe.get_doc("User", user.name)
		user.append("block_modules", {"module": "Core"})
		user.save()
		self.as_system()
		self.assertEqual(navigation.build_context()["tree"], [])

	def test_classic_personal_visibility_can_be_disabled(self):
		self.classic()
		self.profile("_WL No Personal", ["_WL Nav A"])
		private = frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": "_WL Hidden Personal",
				"title": "_WL Hidden Personal",
				"module": "Core",
				"public": 0,
				"for_user": "wl-nav-system@example.test",
				"content": "[]",
			}
		).insert()
		self.settings.show_personal_workspaces = 0
		self.settings.save()
		self.as_system()
		self.assertNotIn(private.name, [item["name"] for item in navigation.build_context()["tree"]])

	def request(self, path, method="GET"):
		return patch.object(
			frappe.local,
			"request",
			Request(EnvironBuilder(path=path, method=method).get_environ()),
			create=True,
		)

	def test_role_priority_and_user_override(self):
		self.rule("_WL Z", "_WL Nav B", 20)
		self.rule("_WL A", "_WL Nav A", 10)
		self.as_system()
		self.assertEqual(navigation.build_context()["home"]["name"], "_WL Nav A")
		context = navigation.set_my_home("_WL Nav B")
		self.assertEqual(context["home"]["name"], "_WL Nav B")
		self.assertEqual(frappe.get_value("User", frappe.session.user, "default_workspace"), "_WL Nav B")

	def test_profile_precedes_role_and_equal_priorities_are_stable(self):
		profile = frappe.get_doc(
			{
				"doctype": "Role Profile",
				"role_profile": "_WL Nav Profile",
				"roles": [{"role": "_WL Nav A"}, {"role": "_WL Nav B"}],
			}
		).insert()
		user = frappe.get_doc("User", "wl-nav-system@example.test")
		user.append("role_profiles", {"role_profile": profile.name})
		user.save()
		self.rule("_WL Role", "_WL Nav B", 1)
		self.rule("_WL Profile Z", "_WL Nav B", 50, applies_to="Role Profile", role_profile=profile.name)
		self.rule("_WL Profile A", "_WL Nav A", 50, applies_to="Role Profile", role_profile=profile.name)
		self.as_system()
		self.assertEqual(navigation.build_context()["home"]["name"], "_WL Nav A")

	def test_inaccessible_default_and_rule_fall_back(self):
		self.rule("_WL Restricted Rule", "_WL Nav Restricted")
		user = frappe.get_doc("User", "wl-nav-system@example.test")
		user.default_workspace = "_WL Nav Hidden"
		user.save()
		self.as_system()
		context = navigation.build_context()
		self.assertEqual(context["home"]["name"], "_WL Nav B")
		names = {w["name"] for w in context["workspaces"]}
		self.assertNotIn("_WL Nav Restricted", names)
		self.assertNotIn("_WL Nav Hidden", names)

	def test_private_workspaces_are_owner_only(self):
		for email in ("wl-nav-system@example.test", "wl-nav-other@example.test"):
			label = "_WL Private " + email
			frappe.get_doc(
				{
					"doctype": "Workspace",
					"label": label,
					"title": label,
					"for_user": email,
					"module": "Core",
					"content": "[]",
					"public": 0,
				}
			).insert()
		self.as_system()
		context = navigation.build_context()
		private = [w for w in context["workspaces"] if w["private"]]
		self.assertEqual([w["name"] for w in private], ["_WL Private wl-nav-system@example.test"])
		self.assertTrue(private[0]["route"].startswith("/desk/private/"))

	def test_group_and_sidebar_are_filtered_and_selected(self):
		sidebar = frappe.get_doc(
			{
				"doctype": "Workspace Sidebar",
				"title": "_WL Nav Sidebar",
				"items": [
					{"type": "Link", "label": "Dashboard", "link_type": "Workspace", "link_to": "_WL Nav A"}
				],
			}
		).insert()
		self.rule("_WL Sidebar Rule", "_WL Nav A", sidebar=sidebar.name)
		frappe.get_doc(
			{
				"doctype": "Whitelabel Workspace Group",
				"title": "_WL Group",
				"enabled": 1,
				"workspaces": [
					{"workspace": "_WL Nav A", "sidebar": sidebar.name},
					{"workspace": "_WL Nav Restricted"},
				],
			}
		).insert()
		self.as_system()
		context = navigation.build_context()
		self.assertIn("sidebar=_WL+Nav+Sidebar", context["home_route"])
		group = next(g for g in context["groups"] if g["name"] == "_WL Group")
		self.assertEqual([i["name"] for i in group["items"]], ["_WL Nav A"])

	def test_no_valid_home_uses_directory(self):
		self.settings.default_workspace = None
		self.settings.save()
		self.as_system()
		context = navigation.build_context()
		self.assertIsNone(context["home"])
		self.assertEqual(context["home_route"], navigation.DIRECTORY_ROUTE)

	def test_guest_and_website_user_never_receive_desk_navigation(self):
		self.assertEqual(frappe.get_value("User", "wl-nav-portal@example.test", "user_type"), "Website User")
		for user in ("Guest", "wl-nav-portal@example.test"):
			frappe.set_user(user)
			self.assertIsNone(navigation.get_context())
			with self.assertRaises(frappe.PermissionError):
				navigation.set_my_home("_WL Nav B")
			navigation.on_session_creation()
			self.assertFalse(frappe.local.flags.get("home_page"))
			if user != "Guest":
				for path in ("/", "/login", "/desk"):
					with self.request(path):
						navigation.before_request()

	def test_root_login_and_desk_share_home_and_deep_links_survive(self):
		self.as_system()
		home = navigation.build_context()["home_route"]
		with patch("frappe.is_setup_complete", return_value=True):
			for path in ("/", "/login", "/desk", "/desk/"):
				with self.request(path), self.assertRaises(RequestRedirect) as redirect:
					navigation.before_request()
				self.assertEqual(redirect.exception.new_url, home)
			for path in (
				"/desk/user",
				"/desk/desktop",
				"/desk/workspace-directory",
				"/api/method/ping",
				"/login?redirect-to=/desk/user",
			):
				with self.request(path):
					navigation.before_request()
			with self.request("/desk", "POST"):
				navigation.before_request()
			navigation.on_session_creation()
			self.assertEqual(frappe.local.flags.home_page, home)

	def test_root_routing_opt_out_and_guest_login(self):
		frappe.set_user("Guest")
		with self.request("/"), self.assertRaises(RequestRedirect) as redirect:
			navigation.before_request()
		self.assertEqual(redirect.exception.new_url, "/login")
		frappe.set_user("Administrator")
		self.settings.route_root_to_workspace = 0
		self.settings.save()
		self.as_system()
		with self.request("/"):
			navigation.before_request()

	def test_disabled_and_setup_wizard_keep_native_behavior(self):
		self.as_system()
		with self.request("/desk"), patch("frappe.is_setup_complete", return_value=False):
			navigation.before_request()
		frappe.set_user("Administrator")
		self.settings.enable_workspace_navigation = 0
		self.settings.save()
		self.as_system()
		self.assertIsNone(navigation.get_context())
		with self.request("/desk"):
			navigation.before_request()

	def test_user_home_permission_and_configuration_controls(self):
		self.as_system()
		with self.assertRaises(frappe.PermissionError):
			navigation.set_my_home("_WL Nav Restricted")
		with self.assertRaises(frappe.PermissionError):
			self.rule("_WL Unauthorized Rule", "_WL Nav A")
		frappe.set_user("Administrator")
		self.settings.allow_user_workspace_home = 0
		self.settings.save()
		self.as_system()
		with self.assertRaises(frappe.PermissionError):
			navigation.set_my_home("_WL Nav A")

	def test_sso_only_normalizes_implicit_system_destinations(self):
		self.as_system()
		frappe.local.flags.whitelabel_login_home = "/desk/example"
		with self.request("/api/method/login"):
			response = Response(status=302, headers={"Location": "/apps"})
			navigation.after_request(frappe.local.request, response)
			self.assertEqual(response.headers["Location"], "/desk/example")
			for destination in ("/portal", "/desk/user", "https://example.com/apps"):
				response = Response(status=302, headers={"Location": destination})
				navigation.after_request(frappe.local.request, response)
				self.assertEqual(response.headers["Location"], destination)

	def test_published_group_shortcut_is_shared_and_permission_filtered(self):
		from frappe.desk.doctype.desktop_icon.desktop_icon import get_desktop_icons

		from whitelabel.whitelabel.doctype.whitelabel_workspace_group.whitelabel_workspace_group import (
			publish_shortcut,
		)

		frappe.get_doc(
			{
				"doctype": "Whitelabel Workspace Group",
				"title": "_WL Published Group",
				"enabled": 1,
				"workspaces": [{"workspace": "_WL Nav A"}],
			}
		).insert()
		published = publish_shortcut("_WL Published Group")
		self.assertTrue(frappe.get_value("Desktop Icon", published["icon"], "standard"))
		self.as_system()
		context = navigation.build_context()
		from frappe.boot import get_sidebar_items

		sidebars = get_sidebar_items([w["name"] for w in context["workspaces"]])
		icons = get_desktop_icons(bootinfo=frappe._dict(workspace_sidebar_item=sidebars))
		self.assertIn(published["icon"], [i.name for i in icons])
		frappe.set_user("wl-nav-other@example.test")
		boot = frappe._dict(desktop_icons=[frappe._dict(name=published["icon"], label=published["icon"])])
		navigation.extend_bootinfo(boot)
		self.assertEqual(boot.desktop_icons, [])

	def test_sidebar_and_shared_default_validation(self):
		private = frappe.get_doc(
			{
				"doctype": "Workspace",
				"label": "_WL Validation Private",
				"title": "_WL Validation Private",
				"for_user": "wl-nav-system@example.test",
				"content": "[]",
				"module": "Core",
			}
		).insert()
		with self.assertRaises(frappe.ValidationError):
			self.rule("_WL Private Rule", private.name)
		with self.assertRaises(frappe.ValidationError):
			self.rule("_WL Hidden Rule", "_WL Nav Hidden")

	def test_converted_website_user_ignores_stale_desk_defaults(self):
		user = frappe.get_doc("User", "wl-nav-portal@example.test")
		user.default_workspace = "_WL Nav B"
		user.save()
		frappe.set_user(user.name)
		navigation.on_session_creation()
		self.assertIsNone(navigation.get_context())
		with self.request("/"):
			with self.assertRaises(RequestRedirect) as redirect:
				navigation.before_request()
			self.assertEqual(redirect.exception.new_url, "/portal")
			response = Response(
				frappe.as_json({"message": "No App", "home_page": "//desk/_wl-nav-b"}),
				mimetype="application/json",
			)
			navigation.after_request(frappe.local.request, response)
			self.assertEqual(response.get_json()["home_page"], "/portal")
			response = Response(
				frappe.as_json({"message": "No App", "home_page": "/me"}), mimetype="application/json"
			)
			navigation.after_request(frappe.local.request, response)
			self.assertEqual(response.get_json()["home_page"], "/me")
