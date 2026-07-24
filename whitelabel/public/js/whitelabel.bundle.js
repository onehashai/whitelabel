frappe.provide("whitelabel");

whitelabel.BRAND_NAME = "OneHash";
whitelabel.BRAND_PATTERN = /Frappe Framework|ERPNext|Frappe/gi;

whitelabel.replace_brand_terms = function (value) {
	if (typeof value !== "string") {
		return value;
	}
	return value.replace(whitelabel.BRAND_PATTERN, whitelabel.BRAND_NAME);
};

whitelabel.is_documentation_url = function (href) {
	if (!href) {
		return false;
	}

	try {
		const url = new URL(href, window.location.origin);
		const host = url.hostname.toLowerCase();
		const path = url.pathname.toLowerCase();
		return (
			host === "docs.erpnext.com" ||
			host.endsWith(".docs.erpnext.com") ||
			host === "docs.frappe.io" ||
			host.endsWith(".docs.frappe.io") ||
			host === "docs.frappeframework.com" ||
			host === "frappeframework.com" ||
			host === "www.frappeframework.com" ||
			((host === "erpnext.com" || host === "www.erpnext.com") &&
				path.startsWith("/docs"))
		);
	} catch (error) {
		return false;
	}
};

whitelabel.is_standard_support_url = function (href) {
	if (!href) {
		return false;
	}

	try {
		const url = new URL(href, window.location.origin);
		const host = url.hostname.toLowerCase();
		const path = url.pathname.toLowerCase();
		return (
			host === "support.frappe.io" ||
			((host === "frappe.io" || host === "www.frappe.io") &&
				path.startsWith("/helpdesk")) ||
			((host === "frappecloud.com" || host === "www.frappecloud.com") &&
				path.startsWith("/support"))
		);
	} catch (error) {
		return false;
	}
};

whitelabel.is_standard_support_label = function (value) {
	return (
		typeof value === "string" &&
		/^(Frappe|OneHash)\s+Support$/i.test(value.trim())
	);
};

whitelabel.is_hidden_profile_label = function (value) {
	return (
		typeof value === "string" &&
		(value.trim().toLowerCase() === "about" ||
			whitelabel.is_standard_support_label(value))
	);
};

whitelabel.is_standard_support_item = function (item) {
	if (!item) {
		return false;
	}

	const label = item.label || item.item_label || "";
	const url = item.url || item.route || item.href || "";
	const action = item.action || "";
	return (
		whitelabel.is_standard_support_label(label) ||
		whitelabel.is_standard_support_url(url) ||
		/support\.frappe\.io|frappe\.io\/helpdesk|frappecloud\.com\/support/i.test(action)
	);
};

whitelabel.hide_standard_support_item = function (node) {
	const item = node?.closest?.(".dropdown-menu-item, [role='menuitem'], a[href]");
	if (!item) {
		return;
	}

	item.classList.add("whitelabel-hidden-standard-support");
	item.setAttribute("aria-hidden", "true");
	item.setAttribute("tabindex", "-1");
};

whitelabel.filter_sidebar_help_items = function (items) {
	return (items || []).filter((item) => !whitelabel.is_standard_support_item(item));
};

whitelabel.filter_standard_menu_items = function (items) {
	return (items || [])
		.filter(
			(item) =>
				!whitelabel.is_hidden_profile_label(item?.label) &&
				!whitelabel.is_standard_support_item(item)
		)
		.map((item) => {
			if (!item?.items) {
				return item;
			}
			return {
				...item,
				items: whitelabel.filter_standard_menu_items(item.items),
			};
		});
};

whitelabel.patch_menu_renderer = function () {
	const Menu = frappe.ui?.menu;
	if (!Menu || Menu.prototype.__whitelabel_menu_patched) {
		return;
	}

	const make = Menu.prototype.make;
	if (typeof make !== "function") {
		return;
	}

	Menu.prototype.make = function () {
		this.menu_items = whitelabel.filter_standard_menu_items(this.menu_items);
		return make.call(this);
	};
	Menu.prototype.__whitelabel_menu_patched = true;
};

whitelabel.patch_sidebar_help_menu = function () {
	const SidebarHeader = frappe.ui?.SidebarHeader;
	if (!SidebarHeader || SidebarHeader.prototype.__whitelabel_help_patched) {
		return;
	}

	const get_help_siblings = SidebarHeader.prototype.get_help_siblings;
	if (typeof get_help_siblings !== "function") {
		return;
	}

	SidebarHeader.prototype.get_help_siblings = function () {
		return whitelabel.filter_sidebar_help_items(get_help_siblings.call(this));
	};
	SidebarHeader.prototype.__whitelabel_help_patched = true;
};

