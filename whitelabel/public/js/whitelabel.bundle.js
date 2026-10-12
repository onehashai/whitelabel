frappe.provide("whitelabel");

whitelabel.documentation_hosts = new Set([
  "docs.erpnext.com",
  "docs.frappe.io",
  "docs.frappeframework.com",
  "frappeframework.com",
  "www.frappeframework.com",
]);

whitelabel.upstream_hosts = new Set([
  ...whitelabel.documentation_hosts,
  "discuss.frappe.io",
  "school.frappe.io",
  "support.frappe.io",
  "frappe.io",
  "www.frappe.io",
  "frappecloud.com",
  "www.frappecloud.com",
]);

whitelabel.get_config = () => frappe.boot?.whitelabel_setting;

whitelabel.parse_url = function (value) {
  if (!value) return null;
  try {
    return new URL(value, window.location.origin);
  } catch (error) {
    return null;
  }
};

whitelabel.is_documentation_url = function (value) {
  const url = whitelabel.parse_url(value);
  if (!url) return false;
  const host = url.hostname.toLowerCase();
  const path = url.pathname.toLowerCase();
  return (
    whitelabel.documentation_hosts.has(host) ||
    host.endsWith(".docs.frappe.io") ||
    host.endsWith(".docs.erpnext.com") ||
    (["erpnext.com", "www.erpnext.com"].includes(host) &&
      path.startsWith("/docs"))
  );
};

whitelabel.is_support_url = function (value) {
  const url = whitelabel.parse_url(value);
  if (!url) return false;
  const host = url.hostname.toLowerCase();
  const path = url.pathname.toLowerCase();
  return (
    host === "support.frappe.io" ||
    (["frappe.io", "www.frappe.io"].includes(host) &&
      (path.startsWith("/helpdesk") || path.startsWith("/support"))) ||
    (["frappecloud.com", "www.frappecloud.com"].includes(host) &&
      path.startsWith("/support"))
  );
};

whitelabel.is_upstream_url = function (value) {
  const url = whitelabel.parse_url(value);
  if (!url) return false;
  const host = url.hostname.toLowerCase();
  const path = url.pathname.toLowerCase();
  return (
    whitelabel.is_documentation_url(value) ||
    whitelabel.is_support_url(value) ||
    whitelabel.upstream_hosts.has(host) ||
    (host === "github.com" &&
      (path.startsWith("/frappe/") || path.startsWith("/frappehq/")))
  );
};

whitelabel.is_upstream_menu_item = function (item) {
  if (!item) return false;
  const label = String(item.label || item.item_label || "").trim();
  const url = item.url || item.route || item.href || "";
  const action = item.action || "";
  return (
    /^(about|frappe support)$/i.test(label) ||
    /show_about/.test(action) ||
    whitelabel.is_upstream_url(url)
  );
};

whitelabel.filter_menu_items = function (items) {
  const config = whitelabel.get_config();
  return (items || [])
    .filter((item) => {
      if (whitelabel.is_upstream_menu_item(item)) return false;
      if (
        !config?.show_help_menu &&
        (item?.name === "help" || item?.label === "Help")
      ) {
        return false;
      }
      return true;
    })
    .map((item) => {
      if (!item?.items) return item;
      return { ...item, items: whitelabel.filter_menu_items(item.items) };
    });
};

whitelabel.patch_menu_renderer = function () {
  const Menu = frappe.ui?.menu;
  if (!Menu || Menu.prototype.__whitelabel_patched) return;
  const make = Menu.prototype.make;
  if (typeof make !== "function") return;

  Menu.prototype.make = function () {
    this.menu_items = whitelabel.filter_menu_items(this.menu_items);
    return make.call(this);
  };
  Menu.prototype.__whitelabel_patched = true;
};

whitelabel.patch_sidebar_help = function () {
  const SidebarHeader = frappe.ui?.SidebarHeader;
  if (!SidebarHeader || SidebarHeader.prototype.__whitelabel_patched) return;
  const get_help_siblings = SidebarHeader.prototype.get_help_siblings;
  if (typeof get_help_siblings !== "function") return;

  SidebarHeader.prototype.get_help_siblings = function () {
    if (!whitelabel.get_config()?.show_help_menu) return [];
    return whitelabel.filter_menu_items(get_help_siblings.call(this));
  };
  SidebarHeader.prototype.__whitelabel_patched = true;
};

whitelabel.filter_route_help = function () {
  if (!frappe.help?.help_links) return;
  Object.keys(frappe.help.help_links).forEach((route) => {
    frappe.help.help_links[route] = (
      frappe.help.help_links[route] || []
    ).filter((item) => !whitelabel.is_upstream_url(item.url));
  });
};

whitelabel.install_known_translations = function () {
  const config = whitelabel.get_config();
  if (!config || !frappe._messages) return;
  Object.assign(frappe._messages, {
    "Frappe Light": `${config.brand_name} Light`,
    "Welcome to Frappe!": `Welcome to ${config.brand_name}!`,
    "Starting Frappe ...": `Starting ${config.brand_name} ...`,
    "ERPNext Settings": `${config.desk_title} Settings`,
    "ERPNext User ID": `${config.brand_name} User ID`,
    "Frappe page builder using components": `${config.brand_name} page builder using components`,
    Whitelabel: `${config.brand_name} Settings`,
    "Whitelabel Setting": "Brand Settings",
    "Whitelabel App Name": "Application Name",
    "Fiscal Year (requires ERPNext to be installed)": "Fiscal Year",
    "Company Abbreviation (requires ERPNext to be installed)":
      "Company Abbreviation",
  });
};

whitelabel.apply_branding = function () {
  const config = whitelabel.get_config();
  if (!config) return;

  whitelabel.patch_menu_renderer();
  whitelabel.patch_sidebar_help();
  whitelabel.filter_route_help();
  whitelabel.install_known_translations();

  frappe.boot.changelog_feed = [];
  frappe.boot.has_app_updates = false;
  frappe.boot.marketplace_apps = [];
  frappe.boot.onboarding_tours = [];
  if (frappe.boot.sysdefaults) {
    frappe.boot.sysdefaults.disable_change_log_notification = 1;
    frappe.boot.sysdefaults.disable_system_update_notification = 1;
    frappe.boot.sysdefaults.disable_product_suggestion = 1;
    frappe.boot.sysdefaults.enable_onboarding = 0;
  }

  const root = document.documentElement;
  const background = config.sidebar_background_color;
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
  set_pixel_variable("--whitelabel-logo-width", config.logo_width);
  set_pixel_variable("--whitelabel-logo-height", config.logo_height);
};

whitelabel.patch_menu_renderer();
whitelabel.patch_sidebar_help();

whitelabel.initialize = function () {
  whitelabel.apply_branding();
  $(document).on("page-change toolbar_setup", whitelabel.apply_branding);
};

if (document.readyState === "loading") {
  $(whitelabel.initialize);
} else {
  whitelabel.initialize();
}
