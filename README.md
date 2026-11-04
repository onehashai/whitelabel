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
- ERPNext `>=16,<17`, if installed (optional)
- Python 3.14
- Node.js 24 for asset builds

Workspace navigation is site- and industry-independent. It uses the site's existing workspaces, roles, Role Profiles and users, including workspaces supplied by other installed apps. No Kairos configuration or business-specific workspace definitions are installed. The regression site runs Frappe and Whitelabel without ERPNext.

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

System Users get **Home**, **Workspaces**, **All Workspaces** and **All Apps** in the existing sidebar header menu throughout Desk. **Workspaces** opens a searchable, permission-filtered switcher with workspace groups and personal Home selection. On All Apps, where Frappe hides the sidebar, the same controls appear in the profile menu. There is no additional top bar. Home consistently resolves from `/desk`, an implicit successful login, and `/login` for an already signed-in System User. Root routing is separately configurable. Explicit login destinations and direct links are preserved; redirects to bare `/desk` resolve Home. **All Apps** opens `/desk/desktop` explicitly, bypassing Home routing. Setup Wizard behavior is preserved.

Switching workspaces does not change the default. When **Allow Users to Choose Their Home** is enabled, **Set as my Home** updates the current user's native Default Workspace through a permission-checked API. It cannot modify another user. Existing user defaults continue to take precedence when personal home selection is disabled.

The native breadcrumb Home icon and menu Home navigate directly to the destination supplied in boot data, including its configured sidebar. Home clicks do not request configuration or render the native desktop first. Programmatic `/desk` navigation and bare history entries resolve before page rendering. Configuration refreshes when opening the workspace switcher/directory, returning to a tab, or saving navigation-related documents; personal Home changes notify other tabs. Native workspace and document permissions still apply at the destination.

**Whitelabel Workspace Group** gathers an explicitly ordered list and/or workspaces from a Module Def. Groups do not change workspace modules, app ownership or permissions. Users see only accessible entries, including their own private workspaces in **My Workspaces**. Workspaces outside configured groups are grouped by module. Access to cards, reports, charts and underlying records continues to use native permissions.

Workspaces must already be accessible under native role, module and domain rules. An empty custom Module Def does not grant module access. For navigation-only grouping, keep workspaces in an accessible native module and collect them into a group with your chosen name. Users with native workspace creation permission can also create a personal workspace from the directory menu.

System Managers configure settings and rules. System Managers and Workspace Managers configure groups and retain native workspace tools. The directory's menu exposes the applicable management links. A System Manager can explicitly **Publish Desktop Shortcut** from a group to create a shared native Desktop Icon and Workspace Sidebar pointing to that group's directory. These records are ordinary site records; manage or remove them in their native lists. Publication never overwrites an existing icon or sidebar. Empty or disabled groups expose no workspace entries.

Developers can ship rules and groups as fixtures using their normal app workflow. No workspace, role or business name is hardcoded. Disabling Workspace Navigation restores native routing and removes the navigation controls on the next load; existing workspaces, user defaults and configured groups/rules are retained.

Navigation regression tests:

```sh
bench --site test-site.local run-tests --app whitelabel --module whitelabel.tests.test_navigation
bench --site test-site.local run-ui-tests whitelabel --headless --browser chrome --spec whitelabel/tests/ui_test_navigation.js
```

## Classic workspace navigation

Classic mode keeps a curated workspace tree in the existing Desk sidebar and opens real v16 workspaces on the right. The same tree remains available on forms, lists and reports. Workspace names navigate; separate arrow buttons expand children. Search reveals matching descendants and their parents. Expanded branches are remembered for each user in the browser. Home uses the existing direct routing, without showing the native desktop first.

Deploy and configure in this order:

1. Pull the app, run `bench --site your-site.local migrate`, and run `bench build --app whitelabel`.
2. Open **Whitelabel Setting → Navigation → Navigation Profiles**. Create a profile and add only the shared workspaces the person needs. Rows define display order; leave **Parent Workspace** empty for a main workspace, or select another row to nest it. Any workspace can have children. Optional labels and icons change navigation presentation only.
3. Add **Assignments** for Roles, Role Profiles or individual System Users. Set the profile's **Home Workspace**, if required. Create an administrator profile too if administrators should have a curated business view.
4. Enable Workspace Navigation and select **Desk Layout → Classic**. Optionally set a **Default Navigation Profile** for users without a matching assignment. Save and reload Desk.

Profiles assigned directly to a User replace that user's role-based profiles. Otherwise matching Role Profile and Role assignments combine. Role Profile assignments take precedence over Role assignments; lower priorities win within each level, then profile name breaks ties. A workspace appears once, with the first matching profile determining its placement and display label. Empty or disabled profiles do not broaden access. Unassigned users without a default profile see “No workspaces assigned” and any enabled personal workspaces, rather than an automatic list of modules.

