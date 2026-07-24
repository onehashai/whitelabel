from __future__ import annotations

import re
from functools import wraps
from urllib.parse import urlparse

import frappe
from bs4 import BeautifulSoup, Comment

from whitelabel.api import (
	DEFAULT_LOGO,
	get_brand_name,
	get_whitelabel_settings,
	is_documentation_url,
	is_standard_support_url,
)


BRAND_PATTERN = re.compile(r"Frappe Framework|ERPNext|Frappe", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+")
SKIPPED_TEXT_PARENTS = {"code", "pre", "script", "style", "textarea"}
BRANDED_ATTRIBUTES = ("alt", "aria-label", "placeholder", "title")


def get_active_brand_name():
	settings = get_whitelabel_settings()
	return get_brand_name(settings) if settings else None


def is_standard_brand_url(value):
	if is_documentation_url(value) or is_standard_support_url(value):
		return True

	try:
		parsed = urlparse(value)
	except (TypeError, ValueError):
		return False

	host = (parsed.hostname or "").lower()
	path = (parsed.path or "").lower()
	return host in {"frappe.io", "www.frappe.io"} and path.startswith("/erpnext")


def replace_brand_text(value, brand_name):
	if not isinstance(value, str) or not brand_name:
		return value

	value = BRAND_PATTERN.sub(brand_name, value)

	def remove_standard_url(match):
		url = match.group(0)
		clean_url = url.rstrip(".,);]}")
		suffix = url[len(clean_url) :]
		return suffix if is_standard_brand_url(clean_url) else url

	return URL_PATTERN.sub(remove_standard_url, value)


def sanitize_brand_html(value, brand_name=None):
	if not isinstance(value, str) or not value:
		return value

	brand_name = brand_name or get_active_brand_name()
	if not brand_name:
		return value

	soup = BeautifulSoup(value, "html.parser")

	for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
		if BRAND_PATTERN.search(str(comment)):
			comment.extract()

	for text_node in list(soup.find_all(string=True)):
		if isinstance(text_node, Comment) or text_node.parent.name in SKIPPED_TEXT_PARENTS:
			continue
		replacement = replace_brand_text(str(text_node), brand_name)
		if replacement != str(text_node):
			text_node.replace_with(replacement)

	for element in soup.find_all(True):
		for attribute in BRANDED_ATTRIBUTES:
			if element.has_attr(attribute):
				element[attribute] = replace_brand_text(str(element[attribute]), brand_name)

		if element.name == "meta" and str(element.get("name", "")).lower() == "generator":
			element["content"] = brand_name

		href = element.get("href")
		if href and is_standard_brand_url(href):
			if element.name == "a":
				element.unwrap()
			else:
				del element["href"]

	return str(soup)


def sanitize_html_response(response, request):
	content_type = response.headers.get("Content-Type", "")
	if "text/html" not in content_type.lower() or response.is_streamed:
		return

	try:
		html = response.get_data(as_text=True)
	except (RuntimeError, UnicodeDecodeError):
		return

	sanitized = sanitize_brand_html(html)
	if sanitized != html:
		response.set_data(sanitized)


def update_website_context(context):
	brand_name = get_active_brand_name()
	if not brand_name:
		return

	settings = get_whitelabel_settings()
	context["app_name"] = brand_name
	context["footer_powered"] = f"Powered by {frappe.utils.escape_html(brand_name)}"
	context["favicon"] = settings.favicon or settings.application_logo or DEFAULT_LOGO


def sanitize_email_message(email_message):
	brand_name = get_active_brand_name()
	if not brand_name:
		return

	subject = email_message.msg_root.get("Subject")
	if subject:
		email_message.set_header("Subject", replace_brand_text(str(subject), brand_name))

	for part in email_message.msg_root.walk():
		content_type = part.get_content_type()
		if part.is_multipart() or content_type not in {"text/html", "text/plain"}:
			continue

		charset = part.get_content_charset() or "utf-8"
		payload = part.get_payload(decode=True)
		if payload is None:
			continue

		try:
			text = payload.decode(charset)
		except (LookupError, UnicodeDecodeError):
			text = payload.decode("utf-8", errors="replace")
			charset = "utf-8"

		sanitized = (
			sanitize_brand_html(text, brand_name)
			if content_type == "text/html"
			else replace_brand_text(text, brand_name)
		)
		if sanitized == text:
			continue

		if part.get("Content-Transfer-Encoding"):
			del part["Content-Transfer-Encoding"]
		part.set_payload(sanitized, charset=charset)


def install_print_sanitizer(**kwargs):
	from frappe.website import serve

	if getattr(serve.get_response_without_exception_handling, "_whitelabel_sanitized", False):
		return

	original_get_response = serve.get_response_without_exception_handling

	@wraps(original_get_response)
	def sanitized_get_response(path, *args, **response_kwargs):
		response = original_get_response(path, *args, **response_kwargs)
		if path != "printview":
			return response

		try:
			html = response.get_data(as_text=True)
		except (AttributeError, RuntimeError, UnicodeDecodeError):
			return response

		sanitized = sanitize_brand_html(html)
		if sanitized != html:
			response.set_data(sanitized)
		return response

	sanitized_get_response._whitelabel_sanitized = True
	serve.get_response_without_exception_handling = sanitized_get_response
