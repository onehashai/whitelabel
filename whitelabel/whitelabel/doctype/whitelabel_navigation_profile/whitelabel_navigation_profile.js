frappe.ui.form.on("Whitelabel Navigation Profile", {
  setup(frm) {
    const names = () =>
      (frm.doc.workspaces || []).map((row) => row.workspace).filter(Boolean);
    frm.set_query("default_workspace", () => ({
      filters: { name: ["in", names()] },
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
});
