# -*- coding: utf-8 -*-
# Copyright (c) 2021, Bhavesh Maheshwari and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.utils.data import escape_html


DEFAULT_BRAND = "OneHash"


class WhitelabelSetting(Document):
	def validate(self):
		self.apply_branding_settings()

	def apply_branding_settings(self):
		system_settings_doc = frappe.get_doc("System Settings", "System Settings")
		navbar_settings_doc = frappe.get_doc("Navbar Settings", "Navbar Settings")
		website_doc = frappe.get_doc("Website Settings", "Website Settings")

		self.enforce_required_controls()
		self.set_app_name(system_settings_doc, website_doc)
		self.set_theme_attr(navbar_settings_doc, website_doc)
		self.disable_onboarding(system_settings_doc)
		self.set_log_notification(system_settings_doc)
		self.set_footer(system_settings_doc, website_doc)

		system_settings_doc.save(ignore_permissions=True)
		navbar_settings_doc.save(ignore_permissions=True)
		website_doc.save(ignore_permissions=True)
		frappe.clear_cache()

	def enforce_required_controls(self):
		self.ignore_onboard_whitelabel = 1
		self.disable_new_update_popup = 1
		self.disable_standard_footer = 1

	def get_brand_name(self):
		brand_name = self.whitelabel_app_name or self.custom_navbar_title or DEFAULT_BRAND
		for source in ("Frappe Framework", "ERPNext", "Frappe"):
			brand_name = brand_name.replace(source, DEFAULT_BRAND)
		return brand_name

	def set_app_name(self, system_settings_doc, website_doc):
		brand_name = self.get_brand_name()
		system_settings_doc.app_name = brand_name
		system_settings_doc.otp_issuer_name = brand_name
		website_doc.app_name = brand_name
		alt_text = escape_html(brand_name)

		if self.application_logo:
			logo = escape_html(self.application_logo)
			website_doc.brand_html = f'<img src="{logo}" alt="{alt_text}">'
		else:
			website_doc.brand_html = alt_text

	def set_theme_attr(self, navbar_settings_doc, website_doc):
		logo = self.application_logo or ""
		navbar_settings_doc.app_logo = logo
		website_doc.app_logo = logo
		website_doc.splash_image = logo
		website_doc.favicon = self.favicon or logo

	def disable_onboarding(self, system_settings_doc):
		system_settings_doc.enable_onboarding = 0

	def set_log_notification(self, system_settings_doc):
		system_settings_doc.disable_system_update_notification = 1
		system_settings_doc.disable_change_log_notification = 1

	def set_footer(self, system_settings_doc, website_doc):
		website_doc.footer_powered = f"Powered by {escape_html(self.get_brand_name())}"
		system_settings_doc.email_footer_address = self.email_footer_address
		system_settings_doc.disable_standard_email_footer = 1
		system_settings_doc.hide_footer_in_auto_email_reports = 1
