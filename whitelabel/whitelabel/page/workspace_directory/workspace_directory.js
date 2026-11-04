frappe.pages["workspace-directory"].on_page_load = function (wrapper) {
  wrapper.whitelabel_page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Workspaces"),
    single_column: true,
  });
};

frappe.pages["workspace-directory"].on_page_show = async function (wrapper) {
  const page = wrapper.whitelabel_page;
  const navigation = whitelabel.navigation;
  const context = await navigation.refresh();
  const body = $(page.body).empty().addClass("whitelabel-workspace-directory");
  page.clear_menu();
  if (!context?.enabled) {
    $("<p class='text-muted'>")
      .text(__("Workspace Navigation is not enabled on this site."))
      .appendTo(body);
    return;
  }
  const group =
    frappe.route_options?.group ||
    new URLSearchParams(window.location.search).get("group");
  page.set_title(
    group
      ? context.groups.find((g) => g.name === group)?.title || __("Workspaces")
      : __("Workspaces")
  );
  navigation.render_list(body, context, { group });
  if (context.can_create_workspace) {
    page.add_menu_item(__("New Workspace"), () =>
      frappe.new_doc("Workspace", {
        public: 0,
        for_user: frappe.session.user,
        content: "[]",
      })
    );
  }
  if (group)
    page.add_menu_item(__("All Workspaces"), () =>
      navigation.open(context.directory_route)
    );
  if (context.can_manage) {
    page.add_menu_item(__("Manage Workspaces"), () =>
      frappe.set_route("List", "Workspace")
    );
    page.add_menu_item(__("Manage Workspace Groups"), () =>
      frappe.set_route("List", "Whitelabel Workspace Group")
    );
  }
  if (context.can_manage_settings) {
    page.add_menu_item(__("Manage Navigation Profiles"), () =>
      frappe.set_route("List", "Whitelabel Navigation Profile")
    );
    page.add_menu_item(__("Manage Workspace Navigation"), () =>
      frappe.set_route("Form", "Whitelabel Setting")
    );
    page.add_menu_item(__("Manage Workspace Rules"), () =>
      frappe.set_route("List", "Whitelabel Workspace Rule")
    );
  }
};
