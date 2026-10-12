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

## Production

Use a production WSGI server and reverse proxy rather than `bench start`. Keep developer mode and error tracebacks disabled so internal package names and stack traces are not shown on error pages.

## License

MIT. See [LICENSE](LICENSE).
