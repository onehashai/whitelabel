import frappe
from frappe.tests import IntegrationTestCase

from whitelabel.api import (
	DEFAULT_LOGO,
	get_brand_config,
	hide_standard_brand_links,
	is_documentation_url,
	is_standard_support_url,
	is_upstream_owned_url,
	update_website_context,
)


class TestWhitelabelSetting(IntegrationTestCase):
	def tearDown(self):
		frappe.clear_cache()

	def test_brand_config_defaults_and_custom_desk_title(self):
		settings = frappe._dict(
			whitelabel_app_name="Acme",
			custom_navbar_title="Acme Desk",
			application_logo=None,
			favicon=None,
			logo_height=24,
			logo_width=48,
			navbar_background_color="#112233",
			show_help_menu=1,
		)
		config = get_brand_config(settings)
		self.assertEqual(config.brand_name, "Acme")
		self.assertEqual(config.desk_title, "Acme Desk")
		self.assertEqual(config.application_logo, DEFAULT_LOGO)
		self.assertEqual(config.favicon, DEFAULT_LOGO)
		self.assertTrue(config.show_help_menu)

	def test_upstream_url_classification_is_host_scoped(self):
		self.assertTrue(is_documentation_url("https://docs.frappe.io/framework"))
		self.assertTrue(is_standard_support_url("https://frappe.io/support"))
		self.assertTrue(is_upstream_owned_url("https://discuss.frappe.io/t/help"))
		self.assertTrue(is_upstream_owned_url("https://github.com/frappe/erpnext/issues"))
		self.assertFalse(is_documentation_url("https://docs.frappe.io.example.com/framework"))
		self.assertFalse(is_standard_support_url("https://example.com/frappe.io/support"))
		self.assertFalse(is_upstream_owned_url("https://example.com/frappe/help"))

	def test_login_context_uses_configured_brand(self):
		settings = frappe.get_single("Whitelabel Setting")
		settings.whitelabel_app_name = "Acme"
		settings.save()
		previous_path = getattr(frappe.local, "path", None)
		try:
			frappe.local.path = "login"
			context = frappe._dict()
			update_website_context(context)
			self.assertEqual(context.title, "Login to Acme")
			self.assertEqual(context.footer_powered, "Powered by Acme")
		finally:
			frappe.local.path = previous_path

	def test_known_standard_website_title_is_branded(self):
		settings = frappe.get_single("Whitelabel Setting")
		settings.whitelabel_app_name = "Acme"
		settings.save()
		context = frappe._dict(title="ERPNext Certification")
		update_website_context(context)
		self.assertEqual(context.title, "Acme Certification")

	def test_standard_brand_help_items_are_removed(self):
		navbar_settings = frappe.get_single("Navbar Settings")
		navbar_settings.append(
			"help_dropdown",
			{
				"item_label": "Frappe Community Guide",
				"item_type": "Route",
				"route": "https://example.com/help",
				"is_standard": 0,
			},
		)
		bootinfo = frappe._dict(navbar_settings=navbar_settings)
		hide_standard_brand_links(bootinfo)
		labels = [item.item_label for item in bootinfo.navbar_settings.help_dropdown]
		self.assertNotIn("About", labels)
		self.assertNotIn("Frappe Support", labels)
		self.assertIn("Frappe Community Guide", labels)

	def test_all_upstream_owned_standard_help_items_are_removed(self):
		bootinfo = frappe._dict(
			navbar_settings={
				"help_dropdown": [
					{"item_label": "Documentation", "route": "https://docs.erpnext.com/", "is_standard": 1},
					{"item_label": "User Forum", "route": "https://discuss.frappe.io", "is_standard": 1},
					{
						"item_label": "Report an Issue",
						"route": "https://github.com/frappe/erpnext/issues",
						"is_standard": 1,
					},
					{"item_label": "Company Help", "route": "https://help.example.com", "is_standard": 1},
				]
			}
		)
		hide_standard_brand_links(bootinfo)
		self.assertEqual(
			[item["item_label"] for item in bootinfo.navbar_settings["help_dropdown"]],
			["Company Help"],
		)

	def test_desk_boot_contains_only_branded_product_chrome(self):
		from frappe.sessions import get as get_boot

		previous_user = frappe.session.user
		previous_request = getattr(frappe.local, "request", None)
		try:
			frappe.set_user("Administrator")
			frappe.local.request = None
			bootinfo = get_boot()
			labels = [item.item_label for item in bootinfo.navbar_settings.help_dropdown]
			self.assertNotIn("About", labels)
			self.assertNotIn("Frappe Support", labels)
			self.assertEqual(bootinfo.whitelabel_setting.brand_name, "OneHash")
			self.assertEqual(bootinfo.changelog_feed, [])
			self.assertEqual(bootinfo.marketplace_apps, [])
			for app in bootinfo.app_data:
				if app.get("app_name") in {"frappe", "erpnext", "whitelabel"}:
					self.assertEqual(app.get("app_title"), "OneHash")
					self.assertEqual(app.get("app_logo_url"), DEFAULT_LOGO)
		finally:
			frappe.local.request = previous_request
			frappe.set_user(previous_user)

	def test_settings_apply_to_supported_v16_singletons(self):
		settings = frappe.get_single("Whitelabel Setting")
		settings.whitelabel_app_name = "Acme"
		settings.custom_navbar_title = "Acme Desk"
		settings.application_logo = None
		settings.favicon = None
		settings.show_help_menu = 0
		settings.save()

		system_settings = frappe.get_single("System Settings")
		website_settings = frappe.get_single("Website Settings")
		navbar_settings = frappe.get_single("Navbar Settings")
		self.assertEqual(system_settings.app_name, "Acme")
		self.assertEqual(system_settings.otp_issuer_name, "Acme")
		self.assertEqual(system_settings.enable_onboarding, 0)
		self.assertEqual(system_settings.disable_product_suggestion, 1)
		self.assertEqual(system_settings.disable_standard_email_footer, 1)
		self.assertEqual(system_settings.hide_footer_in_auto_email_reports, 1)
		self.assertEqual(website_settings.app_name, "Acme")
		self.assertEqual(website_settings.app_logo, DEFAULT_LOGO)
		self.assertEqual(website_settings.favicon, DEFAULT_LOGO)
		self.assertEqual(website_settings.footer_powered, "Powered by Acme")
		self.assertEqual(navbar_settings.app_logo, DEFAULT_LOGO)
		settings.apply_branding_settings()
		self.assertEqual(frappe.db.get_single_value("System Settings", "app_name"), "Acme")

	def test_private_logo_is_rejected(self):
		settings = frappe.get_single("Whitelabel Setting")
		settings.application_logo = "/private/files/secret-logo.svg"
		with self.assertRaises(frappe.ValidationError):
			settings.save()
