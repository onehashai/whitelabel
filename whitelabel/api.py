from __future__ import unicode_literals
import frappe
import re
import json
from frappe.utils import floor, flt, today, cint
from frappe import _
from frappe.installer import update_site_config

DEFAULT_APP_LOGO = "/assets/whitelabel/images/whitelabel_logo.svg"

def whitelabel_patch():
	ensure_default_logo()
	#delete erpnext welcome page
	frappe.delete_doc_if_exists('Page', 'welcome-to-erpnext', force=1)
	#update Welcome Blog Post
	if frappe.db.exists("Blog Post", "Welcome"):
		frappe.db.set_value("Blog Post","Welcome","content","")
	update_field_label()
	brand_name = frappe.get_hooks("brand_name")[0]
	update_onboard_details(brand_name)
	update_website_settings(brand_name)
	update_system_settings(brand_name)

def ensure_default_logo():
	logo = (
		frappe.db.get_single_value("Whitelabel Setting", "application_logo")
		or frappe.db.get_single_value("Website Settings", "app_logo")
		or frappe.db.get_single_value("Navbar Settings", "app_logo")
		or frappe.conf.get("app_logo_url")
		or DEFAULT_APP_LOGO
	)

	for doctype, fieldname in (
		("Whitelabel Setting", "application_logo"),
		("Website Settings", "app_logo"),
		("Website Settings", "splash_image"),
		("Navbar Settings", "app_logo"),
	):
		if not frappe.db.get_single_value(doctype, fieldname):
			frappe.db.set_single_value(doctype, fieldname, logo)

	if not frappe.conf.get("app_logo_url"):
		update_site_config("app_logo_url", logo)

	frappe.clear_cache()
	
def boot_session(bootinfo):
	"""boot session - send website info if guest"""
	if frappe.session['user']!='Guest':
		bootinfo.whitelabel_setting = frappe.get_doc("Whitelabel Setting","Whitelabel Setting")
		bootinfo.app_logo_url = (
			frappe.db.get_single_value("Website Settings", "app_logo")
			or frappe.db.get_single_value("Navbar Settings", "app_logo")
			or frappe.conf.get("app_logo_url")
			or DEFAULT_APP_LOGO
		)

def enforce_default_logo(doc, method=None):
	if not doc.app_logo:
		doc.app_logo = DEFAULT_APP_LOGO

	if doc.doctype == "Website Settings" and not doc.splash_image:
		doc.splash_image = DEFAULT_APP_LOGO

@frappe.whitelist()
def ignore_update_popup():
	if not frappe.db.get_single_value('Whitelabel Setting', 'disable_new_update_popup'):
		show_update_popup_update()

def update_field_label():
	"""Update label of section break in employee doctype"""
	frappe.db.sql("""Update `tabDocField` set label='OneHash' where fieldname='erpnext_user' and parent='Employee'""")

def update_website_settings(brand_name):
	frappe.db.set_value("Website Settings", "Website Settings", "app_name", brand_name)
	frappe.db.commit()

def update_system_settings(brand_name):
	frappe.db.set_value("System Settings", "System Settings", "otp_issuer_name", brand_name)
	frappe.db.commit()

def update_onboard_details(brand_name):
	update_onboard_module(brand_name)
	update_onboard_steps(brand_name)

def update_onboard_module(brand_name):
	onboard_module_details = frappe.get_all("Module Onboarding",filters={},fields=["name"])
	for row in onboard_module_details:
		doc = frappe.get_doc("Module Onboarding",row.name)
		doc.title = re.sub("ERPNext", brand_name, doc.title)
		doc.success_message = re.sub("ERPNext", brand_name, doc.success_message)
		doc.documentation_url = ""
		doc.flags.ignore_mandatory = True
		doc.save(ignore_permissions = True)

def update_onboard_steps(brand_name):
	onboard_steps_details = frappe.get_all("Onboarding Step",filters={},fields=["name"])
	for row in onboard_steps_details:
		doc = frappe.get_doc("Onboarding Step",row.name)
		if doc.title:
			doc.title = re.sub("ERPNext", brand_name, doc.title)
		if doc.description:
			doc.description = re.sub("ERPNext", brand_name, doc.description)
		doc.intro_video_url = ""
		if doc.title == "Introduction to Website":
			doc.video_url = ""
		doc.flags.ignore_mandatory = True
		doc.save(ignore_permissions = True)

@frappe.whitelist()
def show_update_popup_update():
	cache = frappe.cache()
	user  = frappe.session.user
	update_info = cache.get_value("update-info")
	if not update_info:
		return

	updates = json.loads(update_info)

	# Check if user is int the set of users to send update message to
	update_message = ""
	if cache.sismember("update-user-set", user):
		for update_type in updates:
			release_links = ""
			for app in updates[update_type]:
				app = frappe._dict(app)
				release_links += "<b>{title}</b>: <a href='https://github.com/{org_name}/{app_name}/releases/tag/v{available_version}'>v{available_version}</a><br>".format(
					available_version = app.available_version,
					org_name          = app.org_name,
					app_name          = app.app_name,
					title             = app.title
				)
			if release_links:
				message = _("New {} releases for the following apps are available").format(_(update_type))
				update_message += "<div class='new-version-log'>{0}<div class='new-version-links'>{1}</div></div>".format(message, release_links)

	if update_message:
		frappe.msgprint(update_message, title=_("New updates are available"), indicator='green')
		cache.srem("update-user-set", user)
