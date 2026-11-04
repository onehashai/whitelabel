frappe.provide("whitelabel.classic");

(() => {
  const classic = whitelabel.classic;
  const context = () => frappe.boot?.whitelabel_navigation;
  const enabled = () => !!context()?.classic;
  const storage_key = () => `whitelabel-tree:${frappe.session.user}`;

  classic.refresh_workspaces = async () => {
    const workspaces = await frappe.xcall(
      "frappe.desk.desktop.get_workspaces",
      {},
      "GET"
    );
    frappe.boot.workspaces = workspaces;
    frappe.app.setup_workspaces();
    if (frappe.workspace) {
      frappe.workspace.workspaces = workspaces.pages;
      frappe.workspace.cached_pages = $.extend(true, {}, workspaces);
      frappe.workspace.pages = {};
      frappe.workspace._page = null;
      frappe.workspace.setup();
    }
    return whitelabel.navigation.refresh();
  };

  classic.new_workspace = () => {
    const config = context();
    const private_items = config.workspaces.filter((item) => item.private);
    const dialog = new frappe.ui.Dialog({
      title: __("New Workspace"),
      fields: [
        { fieldname: "title", fieldtype: "Data", label: __("Title"), reqd: 1 },
        {
          fieldname: "parent",
          fieldtype: "Select",
          label: __("Parent Workspace"),
          options: [
            { label: "", value: "" },
            ...private_items.map((item) => ({
              label: item.title,
              value: item.name,
            })),
          ],
        },
      ],
      primary_action_label: __("Create"),
      primary_action: async (values) => {
        dialog.get_primary_btn().prop("disabled", true);
        try {
          const title = strip_html(values.title).trim();
          if (!title) {
            frappe.msgprint(__("Enter a workspace title."));
            return;
          }
          const doc = await frappe.xcall("frappe.client.insert", {
            doc: {
              doctype: "Workspace",
              label: `${title}-${frappe.session.user}`,
              title,
              type: "Workspace",
              public: 0,
              for_user: frappe.session.user,
              module: config.workspaces[0]?.module || null,
              parent_page: values.parent || null,
              content: JSON.stringify([
                {
                  id: frappe.utils.get_random(10),
                  type: "header",
                  data: { text: title, col: 12 },
                },
              ]),
            },
          });
          await classic.refresh_workspaces();
          dialog.hide();
          whitelabel.navigation.open(
            `/desk/private/${frappe.router.slug(doc.name)}`
          );
        } finally {
          dialog.get_primary_btn().prop("disabled", false);
        }
      },
    });
    dialog.show();
  };

  classic.update = () => {
    document.body.classList.toggle("whitelabel-classic", enabled());
    const sidebar = frappe.app?.sidebar;
    if (!sidebar?.wrapper) return;
    if (enabled()) {
      sidebar.setup();
    } else if (sidebar.classic_active) {
      sidebar.classic_active = false;
      sidebar.classic_signature = null;
      sidebar.set_workspace_sidebar(frappe.router);
    }
  };

  classic.render = (sidebar) => {
    const config = context();
    const signature = JSON.stringify([
      config.tree,
      config.home_route,
      config.can_create_workspace,
      config.allow_personal_workspaces,
      config.can_manage_settings,
    ]);
    if (sidebar.classic_signature === signature) {
      classic.select(sidebar);
      return;
    }
    sidebar.classic_signature = signature;
    const container = sidebar.$items_container
      .empty()
      .addClass("whitelabel-classic-tree");
    const navigation = whitelabel.navigation;
    const controls = $("<div class='whitelabel-tree-controls'>").appendTo(
      container
    );
    $(
      "<button type='button' class='btn btn-default btn-sm whitelabel-tree-home'>"
    )
      .text(__("Home"))
      .on("click", navigation.home)
      .appendTo(controls);
    if (config.can_create_workspace && config.allow_personal_workspaces) {
      $(
        "<button type='button' class='btn btn-default btn-sm whitelabel-tree-new'>"
      )
        .text(__("New Workspace"))
        .appendTo(controls)
        .on("click", () => {
          if (frappe.is_mobile()) sidebar.close();
          classic.new_workspace();
        });
    }
    const search = $(
      "<input type='search' class='form-control input-sm whitelabel-tree-search'>"
    )
      .attr({
        placeholder: __("Find a workspace…"),
        "aria-label": __("Find a workspace"),
      })
      .appendTo(container);
    const tree = $("<div role='tree'>")
      .attr("aria-label", __("Workspaces"))
      .appendTo(container);
    sidebar.classic_nodes = new Map();
    let expanded;
    try {
      expanded = JSON.parse(localStorage.getItem(storage_key()) || "{}");
    } catch {
      expanded = {};
    }
    const items = config.tree || [];
    const children = new Map();
    for (const item of items) {
      const key = item.parent || (item.private ? "__personal" : "__public");
      if (!children.has(key)) children.set(key, []);
      children.get(key).push(item);
    }
    const persist = () =>
      localStorage.setItem(storage_key(), JSON.stringify(expanded));
    const render_node = (item, parent) => {
      const wrapper = $("<div class='whitelabel-tree-node' role='treeitem'>")
        .attr("data-workspace", item.name)
        .appendTo(parent);
      const row = $(
        "<div class='whitelabel-tree-row standard-sidebar-item'>"
      ).appendTo(wrapper);
      const link = $("<a class='whitelabel-tree-link item-anchor'>")
        .attr({ href: item.route, title: __(item.label) })
        .appendTo(row);
      $("<span class='sidebar-item-icon'>")
        .html(frappe.utils.icon(item.icon || "folder", "sm"))
        .appendTo(link);
      $("<span class='sidebar-item-label'>")
        .text(__(item.label))
        .appendTo(link);
      link.on("click", (event) => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
          return;
        event.preventDefault();
        event.stopPropagation();
        navigation.open(item.route);
      });
      const nested = $(
        "<div class='whitelabel-tree-children' role='group'>"
      ).appendTo(wrapper);
      const descendants = children.get(item.name) || [];
      const set_open = (open, remember = false) => {
        if (!descendants.length) return;
        nested.toggleClass("hidden", !open);
        wrapper.attr("aria-expanded", String(open));
        toggle
          .attr("aria-expanded", String(open))
          .html(
            frappe.utils.icon(open ? "chevron-down" : "chevron-right", "xs")
          );
        if (remember) {
          expanded[item.name] = open;
          persist();
        }
      };
      let toggle;
      if (descendants.length) {
        toggle = $(
          "<button type='button' class='btn-reset whitelabel-tree-toggle'>"
        )
          .attr({
            "aria-label": __("Expand or collapse {0}", [__(item.label)]),
          })
          .appendTo(row)
          .on("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            set_open(wrapper.attr("aria-expanded") !== "true", true);
          });
        descendants.forEach((child) => render_node(child, nested));
        set_open(expanded[item.name] === true);
      } else {
        nested.remove();
      }
      sidebar.classic_nodes.set(item.name, {
        item,
        wrapper,
        row,
        link,
        nested,
        set_open,
      });
      link.on("keydown", (event) => {
        const links = container.find(".whitelabel-tree-link:visible").toArray();
        const index = links.indexOf(link[0]);
        if (event.key === "ArrowDown") {
          event.preventDefault();
          links[index + 1]?.focus();
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          links[index - 1]?.focus();
        }
        if (event.key === "ArrowRight" && descendants.length) {
          event.preventDefault();
          set_open(true, true);
        }
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          if (wrapper.attr("aria-expanded") === "true") set_open(false, true);
          else sidebar.classic_nodes.get(item.parent)?.link.trigger("focus");
        }
      });
    };
    for (const [key, title] of [
      ["__personal", __("Personal")],
      ["__public", __("Workspaces")],
    ]) {
      const roots = children.get(key) || [];
      if (!roots.length) continue;
      const section = $("<section class='whitelabel-tree-section'>").appendTo(
        tree
      );
      $("<div class='whitelabel-tree-heading'>").text(title).appendTo(section);
      roots.forEach((item) => render_node(item, section));
    }
    if (!items.length) {
      $("<p class='text-muted whitelabel-tree-empty'>")
        .text(__("No workspaces assigned."))
        .appendTo(tree);
    }
    if (config.can_manage_settings) {
      $(
        "<button type='button' class='btn btn-default btn-sm whitelabel-tree-manage'>"
      )
        .text(__("Organise Workspaces"))
        .appendTo(container)
        .on("click", () => {
          if (frappe.is_mobile()) sidebar.close();
          frappe.set_route("List", "Whitelabel Navigation Profile");
        });
    }
    search.on("input", () => {
      const query = search.val().trim().toLocaleLowerCase();
      const matches = new Set();
      for (const item of items) {
        if (
          !query ||
          `${item.label} ${item.name}`.toLocaleLowerCase().includes(query)
        ) {
          let name = item.name;
          while (name && !matches.has(name)) {
            matches.add(name);
            name = sidebar.classic_nodes.get(name)?.item.parent;
          }
        }
      }
      for (const [name, node] of sidebar.classic_nodes) {
        node.wrapper.toggleClass("hidden", !matches.has(name));
        node.set_open(query ? true : expanded[name] === true);
      }
      tree.find("section").each((_, section) => {
        $(section).toggleClass(
          "hidden",
          !$(section).children(".whitelabel-tree-node:not(.hidden)").length
        );
      });
      if (!query) classic.select(sidebar);
    });
    classic.select(sidebar);
  };

  classic.select = (sidebar) => {
    const route = frappe.get_route?.() || [];
    if (route[0] === "Workspaces") sidebar.classic_selected = route.at(-1);
    for (const [name, node] of sidebar.classic_nodes || []) {
      const active = name === sidebar.classic_selected;
      node.row.toggleClass("active-sidebar", active);
      node.link.attr("aria-current", active ? "page" : null);
      node.wrapper.attr("aria-selected", String(active));
      if (active) {
        let parent = node.item.parent;
        while (parent) {
          const ancestor = sidebar.classic_nodes.get(parent);
          ancestor?.set_open(true);
          parent = ancestor?.item.parent;
        }
      }
    }
  };

  const NativeSidebar = frappe.ui.Sidebar;
  frappe.ui.Sidebar = class ClassicWorkspaceSidebar extends NativeSidebar {
    setup(title) {
      if (!enabled()) {
        this.$items_container?.removeClass("whitelabel-classic-tree");
        return super.setup(title);
      }
      document.body.classList.add("whitelabel-classic");
      if (!this.classic_active) {
        this.classic_active = true;
        this.sidebar_title = "Workspaces";
        this.workspace_title = "__whitelabel_classic";
        this.workspace_sidebar_items = [];
        this.sidebar_data = { items: [], label: "Workspaces" };
        this.header_subtitle = frappe.boot.whitelabel_setting?.brand_name || "";
        this.add_standard_items();
        this.sidebar_header = new frappe.ui.SidebarHeader(this);
        this.$sidebar.attr("data-title", "Workspaces");
        this.load_sidebar_state();
        this.expand_sidebar();
      }
      classic.render(this);
    }
    set_workspace_sidebar(router) {
      if (enabled()) return this.setup();
      return super.set_workspace_sidebar(router);
    }
    show_sidebar_for_module(module) {
      if (enabled()) return this.setup();
      return super.show_sidebar_for_module(module);
    }
    set_active_workspace_item() {
      if (enabled()) return classic.select(this);
      return super.set_active_workspace_item();
    }
    store_last_show_sidebar_for_item() {
      if (!enabled()) return super.store_last_show_sidebar_for_item();
    }
  };
})();
