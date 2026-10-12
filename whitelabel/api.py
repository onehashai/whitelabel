from __future__ import annotations

import re
from urllib.parse import urlparse

import frappe
from frappe.utils import cint
from frappe.utils.data import escape_html

BRANDED_APPS = {"frappe", "erpnext", "whitelabel"}
DEFAULT_BRAND = "OneHash"
DEFAULT_LOGO = "/assets/whitelabel/images/whitelabel_logo.svg"
UPSTREAM_BRAND_PATTERN = re.compile(r"Frappe Framework|ERPNext|Frappe", re.IGNORECASE)
DOCUMENTATION_HOSTS = {
	"docs.erpnext.com",
	"docs.frappe.io",
	"docs.frappeframework.com",
	"frappeframework.com",
	"www.frappeframework.com",
}
STANDARD_SUPPORT_HOSTS = {"support.frappe.io"}
KNOWN_UPSTREAM_PAGE_TITLES = {"ERPNext Certification"}
UPSTREAM_OWNED_HOSTS = {
	"discuss.frappe.io",
	"school.frappe.io",
	"frappe.io",
	"www.frappe.io",
	"frappecloud.com",
	"www.frappecloud.com",
}


def get_whitelabel_settings():
	if not frappe.db.exists("DocType", "Whitelabel Setting"):
		return None

	return frappe.get_cached_doc("Whitelabel Setting")


def replace_brand_terms(value, replacement=DEFAULT_BRAND):
	if not isinstance(value, str):
		return value
	return UPSTREAM_BRAND_PATTERN.sub(replacement, value)


def _validated_pixels(value):
	value = cint(value)
	return value if 8 <= value <= 200 else None


def get_brand_config(settings=None):
	settings = settings or get_whitelabel_settings()
	if not settings:
		return frappe._dict(
			brand_name=DEFAULT_BRAND,
			desk_title=DEFAULT_BRAND,
			application_logo=DEFAULT_LOGO,
			favicon=DEFAULT_LOGO,
			logo_height=None,
			logo_width=None,
			sidebar_background_color=None,
			show_help_menu=False,
		)

	brand_name = (settings.whitelabel_app_name or DEFAULT_BRAND).strip() or DEFAULT_BRAND
	brand_name = replace_brand_terms(brand_name)
	desk_title = (settings.custom_navbar_title or brand_name).strip() or brand_name
	desk_title = replace_brand_terms(desk_title, brand_name)
	logo = settings.application_logo or DEFAULT_LOGO

	return frappe._dict(
		brand_name=brand_name,
		desk_title=desk_title,
		application_logo=logo,
		favicon=settings.favicon or logo,
		logo_height=_validated_pixels(settings.logo_height),
		logo_width=_validated_pixels(settings.logo_width),
		sidebar_background_color=settings.navbar_background_color or None,
		show_help_menu=bool(cint(settings.show_help_menu)),
	)


def _hostname(value):
	if not value or not isinstance(value, str):
		return "", ""
	try:
		parsed = urlparse(value)
	except ValueError:
		return "", ""
	return (parsed.hostname or "").lower(), (parsed.path or "").lower()


def is_documentation_url(value):
	host, path = _hostname(value)
	return bool(
		host in DOCUMENTATION_HOSTS
		or host.endswith(".docs.frappe.io")
		or host.endswith(".docs.erpnext.com")
		or (host in {"erpnext.com", "www.erpnext.com"} and path.startswith("/docs"))
	)


def is_standard_support_url(value):
	host, path = _hostname(value)
	return bool(
		host in STANDARD_SUPPORT_HOSTS
		or (host in {"frappe.io", "www.frappe.io"} and path.startswith(("/helpdesk", "/support")))
		or (host in {"frappecloud.com", "www.frappecloud.com"} and path.startswith("/support"))
	)


def is_upstream_owned_url(value):
	host, path = _hostname(value)
	if is_documentation_url(value) or is_standard_support_url(value):
		return True
	if host in UPSTREAM_OWNED_HOSTS:
		return True
	return host == "github.com" and path.startswith(("/frappe/", "/frappehq/"))


def is_upstream_standard_help_item(item):
	if not cint(item.get("is_standard")):
		return False

	label = item.get("item_label") or ""
	action = item.get("action") or ""
	route = item.get("route") or ""
	return bool(
		UPSTREAM_BRAND_PATTERN.search(label) or "show_about" in action or is_upstream_owned_url(route)
	)