whitelabel.filter_help_links = function () {
	const help_links = frappe.help?.help_links;
	if (!help_links) {
		return;
	}

	Object.keys(help_links).forEach((route) => {
		help_links[route] = (help_links[route] || []).filter(
			(item) =>
				!whitelabel.is_documentation_url(item.url) &&
				!whitelabel.is_standard_support_url(item.url) &&
				!whitelabel.is_standard_support_label(item.label)
		);
	});
};

whitelabel.sanitize_node = function (root) {
	if (!root) {
		return;
	}

	const process_node = (node) => {
		if (node.nodeType === Node.TEXT_NODE) {
			const parent = node.parentElement;
			if (
				!parent ||
				parent.closest("script, style, code, pre, textarea, [contenteditable='true']")
			) {
				return;
			}
			if (whitelabel.is_hidden_profile_label(node.nodeValue)) {
				whitelabel.hide_standard_support_item(parent);
			}
			node.nodeValue = whitelabel.replace_brand_terms(node.nodeValue);
			return;
		}

		if (node.nodeType !== Node.ELEMENT_NODE) {
			return;
		}

		if (node.matches("a[href]") && whitelabel.is_documentation_url(node.href)) {
			node.classList.add("whitelabel-hidden-documentation-link");
			node.setAttribute("aria-hidden", "true");
			node.setAttribute("tabindex", "-1");
		}
		if (node.matches("a[href]") && whitelabel.is_standard_support_url(node.href)) {
			whitelabel.hide_standard_support_item(node);
		}

		["title", "aria-label", "alt", "placeholder"].forEach((attribute) => {
			if (node.hasAttribute(attribute)) {
				node.setAttribute(
					attribute,
					whitelabel.replace_brand_terms(node.getAttribute(attribute))
				);
			}
		});
	};

	process_node(root);
	const walker = document.createTreeWalker(
		root,
		NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT
	);
	while (walker.nextNode()) {
		process_node(walker.currentNode);
	}
};

whitelabel.setup_dynamic_sanitizer = function () {
	if (whitelabel.branding_observer || !document.body) {
		return;
	}

	whitelabel.sanitize_node(document.body);
	whitelabel.branding_observer = new MutationObserver((mutations) => {
		mutations.forEach((mutation) => {
			mutation.addedNodes.forEach((node) => whitelabel.sanitize_node(node));
		});
	});
	whitelabel.branding_observer.observe(document.body, {
		childList: true,
		subtree: true,
	});
};

whitelabel.apply_branding = function () {
	const settings = frappe.boot?.whitelabel_setting;
	if (!settings) {
		return;
	}

	whitelabel.filter_help_links();
	whitelabel.patch_menu_renderer();
	whitelabel.patch_sidebar_help_menu();
	frappe.boot.changelog_feed = [];
	frappe.boot.has_app_updates = false;
	frappe.boot.onboarding_tours = [];
	if (frappe.boot.sysdefaults) {
		frappe.boot.sysdefaults.disable_change_log_notification = 1;
		frappe.boot.sysdefaults.disable_system_update_notification = 1;
		frappe.boot.sysdefaults.enable_onboarding = 0;
	}

	const help_dropdown = frappe.boot?.navbar_settings?.help_dropdown;
	if (help_dropdown) {
		frappe.boot.navbar_settings.help_dropdown =
			whitelabel.filter_sidebar_help_items(help_dropdown);
	}

	const root = document.documentElement;
	const background = settings.navbar_background_color;

	if (background && window.CSS?.supports("color", background)) {
		root.style.setProperty("--whitelabel-sidebar-bg", background);
	} else {
		root.style.removeProperty("--whitelabel-sidebar-bg");
	}

	const set_pixel_variable = (name, value) => {
		const pixels = Number.parseInt(value, 10);
		if (Number.isFinite(pixels) && pixels >= 8 && pixels <= 200) {
			root.style.setProperty(name, `${pixels}px`);
		} else {
			root.style.removeProperty(name);
		}
	};

	set_pixel_variable("--whitelabel-logo-width", settings.logo_width);
	set_pixel_variable("--whitelabel-logo-height", settings.logo_height);

	const hide_help = !Number(settings.show_help_menu);
	document.body?.classList.toggle("whitelabel-hide-help", hide_help);

	document.querySelectorAll(".frappe-menu .dropdown-menu-item").forEach((item) => {
		const title = item.querySelector(".menu-item-title");
		if (title?.textContent.trim() === __("Help")) {
			item.classList.toggle("whitelabel-help-menu-item", hide_help);
		}
		if (whitelabel.is_hidden_profile_label(title?.textContent)) {
			whitelabel.hide_standard_support_item(item);
		}
	});
};

whitelabel.patch_menu_renderer();
whitelabel.patch_sidebar_help_menu();

frappe.ready(() => {
	whitelabel.apply_branding();
	whitelabel.setup_dynamic_sanitizer();

	$(document).on("page-change toolbar_setup", () => {
		window.setTimeout(whitelabel.apply_branding, 0);
	});
});
