(() => {
	const BRAND_NAME = "OneHash";
	const BRAND_PATTERN = /Frappe Framework|ERPNext|Frappe/gi;
	const SKIPPED_PARENTS =
		"script, style, code, pre, textarea, [contenteditable='true']";

	const is_standard_brand_url = (href) => {
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
				host === "support.frappe.io" ||
				((host === "frappe.io" || host === "www.frappe.io") &&
					(path.startsWith("/erpnext") || path.startsWith("/helpdesk"))) ||
				((host === "erpnext.com" || host === "www.erpnext.com") &&
					path.startsWith("/docs")) ||
				((host === "frappecloud.com" || host === "www.frappecloud.com") &&
					path.startsWith("/support"))
			);
		} catch (error) {
			return false;
		}
	};

	const replace_brand_terms = (value) =>
		typeof value === "string"
			? value.replace(BRAND_PATTERN, BRAND_NAME)
			: value;

	const sanitize_node = (root) => {
		if (!root) {
			return;
		}

		const process_node = (node) => {
			if (node.nodeType === Node.TEXT_NODE) {
				const parent = node.parentElement;
				if (!parent || parent.closest(SKIPPED_PARENTS)) {
					return;
				}
				node.nodeValue = replace_brand_terms(node.nodeValue);
				return;
			}

			if (node.nodeType !== Node.ELEMENT_NODE) {
				return;
			}

			if (node.matches("a[href]") && is_standard_brand_url(node.href)) {
				node.removeAttribute("href");
				node.setAttribute("aria-disabled", "true");
			}

			["title", "aria-label", "alt", "placeholder"].forEach((attribute) => {
				if (node.hasAttribute(attribute)) {
					node.setAttribute(
						attribute,
						replace_brand_terms(node.getAttribute(attribute))
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

	const start = () => {
		sanitize_node(document.body);
		new MutationObserver((mutations) => {
			mutations.forEach((mutation) => {
				mutation.addedNodes.forEach((node) => sanitize_node(node));
			});
		}).observe(document.body, { childList: true, subtree: true });
	};

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", start, { once: true });
	} else {
		start();
	}
})();
