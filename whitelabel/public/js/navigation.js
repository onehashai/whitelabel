frappe.provide("whitelabel.navigation");

(() => {
  const navigation = whitelabel.navigation;
  const config = () => frappe.boot?.whitelabel_navigation;
  const desk_url = (route) => {
    const url = new URL(route, window.location.origin);
    return url.origin === window.location.origin &&
      url.pathname.startsWith("/desk/")
      ? url
      : null;
  };
  const home_url = () => config()?.enabled && desk_url(config().home_route);

  navigation.refresh = async () => {
    if (!navigation.refreshing) {
      navigation.refreshing = frappe
        .xcall("whitelabel.navigation.get_context")
        .then((context) => {
          frappe.boot.whitelabel_navigation = context;
          navigation.update();
          return context;
        })
        .finally(() => {
          navigation.refreshing = null;
        });
    }
    return navigation.refreshing;
  };

  navigation.open = (route) => {
    const url = desk_url(route);
    if (!url) return;
    if (frappe.is_mobile()) frappe.app.sidebar?.close();
    const target = url.pathname + url.search + url.hash;
    if (
      window.location.pathname +
        window.location.search +
        window.location.hash ===
      target
    )
      return;
    // push_state takes a URL. set_route parses a query as part of the page name,
    // and some v16 releases discard its separate query_params argument.
    frappe.route_options = Object.fromEntries(url.searchParams);
    return frappe.router.push_state(target);
  };

  navigation.home = () => {
    if (navigation.saving_home) return;
    const context = config();
    if (context?.enabled) navigation.open(context.home_route);
  };

  navigation.sections = (context, groupName) => {
    const byName = new Map(
      context.workspaces.map((workspace) => [workspace.name, workspace])
    );
    const used = new Set();
    const sections = [];
    (context.groups || []).forEach((group) => {
      if (groupName && group.name !== groupName) return;
      const items = group.items.map((item) => {
        used.add(item.name);
        return { ...byName.get(item.name), route: item.route };
      });
      sections.push({ title: group.title, items });
    });
    if (!groupName) {
      const modules = new Map();
      context.workspaces.forEach((workspace) => {
        if (used.has(workspace.name)) return;
        const title = workspace.private
          ? __("My Workspaces")
          : workspace.module || __("Other Workspaces");
        if (!modules.has(title)) modules.set(title, []);
        modules.get(title).push(workspace);
      });
      [...modules]
        .sort(([a], [b]) => a.localeCompare(b))
        .forEach(([title, items]) => {
          sections.push({ title, items });
        });
    }
    return sections;
  };

  navigation.render_list = (
    wrapper,
    context,
    { group, onSelect, dialog } = {}
  ) => {
    wrapper.empty();
    const search = $("<input type='search' class='form-control mb-4'>")
      .attr({
        placeholder: __("Find a workspace…"),
        "aria-label": __("Find a workspace"),
      })
      .appendTo(wrapper);
    const list = $("<div class='whitelabel-workspace-list'>").appendTo(wrapper);
    const current = frappe.get_route?.() || [];
    const currentName = current[0] === "Workspaces" ? current.at(-1) : null;
    const render = () => {
      list.empty();
      const query = search.val().trim().toLocaleLowerCase();
      let count = 0;
      navigation.sections(context, group).forEach((section) => {
        const items = section.items.filter((item) =>
          `${item.title} ${item.name} ${section.title}`
            .toLocaleLowerCase()
            .includes(query)
        );
        if (!items.length) return;
        $("<h3 class='whitelabel-workspace-group'>")
          .text(__(section.title))
          .appendTo(list);
        items.forEach((item) => {
          count++;
          const row = $("<div class='whitelabel-workspace-row'>").appendTo(
            list
          );
          const link = $("<a class='whitelabel-workspace-link'>")
            .attr("href", item.route)
            .text(__(item.title || item.name))
            .appendTo(row);
          if (currentName === item.name) link.attr("aria-current", "page");
          link.on("click", (event) => {
            if (
              event.ctrlKey ||
              event.metaKey ||
              event.shiftKey ||
              event.altKey
            )
              return;
            event.preventDefault();
            event.stopPropagation();
            dialog?.hide();
            navigation.open(item.route);
            onSelect?.(item);
          });
          if (context.home?.name === item.name) {
            $("<span class='text-muted small'>").text(__("Home")).appendTo(row);
          } else if (context.allow_user_home) {
            $("<button type='button' class='btn btn-xs btn-default'>")
              .text(__("Set as my Home"))
              .attr(
                "aria-label",
                __("Set {0} as my Home", [item.title || item.name])
              )
              .appendTo(row)
              .on("click", async (event) => {
                if (navigation.saving_home) return;
                navigation.saving_home = true;
                const button = $(event.currentTarget).prop("disabled", true);
                try {
                  context = await frappe.xcall(
                    "whitelabel.navigation.set_my_home",
                    { workspace: item.name }
                  );
                  frappe.boot.whitelabel_navigation = context;
                  navigation.update();
                  // Notify other tabs without putting a request on the Home click.
                  localStorage.setItem(
                    navigation.storage_key(),
                    String(Date.now())
                  );
                  render();
                  frappe.show_alert({
                    message: __("Home workspace updated"),
                    indicator: "green",
                  });
                } finally {
                  navigation.saving_home = false;
                  button.prop("disabled", false);
                }
              });
          }
        });
      });
      if (!count) {
        $("<p class='text-muted'>")
          .text(__("No available workspaces match your selection."))
          .appendTo(list);
      }
    };
    search.on("input", render);
    render();
    return search;
  };

  navigation.show_switcher = async () => {
    if (frappe.is_mobile()) frappe.app.sidebar?.close();
    const context = await navigation.refresh();
    if (!context?.enabled) return;
    if (navigation.dialog) navigation.dialog.hide();
    const dialog = new frappe.ui.Dialog({
      title: __("Workspaces"),
      animate: false,
      fields: [{ fieldname: "workspaces", fieldtype: "HTML" }],
      secondary_action_label: __("All Workspaces"),
      secondary_action: () => {
        dialog.hide();
        navigation.open(context.directory_route);
      },
    });
    navigation.dialog = dialog;
    const search = navigation.render_list(
      dialog.fields_dict.workspaces.$wrapper,
      context,
      { dialog }
    );
    dialog.show();
    search.trigger("focus");
  };

  navigation.sidebar_menu_items = (items) => {
    const context = config();
    if (!context?.enabled) return items;
    return [
      {
        name: "whitelabel-home",
        label: __("Home"),
        icon: "home",
        onClick: navigation.home,
      },
      {
        name: "whitelabel-workspaces",
        label: __("Workspaces"),
        icon: "wallpaper",
        onClick: navigation.show_switcher,
      },
      {
        name: "whitelabel-directory",
        label: __("All Workspaces"),
        icon: "list",
        onClick: () => navigation.open(config().directory_route),
      },
      {
        name: "whitelabel-desktop",
        label: __("All Apps"),
        icon: "grid",
        onClick: () => navigation.open(config().desktop_route),
      },
      ...items.filter((item) => !["desktop", "workspaces"].includes(item.name)),
    ];
  };

  navigation.update = () => {
    // Remove the former top bar without changing Frappe's native page layout.
    $("#whitelabel-navigation").remove();
    document.body.classList.remove("whitelabel-navigation-enabled");
    const url = home_url();
    $(".navbar-breadcrumbs li:first-child a")
      .attr("href", url ? url.pathname + url.search : "/desk")
      .off("click.whitelabel-home")
      .on("click.whitelabel-home", (event) => {
        if (
          !home_url() ||
          event.ctrlKey ||
          event.metaKey ||
          event.shiftKey ||
          event.altKey
        )
          return;
        event.preventDefault();
        event.stopPropagation();
        navigation.home();
      });
  };

  navigation.install_routing = () => {
    const router = frappe.router;
    if (!router || router.__whitelabel_home) return;
    router.__whitelabel_home = true;
    const push_state = router.push_state;
    router.push_state = function (path, ...args) {
      const url = home_url();
      // Resolve programmatic Home before Frappe writes history or renders Desk.
      if (url && path.replace(/\/$/, "") === "/desk") {
        frappe.route_options = Object.fromEntries(url.searchParams);
        return push_state.call(this, url.pathname + url.search);
      }
      return push_state.call(this, path, ...args);
    };
    const route = router.route;
    router.route = function (...args) {
      const url = home_url();
      // popstate and initial routing can enter without going through push_state.
      if (url && window.location.pathname.replace(/\/$/, "") === "/desk") {
        window.history.replaceState(
          window.history.state,
          "",
          url.pathname + url.search
        );
        frappe.route_options = Object.fromEntries(url.searchParams);
      }
      return route.apply(this, args);
    };
    const clear = frappe.breadcrumbs.clear;
    frappe.breadcrumbs.clear = function (...args) {
      const result = clear.apply(this, args);
      navigation.update();
      return result;
    };
  };

  navigation.storage_key = () => `whitelabel-home:${frappe.session.user}`;
  navigation.refresh_if_enabled = () => {
    if (config()?.enabled && !document.hidden) {
      navigation
        .refresh()
        .catch((error) =>
          console.warn("Workspace navigation refresh failed", error)
        );
    }
  };
  navigation.initialize = () => {
    if (navigation.initialized || !frappe.router || !frappe.boot) return;
    navigation.initialized = true;
    navigation.install_routing();
    $(document).on("page-change.whitelabel-navigation", navigation.update);
    $(window).on("focus.whitelabel-navigation", navigation.refresh_if_enabled);
    $(document).on(
      "visibilitychange.whitelabel-navigation",
      navigation.refresh_if_enabled
    );
    $(window).on("storage.whitelabel-navigation", (event) => {
      if (event.originalEvent.key === navigation.storage_key())
        navigation.refresh_if_enabled();
    });
    $(document).on("save.whitelabel-navigation", (event, doc) => {
      const affects_home =
        [
          "Whitelabel Setting",
          "Whitelabel Workspace Rule",
          "Whitelabel Workspace Group",
          "Workspace",
          "Workspace Sidebar",
          "Role",
          "Role Profile",
        ].includes(doc.doctype) ||
        (doc.doctype === "User" && doc.name === frappe.session.user);
      if (
        affects_home &&
        (config()?.enabled || doc.doctype === "Whitelabel Setting")
      ) {
        navigation
          .refresh()
          .then(() => {
            localStorage.setItem(navigation.storage_key(), String(Date.now()));
          })
          .catch((error) =>
            console.warn("Workspace navigation refresh failed", error)
          );
      }
    });
    navigation.update();
  };
  // Install before Application.startup makes its first routing decision.
  navigation.install_routing();
  $(document).on("app_ready.whitelabel-navigation", navigation.initialize);
  if (frappe.app) navigation.initialize();
})();
