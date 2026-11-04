frappe.ui.form.on("Whitelabel Navigation Profile", {
  setup(frm) {
    const names = () =>
      (frm.doc.workspaces || []).map((row) => row.workspace).filter(Boolean);
    frm.set_query("default_workspace", () => ({
      filters: { public: 1, is_hidden: 0, type: "Workspace" },
    }));
    frm.set_query("workspace", "workspaces", () => ({
      filters: { public: 1, is_hidden: 0, type: "Workspace" },
    }));
    frm.set_query("parent_workspace", "workspaces", () => ({
      filters: { name: ["in", names()] },
    }));
    frm.set_query("user", "assignments", () => ({
      filters: { user_type: "System User", enabled: 1 },
    }));
  },
  async default_workspace(frm) {
    const workspace = frm.doc.default_workspace;
    if (
      !workspace ||
      (frm.doc.workspaces || []).some((row) => row.workspace === workspace)
    )
      return;
    const empty = (frm.doc.workspaces || []).find(
      (row) =>
        !row.workspace && !row.parent_workspace && !row.label && !row.icon
    );
    if (empty) {
      await frappe.model.set_value(
        empty.doctype,
        empty.name,
        "workspace",
        workspace
      );
    } else {
      frm.add_child("workspaces", { workspace });
    }
    frm.refresh_field("workspaces");
  },
});
