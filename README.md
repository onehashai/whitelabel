# Whitelabel for Frappe and ERPNext v16

Whitelabel provides configurable, site-level branding for Frappe Framework and ERPNext v16. It changes user-facing product chrome without modifying either upstream repository or rewriting business content.

## What it brands

- Desk, login, website and splash logos
- Browser favicon and page/application name
- Desk app switcher, ERPNext desktop folder, sidebar title and colors
- Website and email footer settings
- OTP issuer name
- Help, About, upstream support and documentation menu entries
- Onboarding, product promotions, changelog and update notifications

The replacement name, optional Desk title, public logo, favicon, sidebar color, logo size, email footer address and neutral Help-menu visibility are managed in **Whitelabel Setting**. The default brand is OneHash.

Whitelabel intentionally does not rename Python packages, API routes, HTTP headers, database DocTypes, source code, license notices or browser developer-tool identifiers. User-authored website content, emails, print formats and business records are never text-rewritten.

The visible product surface is branded for guests, portal users, Desk users and System Managers. Internal identifiers can still be seen in browser developer tools, logs, API payloads and the legally required attribution page.

## Requirements

- Frappe Framework `>=16,<17`
- ERPNext `>=16,<17`
- Python 3.14
- Node.js 24 for asset builds

## Install

```sh
bench get-app git@github.com:sanskar-onehash/whitelabel.git --branch v-16
bench --site your-site.local install-app whitelabel
bench build --app whitelabel
bench --site your-site.local migrate
bench --site your-site.local clear-cache
```

When upgrading an existing v15 installation, switch the app to `v-16` after upgrading Frappe and ERPNext, then run the build and migrate commands above. Existing Whitelabel Setting values are retained. Obsolete v15 enforcement fields remain hidden for schema compatibility.

Logo and favicon attachments must be public because they are displayed before login. Logo height and width accept values from 8 through 200 pixels.

## Tests

```sh
bench --site test-site.local run-tests --app whitelabel
bench build --app whitelabel
bench --site test-site.local run-ui-tests whitelabel --headless --browser chrome --spec whitelabel/tests/ui_test_whitelabel.js
```

Run the integration and UI suites after every Frappe or ERPNext v16 update. The UI suite checks visible text and links on login and Desk surfaces for upstream product branding.

## Workspace navigation

Workspace navigation is optional and disabled by default. After upgrading, run `bench --site your-site.local migrate` and `bench build --app whitelabel`, then open **Whitelabel Setting → Navigation** and enable **Workspace Navigation**.

This feature applies only to enabled **System Users**. **Website Users** retain native portal/website routing, login destinations and Desk access restrictions, even if they have workspace-related roles or defaults. Guests never receive workspace metadata. Leave **Use Site Root for Desk Login and Home** off when `/` should serve a public website; enabling it sends guests at `/` to login and System Users to their home. Signed-in Website Users continue through native website routing.

When an account has been converted to a Website User, stale Desk workspace/app defaults are ignored for implicit login and root navigation. Its configured role/portal/website destination is retained, with `/portal` as the fallback. Explicit destinations retain native permission checks; Website Users never gain Desk access through this feature.

Configure a **Site Default Workspace**, with an optional shared sidebar containing that workspace. Use **Whitelabel Workspace Rule** records for Role or Role Profile defaults. Home selection is:

1. The user's existing **Default Workspace**.
2. A matching Role Profile rule.
3. A matching Role rule.
4. The site default.
5. The **All Workspaces** directory if no valid default exists.

Lower numeric priorities win within a rule type; equal priorities sort by rule name. Inaccessible, hidden, deleted and non-workspace targets are skipped. A matching rule's preferred sidebar also applies to a user override selecting the same workspace. These rules take precedence over native Role Home Page, Default App and website redirects **for the entry points managed by this feature**. Other apps and explicit document/report/workspace destinations remain available.

System Users get persistent **Home**, **Workspaces**, **All Workspaces** and **All Apps** controls throughout Desk. Home consistently resolves from `/desk`, an implicit successful login, and `/login` for an already signed-in System User. Root routing is separately configurable. Explicit login destinations and direct links are preserved; redirects to bare `/desk` resolve Home. **All Apps** opens `/desk/desktop` explicitly, bypassing Home routing. Setup Wizard behavior is preserved.

Switching workspaces does not change the default. When **Allow Users to Choose Their Home** is enabled, **Set as my Home** updates the current user's native Default Workspace through a permission-checked API. It cannot modify another user. Existing user defaults continue to take precedence when personal home selection is disabled.

**Whitelabel Workspace Group** gathers an explicitly ordered list and/or workspaces from a Module Def. Groups do not change workspace modules, app ownership or permissions. Users see only accessible entries, including their own private workspaces in **My Workspaces**. Workspaces outside configured groups are grouped by module. Access to cards, reports, charts and underlying records continues to use native permissions.

Workspaces must already be accessible under native role, module and domain rules. An empty custom Module Def does not grant module access. For navigation-only grouping, keep workspaces in an accessible native module and collect them into a group with your chosen name. Users with native workspace creation permission can also create a personal workspace from the directory menu.

System Managers configure settings and rules. System Managers and Workspace Managers configure groups and retain native workspace tools. The directory's menu exposes the applicable management links. A System Manager can explicitly **Publish Desktop Shortcut** from a group to create a shared native Desktop Icon and Workspace Sidebar pointing to that group's directory. These records are ordinary site records; manage or remove them in their native lists. Publication never overwrites an existing icon or sidebar. Empty or disabled groups expose no workspace entries.

Developers can ship rules and groups as fixtures using their normal app workflow. No workspace, role or business name is hardcoded. Disabling Workspace Navigation restores native routing and removes the navigation controls on the next load; existing workspaces, user defaults and configured groups/rules are retained.

Navigation regression tests:

```sh
bench --site test-site.local run-tests --app whitelabel --module whitelabel.tests.test_navigation
bench --site test-site.local run-ui-tests whitelabel --headless --browser chrome --spec whitelabel/tests/ui_test_navigation.js
```

## Production

Use a production WSGI server and reverse proxy rather than `bench start`. Keep developer mode and error tracebacks disabled so internal package names and stack traces are not shown on error pages.

## License

MIT. See [LICENSE](LICENSE).
