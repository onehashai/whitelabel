frappe.ui.form.on("Whitelabel Workspace Group", {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__("Open Group"), () => {
      frappe.set_route("workspace-directory", { group: frm.doc.name });
    });
    if (frappe.user.has_role("System Manager")) {
      frm.add_custom_button(__("Publish Desktop Shortcut"), () => {
        frappe.call({
          method:
            "whitelabel.whitelabel.doctype.whitelabel_workspace_group.whitelabel_workspace_group.publish_shortcut",
          args: { group: frm.doc.name },
          freeze: true,
          callback: () =>
            frappe.msgprint(
              __("Desktop shortcut published. Reload Desk to see it.")
            ),
        });
      });
    }
  },
});
