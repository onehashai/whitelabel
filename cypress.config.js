const path = require("path");

const { defineConfig } = require("../frappe/node_modules/cypress");

module.exports = defineConfig({
  adminPassword: "admin",
  defaultCommandTimeout: 20000,
  pageLoadTimeout: 30000,
  retries: {
    runMode: 1,
    openMode: 0,
  },
  video: false,
  viewportHeight: 960,
  viewportWidth: 1400,
  e2e: {
    baseUrl: "http://test_site_ui:8000",
    setupNodeEvents(on, config) {
      on("before:browser:launch", (browser, launchOptions) => {
        const localSiteAddress = process.env.CYPRESS_LOCAL_SITE_ADDRESS;
        if (browser.family === "chromium" && localSiteAddress) {
          const siteHost = new URL(config.baseUrl).hostname;
          launchOptions.args.push(
            `--host-resolver-rules=MAP ${siteHost} ${localSiteAddress}`
          );
        }
        return launchOptions;
      });
      return config;
    },
    specPattern: "whitelabel/tests/ui_test_*.js",
    supportFile: path.resolve(__dirname, "whitelabel/tests/support.js"),
    testIsolation: false,
  },
});
