from __future__ import unicode_literals

from urllib.parse import urlparse

import frappe


BRANDED_APPS = {"frappe", "erpnext"}
DEFAULT_BRAND = "OneHash"
DEFAULT_LOGO = "/assets/whitelabel/images/whitelabel_logo.svg"
DOCUMENTATION_HOSTS = {
	"docs.erpnext.com",
	"docs.frappe.io",
	"docs.frappeframework.com",
	"frappeframework.com",
}
STANDARD_SUPPORT_HOSTS = {
	"support.frappe.io",
}


def get_whitelabel_settings():
	if not frappe.db.exists("DocType", "Whitelabel Setting"):
		return None

	return frappe.get_cached_doc("Whitelabel Setting")


def get_brand_name(settings):
	configured_name = settings.whitelabel_app_name or settings.custom_navbar_title or DEFAULT_BRAND
	return replace_brand_terms(configured_name)


def replace_brand_terms(value):
	if not isinstance(value, str):
		return value

	for source in ("Frappe Framework", "ERPNext", "Frappe"):
		value = value.replace(source, DEFAULT_BRAND)
	return value


def is_documentation_url(value):
	if not value or not isinstance(value, str):
		return False

	try:
		parsed = urlparse(value)
	except ValueError:
		return False

	host = (parsed.hostname or "").lower()
	path = (parsed.path or "").lower()
	return (
		host in DOCUMENTATION_HOSTS
		or host.endswith(".docs.frappe.io")
		or host.endswith(".docs.erpnext.com")
		or (host in {"erpnext.com", "www.erpnext.com"} and path.startswith("/docs"))
	)


def is_standard_support_url(value):
	if not value or not isinstance(value, str):
		return False

	try:
		parsed = urlparse(value)
	except ValueError:
		return False

	host = (parsed.hostname or "").lower()
	path = (parsed.path or "").lower()
	return (
		host in STANDARD_SUPPORT_HOSTS
		or (host in {"frappe.io", "www.frappe.io"} and path.startswith("/helpdesk"))
		or (host in {"frappecloud.com", "www.frappecloud.com"} and path.startswith("/support"))
	)


def hide_standard_brand_links(bootinfo):
	navbar_settings = getattr(bootinfo, "navbar_settings", None)
	if not navbar_settings:
		return

	help_dropdown = navbar_settings.get("help_dropdown") or []
	filtered_items = []
	for item in help_dropdown:
		label = item.get("item_label") or ""
		action = item.get("action") or ""
		route = item.get("route") or ""
		if (
			"frappe" in label.lower()
			or "erpnext" in label.lower()
			or "show_about" in action
			or is_documentation_url(route)
			or is_standard_support_url(route)
		):
			continue
		if isinstance(item, dict):
			item["item_label"] = replace_brand_terms(label)
		else:
			item.item_label = replace_brand_terms(label)
		filtered_items.append(item)

	if isinstance(navbar_settings, dict):
		navbar_settings["help_dropdown"] = filtered_items
	else:
		navbar_settings.set("help_dropdown", filtered_items)


def whitelabel_patch():
	"""Reapply supported branding settings after a site migration."""
	if settings := get_whitelabel_settings():
		settings.save(ignore_permissions=True)


def boot_session(bootinfo):
	"""Expose branding and adapt v16 Desk metadata for system users."""
	if frappe.session.user == "Guest":
		return

	settings = get_whitelabel_settings()
	if not settings:
		return

	brand_name = get_brand_name(settings)
	logo = settings.application_logo or DEFAULT_LOGO

	bootinfo.whitelabel_setting = frappe._dict(
		{
			"application_logo": logo,
			"logo_height": settings.logo_height,
			"logo_width": settings.logo_width,
			"navbar_background_color": settings.navbar_background_color,
			"show_help_menu": settings.show_help_menu,
			"whitelabel_app_name": brand_name,
		}
	)
	bootinfo.app_logo_url = logo
	bootinfo.changelog_feed = []
	bootinfo.has_app_updates = False
	bootinfo.onboarding_tours = []
	if getattr(bootinfo, "sysdefaults", None):
		bootinfo.sysdefaults["disable_change_log_notification"] = 1
		bootinfo.sysdefaults["disable_system_update_notification"] = 1
		bootinfo.sysdefaults["enable_onboarding"] = 0

	for app in getattr(bootinfo, "app_data", []):
		app["app_title"] = replace_brand_terms(app.get("app_title"))
		if app.get("app_name") in BRANDED_APPS:
			app["app_title"] = brand_name
			app["app_logo_url"] = logo

	renamed_icon_labels = {}
	workspace_sidebar_items = getattr(bootinfo, "workspace_sidebar_item", {})
	for icon in getattr(bootinfo, "desktop_icons", []):
		old_label = icon.get("label")
		new_label = replace_brand_terms(old_label)
		if old_label and new_label != old_label:
			renamed_icon_labels[old_label] = new_label
			icon["label"] = new_label

			sidebar = workspace_sidebar_items.get(old_label.lower())
			if sidebar:
				sidebar["label"] = new_label
				workspace_sidebar_items[new_label.lower()] = sidebar

		if icon.get("icon_type") == "App" and icon.get("app") in BRANDED_APPS:
			icon["logo_url"] = logo

	for icon in getattr(bootinfo, "desktop_icons", []):
		parent_icon = icon.get("parent_icon")
		if parent_icon in renamed_icon_labels:
			icon["parent_icon"] = renamed_icon_labels[parent_icon]

	hide_standard_brand_links(bootinfo)