def hide_standard_brand_links(bootinfo):
	navbar_settings = getattr(bootinfo, "navbar_settings", None)
	if not navbar_settings:
		return

	filtered_items = []
	for item in navbar_settings.get("help_dropdown") or []:
		if is_upstream_standard_help_item(item):
			continue
		filtered_items.append(item)

	if hasattr(navbar_settings, "set"):
		navbar_settings.set("help_dropdown", filtered_items)
	else:
		navbar_settings["help_dropdown"] = filtered_items


def sanitize_navbar_settings():
	"""Remove upstream-owned links from the persisted v16 Navbar Settings."""
	navbar_settings = frappe.get_single("Navbar Settings")
	items = navbar_settings.get("help_dropdown") or []
	filtered_items = [item for item in items if not is_upstream_standard_help_item(item)]
	if len(filtered_items) == len(items):
		return

	navbar_settings.set("help_dropdown", filtered_items)
	navbar_settings.save(ignore_permissions=True)


def whitelabel_patch():
	"""Reapply supported branding settings after schema migration."""
	settings = get_whitelabel_settings()
	if settings:
		settings.apply_branding_settings()


def extend_bootinfo(bootinfo):
	"""Remove promotional data added after the regular boot-session hooks."""
	if frappe.session.user == "Guest" or not get_whitelabel_settings():
		return

	bootinfo["changelog_feed"] = []
	bootinfo["marketplace_apps"] = []
	bootinfo["onboarding_tours"] = []


def boot_session(bootinfo):
	"""Expose normalized branding and adapt Frappe v16 Desk metadata."""
	if frappe.session.user == "Guest":
		return

	settings = get_whitelabel_settings()
	if not settings:
		return

	config = get_brand_config(settings)
	bootinfo.whitelabel_setting = config
	bootinfo.onboarding_tours = []

	if getattr(bootinfo, "sysdefaults", None):
		bootinfo.sysdefaults["disable_change_log_notification"] = 1
		bootinfo.sysdefaults["disable_system_update_notification"] = 1
		bootinfo.sysdefaults["disable_product_suggestion"] = 1
		bootinfo.sysdefaults["enable_onboarding"] = 0

	for app in getattr(bootinfo, "app_data", []):
		if app.get("app_name") in BRANDED_APPS:
			app["app_title"] = config.desk_title
			app["app_logo_url"] = config.application_logo

	renamed_icon_labels = {}
	workspace_sidebar_items = getattr(bootinfo, "workspace_sidebar_item", {})
	for icon in getattr(bootinfo, "desktop_icons", []):
		old_label = icon.get("label")
		new_label = replace_brand_terms(old_label, config.desk_title)
		if old_label and new_label != old_label:
			renamed_icon_labels[old_label] = new_label
			icon["label"] = new_label
			sidebar = workspace_sidebar_items.get(old_label.lower())
			if sidebar:
				sidebar["label"] = new_label
				workspace_sidebar_items[new_label.lower()] = sidebar

		if icon.get("icon_type") == "App" and icon.get("app") in BRANDED_APPS:
			icon["logo_url"] = config.application_logo

	for icon in getattr(bootinfo, "desktop_icons", []):
		if icon.get("parent_icon") in renamed_icon_labels:
			icon["parent_icon"] = renamed_icon_labels[icon["parent_icon"]]

	hide_standard_brand_links(bootinfo)


def update_website_context(context):
	settings = get_whitelabel_settings()
	if not settings:
		return

	config = get_brand_config(settings)
	context["app_name"] = config.brand_name
	context["favicon"] = config.favicon
	context["splash_image"] = config.application_logo
	context["brand_html"] = (
		f'<img src="{escape_html(config.application_logo)}" alt="{escape_html(config.brand_name)}">'
	)
	context["footer_powered"] = f"Powered by {escape_html(config.brand_name)}"
	if context.get("title") in KNOWN_UPSTREAM_PAGE_TITLES:
		context["title"] = replace_brand_terms(context["title"], config.brand_name)
	if getattr(frappe.local, "path", "").strip("/") == "login":
		context["title"] = f"Login to {config.brand_name}"
