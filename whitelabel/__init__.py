# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__version__ = "0.0.1"

try:
    import frappe

    if frappe.conf and frappe.conf.get("app_logo_url"):
        __logo__ = (
            frappe.conf.get("app_logo_url")
            or "/assets/whitelabel/images/whitelabel_logo.svg"
        )
    else:
        raise Exception
except:
    __logo__ = "/assets/whitelabel/images/whitelabel_logo.svg"

