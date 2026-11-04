// Copyright (c) 2021, Bhavesh Maheshwari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Whitelabel Setting", {
	refresh(frm) {
		frm.add_custom_button(__("Protected Workspaces"), () =>
			frappe.set_route("List", "Workspace", { custom_whitelabel_protect_migration: 1 })
		);
		const wrapper = frm.fields_dict.navigation_configuration?.$wrapper;
		if (!wrapper) return;
		wrapper.empty();
		[
			[__("Navigation Profiles"), "List", "Whitelabel Navigation Profile"],
			[__("Workspace Rules"), "List", "Whitelabel Workspace Rule"],
			[__("Workspace Groups"), "List", "Whitelabel Workspace Group"],
			[__("Workspaces"), "List", "Workspace"],
		].forEach(([label, ...route]) => {
			$("<button type='button' class='btn btn-default btn-sm mr-2 mb-2'>")
				.text(label).on("click", () => frappe.set_route(...route)).appendTo(wrapper);
		});
	},
	after_save() {
		frappe.ui.toolbar.clear_cache();
	},
});
