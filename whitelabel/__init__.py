# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe

from .version import __version__

if frappe.conf and frappe.conf.get("app_logo_url"):
    __logo__ = frappe.conf.get("app_logo_url") or '/assets/whitelabel/images/whitelabel_logo.svg'
else:
    __logo__ = '/assets/whitelabel/images/whitelabel_logo.svg'