In Classic mode, the personal Home preference, matching Home rules/profile defaults, and site default are considered only if their destination is in the curated tree. Profile defaults participate at their assignment level. If no configured Home is available, the first visible workspace opens; an empty tree opens the workspace directory. A user cannot select an unlisted shared workspace as their personal Home through this feature.

**Show Personal Workspaces** adds only the user's own private workspaces. **New Workspace** creates a private workspace through native permissions and immediately adds it to Personal, without requiring a reload. It can be nested under another personal workspace. Use the native workspace Edit menu to add charts, cards, links and custom blocks. Shared workspace creation and editing retain native Workspace Manager requirements. System Managers organise shared navigation through profiles; the sidebar and header menu include the management link.

All configured entries pass native workspace role, module, domain, visibility and ownership checks. An accessible child of an inaccessible parent remains reachable without displaying the restricted parent. Profiles control presentation and do not grant access: permitted direct document/report links and global search remain available. No Accounting, Stock, Setup or other module is automatically added. Website Users retain their portal and website routing.

Existing workspace records, chart definitions and layouts are reused. Classic mode does not import v15 business dashboards or create replacement standard workspaces. Site-specific v15 content must be restored or built in the native workspace editor; adding its workspace to a profile makes it part of the tree. Existing Workspace Groups remain available for Standard navigation, while Classic navigation is defined by profiles.

Selecting **Desk Layout → Standard** restores the native sidebar. Disabling Workspace Navigation restores native routing too. Both retain profiles, workspace content and personal Home preferences. No core files are edited; the sidebar adapter is scoped to Classic mode and should be checked when upgrading v16.

Additional browser regression:

```sh
bench --site test-site.local run-ui-tests whitelabel --headless --browser chrome --spec whitelabel/tests/ui_test_classic_workspace.js
```

## Public workspace migration protection

Some v16 releases remove site-created public workspaces during `bench migrate` when their App and Module are populated but no native workspace JSON exists. Whitelabel provides **Protect During Migration** on Workspace records, independently of whether Workspace Navigation is enabled.

Mark existing site-managed public workspaces before the next migration. The field can be created through Customize Form before deploying this update: fieldname `custom_whitelabel_protect_migration`, type Check, default `0`, on Workspace. This lets the first migration of the updated app protect already-marked records. Whitelabel also installs the field through `before_migrate` and `after_install`. The checkbox is available on the native Workspace form; **Protected Workspaces** in Whitelabel Setting opens the marked records.

New public workspaces created through normal site operations outside developer mode are protected automatically. Imports, patches, migration-created records and developer-mode workspaces retain their normal app-managed lifecycle. Existing workspaces are not automatically reclassified because an obsolete app workspace and a site-created workspace can have identical metadata. Administrators can opt out by unchecking the field on an existing record. Intentional deletion outside migration still uses normal permissions and link checks.

Before migration, the app records the protected names and writes a private snapshot of the workspaces and their referenced Number Cards, Dashboard Charts and Custom HTML Blocks under `private/backups/whitelabel-workspaces/`. Snapshot files have mode `0600`. An unwritable snapshot or a protected name that now collides with app-shipped JSON aborts before patches/imports run. During migration, a Workspace class extension blocks deletion before the core `on_trash` controller and its side effects. Native orphan cleanup reports that deletion was skipped and continues with unprotected app entities. After migration, the app verifies preserved workspace content, role tables and widget references; unexpected changes fail verification and retain the snapshot for recovery. Nothing is silently restored or overwritten.

On affected releases, native cleanup prints `Error occurred while deleting entity` followed by `Skipping migration deletion of protected workspace ...` for a blocked attempt. This is an expected skip; the final `Verified ... protected workspace(s)` message confirms that the records and widget content remained intact.

This guard targets native document deletion during migration. Direct SQL deletion, `ignore_on_trash`, and schema reloads bypass document hooks; snapshots and verification help detect such changes, but are not a replacement for a full database backup. Server Scripts are deliberately not used: the framework skips document-event Server Scripts during migration. The protection code must be deployed before running the next migration; the checkbox alone cannot protect records on an older app version.

Do not mark workspaces shipped by an installed app as site-managed. Their native workspace JSON belongs in source control. Standard app imports and intentional retirement of unprotected app records remain unchanged. Protection snapshots are private site data and can be retained/archived using the site's backup policy.

Regression checks:

```sh
bench --site test_site run-tests --app whitelabel --module whitelabel.tests.test_workspace_protection
# Full cleanup regression: disposable .test site, allow_tests enabled, developer_mode disabled.
bench --site disposable.test execute whitelabel.tests.migration_workspace_roundtrip.run
```

The full regression executes two complete migrations and checks that protected public workspaces, their content and their referenced widgets remain intact, that they never appear in Deleted Document, and that an explicitly unprotected orphan is still removed.

## Production

Use a production WSGI server and reverse proxy rather than `bench start`. Keep developer mode and error tracebacks disabled so internal package names and stack traces are not shown on error pages.

## License

MIT. See [LICENSE](LICENSE).
