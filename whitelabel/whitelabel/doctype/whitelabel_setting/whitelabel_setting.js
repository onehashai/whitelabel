// Copyright (c) 2021, Bhavesh Maheshwari and contributors
// For license information, please see license.txt

frappe.ui.form.on("Whitelabel Setting", {
	after_save() {
		frappe.ui.toolbar.clear_cache();
	},
});
