from __future__ import annotations

from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import escape_html

from whitelabel.api import (
	DEFAULT_BRAND,
	UPSTREAM_BRAND_PATTERN,
	get_brand_config,
	sanitize_navbar_settings,
)


class WhitelabelSetting(Document):
	def validate(self):
		self._validate_branding()
		self._enforce_required_controls()

	def on_update(self):
		self.apply_branding_settings()

	def _validate_branding(self):
		self.whitelabel_app_name = (self.whitelabel_app_name or DEFAULT_BRAND).strip()
		if UPSTREAM_BRAND_PATTERN.search(self.whitelabel_app_name):
			frappe.throw(_("Whitelabel App Name cannot contain Frappe or ERPNext."))

		if self.custom_navbar_title:
			self.custom_navbar_title = self.custom_navbar_title.strip()
			if UPSTREAM_BRAND_PATTERN.search(self.custom_navbar_title):
				frappe.throw(_("Navbar Title cannot contain Frappe or ERPNext."))

		for fieldname in ("application_logo", "favicon"):
			value = self.get(fieldname)
			if not value:
				continue
			path = urlparse(value).path
			if path.startswith("/private/"):
				frappe.throw(
					_("{0} must be a public file so it is visible before login.").format(
						self.meta.get_label(fieldname)
					)
				)

		for fieldname in ("logo_height", "logo_width"):
			value = self.get(fieldname)
			if value and not 8 <= value <= 200:
				frappe.throw(
					_("{0} must be between 8 and 200 pixels.").format(self.meta.get_label(fieldname))
				)

	def _enforce_required_controls(self):
		self.ignore_onboard_whitelabel = 1
		self.disable_new_update_popup = 1
		self.disable_standard_footer = 1

	def apply_branding_settings(self):
		config = get_brand_config(self)
		frappe.db.set_single_value(
			"System Settings",
			{
				"app_name": config.brand_name,
				"otp_issuer_name": config.brand_name,
				"enable_onboarding": 0,
				"disable_system_update_notification": 1,
				"disable_change_log_notification": 1,
				"disable_product_suggestion": 1,
				"email_footer_address": self.email_footer_address,
				"disable_standard_email_footer": 1,
				"hide_footer_in_auto_email_reports": 1,
			},
		)
		frappe.db.set_single_value("Navbar Settings", "app_logo", config.application_logo)
		sanitize_navbar_settings()
		frappe.db.set_single_value(
			"Website Settings",
			{
				"app_name": config.brand_name,
				"app_logo": config.application_logo,
				"splash_image": config.application_logo,
				"favicon": config.favicon,
				"brand_html": (
					f'<img src="{escape_html(config.application_logo)}" '
					f'alt="{escape_html(config.brand_name)}">'
				),
				"footer_powered": f"Powered by {escape_html(config.brand_name)}",
			},
		)

		frappe.clear_cache()
