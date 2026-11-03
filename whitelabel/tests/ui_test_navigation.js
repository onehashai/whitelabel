const ADMIN = Cypress.env("adminPassword") || "admin";
const PASSWORD = "Navigation-test-Password1";
const SYSTEM = "navigation-browser@example.test";
const WEBSITE = "navigation-portal@example.test";
const A = "Navigation Browser A";
const B = "Navigation Browser B";
const RESTRICTED = "Navigation Browser Restricted";
const GROUP = "Navigation Browser Group";
const routeA = "/desk/navigation-browser-a";
const routeB = "/desk/navigation-browser-b";
const configuration = [
  "enable_workspace_navigation",
  "route_root_to_workspace",
  "allow_user_workspace_home",
  "default_workspace",
  "default_workspace_sidebar",
];
let originalSettings;

function api(method, body, failOnStatusCode = true) {
  return cy.window().then((window) =>
    cy.request({
      method: "POST",
      url: `/api/method/${method}`,
      body,
      failOnStatusCode,
      headers: window.frappe?.csrf_token
        ? { "X-Frappe-CSRF-Token": window.frappe.csrf_token }
        : {},
    })
  );
}
function insert(doc) {
  return api("frappe.client.insert", { doc: JSON.stringify(doc) });
}
function update(doctype, name, values) {
  return api("frappe.client.set_value", {
    doctype,
    name,
    fieldname: JSON.stringify(values),
  });
}

function menuAction(label) {
  cy.window().then((window) => {
    if (window.location.pathname === "/desk/desktop") {
      cy.get(".desktop-avatar:visible").click();
      return;
    }
    if (window.frappe.is_mobile()) window.frappe.app.sidebar.open();
    cy.get(".sidebar-header:visible").click();
  });
  cy.contains(
    ".frappe-menu:visible .menu-item-title",
    new RegExp(`^${label}$`)
  ).click();
}

describe("Workspace navigation", () => {
  before(() => {
    cy.login("Administrator", ADMIN);
    api("frappe.client.get", { doctype: "Whitelabel Setting" }).then(
      ({ body }) => {
        originalSettings = Object.fromEntries(
          configuration.map((field) => [field, body.message[field]])
        );
      }
    );
    insert({
      doctype: "Web Page",
      name: "navigation-portal-test",
      title: "Navigation Portal Test",
      route: "navigation-portal-test",
      published: 1,
      content_type: "HTML",
      main_section_html: "<p>Navigation portal destination</p>",
    });
    insert({
      doctype: "Role",
      role_name: "Navigation Browser User",
      desk_access: 1,
    });
    insert({
      doctype: "Role",
      role_name: "Navigation Browser Portal",
      desk_access: 0,
      home_page: "/navigation-portal-test",
    });
    insert({
      doctype: "User",
      email: SYSTEM,
      first_name: "Navigation Browser",
      send_welcome_email: 0,
      new_password: PASSWORD,
      roles: [{ role: "Navigation Browser User" }],
    });
    insert({
      doctype: "User",
      email: WEBSITE,
      first_name: "Navigation Portal",
      send_welcome_email: 0,
      new_password: PASSWORD,
      roles: [{ role: "Navigation Browser Portal" }],
    });
    [A, B, RESTRICTED].forEach((name) =>
      insert({
        doctype: "Workspace",
        label: name,
        title: name,
        module: "Core",
        public: 1,
        content: JSON.stringify([
          {
            id: "navtestheader",
            type: "header",
            data: { text: name, col: 12 },
          },
        ]),
        roles: [
          {
            role:
              name === RESTRICTED
                ? "Navigation Browser Portal"
                : "Navigation Browser User",
          },
        ],
      })
    );
    insert({
      doctype: "Whitelabel Workspace Group",
      title: GROUP,
      enabled: 1,
      workspaces: [
        { workspace: A },
        { workspace: B },
        { workspace: RESTRICTED },
      ],
    });
    insert({
      doctype: "Whitelabel Workspace Rule",
      title: "Navigation Browser Rule",
      enabled: 1,
      applies_to: "Role",
      role: "Navigation Browser User",
      workspace: A,
      priority: 10,
    });
    // Simulate an account converted from a System User to a Website User.
    update("User", WEBSITE, { default_workspace: A, default_app: "frappe" });
    update("Whitelabel Setting", "Whitelabel Setting", {
      enable_workspace_navigation: 1,
      route_root_to_workspace: 1,
      allow_user_workspace_home: 1,
      default_workspace: B,
      default_workspace_sidebar: null,
    });
  });

  after(() => {
    cy.login("Administrator", ADMIN);
    cy.visit("/desk/workspace-directory");
    if (originalSettings)
      update("Whitelabel Setting", "Whitelabel Setting", originalSettings);
    [
      ["Whitelabel Workspace Rule", "Navigation Browser Rule"],
      ["Whitelabel Workspace Group", GROUP],
      ["User", SYSTEM],
      ["User", WEBSITE],
      ["Workspace", A],
      ["Workspace", B],
      ["Workspace", RESTRICTED],
      ["Web Page", "navigation-portal-test"],
      ["Role", "Navigation Browser User"],
      ["Role", "Navigation Browser Portal"],
    ].forEach(([doctype, name]) => {
      api("frappe.client.delete", { doctype, name }, false);
    });
  });

  it("sends an implicit System User login, root, login page and desk to the same Home", () => {
    cy.clearAllCookies();
    api("login", { usr: SYSTEM, pwd: PASSWORD }).then(({ body }) => {
      expect(body.home_page).to.contain(routeA);
    });
    ["/", "/login", "/desk"].forEach((path) => {
      cy.visit(path);
      cy.location("pathname").should("eq", routeA);
      cy.get(".sidebar-header").should("be.visible");
      cy.get("#whitelabel-navigation").should("not.exist");
    });
  });

  it("switches permitted workspaces and returns Home after opening a form", () => {
    cy.login(SYSTEM, PASSWORD);
    cy.visit(routeA);
    menuAction("Workspaces");
    cy.get(".modal:visible").within(() => {
      cy.contains(".whitelabel-workspace-group", GROUP).should("be.visible");
      cy.contains(".whitelabel-workspace-link", B).click();
    });
    cy.location("pathname").should("eq", routeB);
    menuAction("Home");
    cy.location("pathname").should("eq", routeA);
    cy.visit(`/desk/user/${SYSTEM}`);
    menuAction("Home");
    cy.location("pathname").should("eq", routeA);
    cy.reload();
    cy.get(".sidebar-header").should("exist");
  });

  it("routes the native breadcrumb directly Home without a configuration request or intermediate render", () => {
    cy.login(SYSTEM, PASSWORD);
    cy.visit(`/desk/user/${SYSTEM}`);
    cy.window().should((window) =>
      expect(window.cur_frm?.doc.name).to.eq(SYSTEM)
    );
    cy.window().then(
      (window) =>
        new Cypress.Promise((resolve) => window.frappe.after_ajax(resolve))
    );
    // A slow configuration service must not delay Home or allow Desktop to render.
    cy.intercept(
      "POST",
      "/api/method/whitelabel.navigation.get_context",
      (request) => {
        request.on("response", (response) => response.setDelay(2500));
      }
    ).as("homeConfiguration");
    const renders = [];
    let expectedHome;
    cy.window().then((window) => {
      expectedHome = new URL(
        window.frappe.boot.whitelabel_navigation.home_route,
        window.location.origin
      );
      const render = window.frappe.router.render;
      cy.stub(window.frappe.router, "render").callsFake(function (...args) {
        renders.push(window.location.pathname);
        return render.apply(this, args);
      });
      cy.spy(window.history, "pushState").as("homeHistory");
    });
    cy.get(".page-container:visible .navbar-breadcrumbs li:first-child a")
      .should("have.attr", "href")
      .and("contain", routeA);
    cy.get(
      ".page-container:visible .navbar-breadcrumbs li:first-child a"
    ).click();
    cy.location("pathname").should("eq", routeA);
    cy.location("search").should((search) =>
      expect(search).to.eq(expectedHome.search)
    );
    cy.get("@homeConfiguration.all").should("have.length", 0);
    cy.get("@homeHistory").should((spy) => {
      expect(spy.getCalls().map((call) => call.args[2])).to.deep.eq([
        expectedHome.pathname + expectedHome.search,
      ]);
    });
    cy.go("back");
    cy.location("pathname").should("eq", `/desk/user/${SYSTEM}`);
    cy.go("forward");
    cy.location("pathname").should("eq", routeA);
    cy.then(() =>
      expect(renders).to.deep.eq([routeA, `/desk/user/${SYSTEM}`, routeA])
    );
    menuAction("Home");
    cy.get("@homeHistory").should("have.been.calledOnce");
    cy.get("@homeConfiguration.all").should("have.length", 0);
  });

  it("resolves programmatic Home and bare history entries before native rendering", () => {
    cy.login(SYSTEM, PASSWORD);
    cy.visit(`/desk/user/${SYSTEM}`);
    cy.window().should((window) =>
      expect(window.cur_frm?.doc.name).to.eq(SYSTEM)
    );
    const renders = [];
    cy.window().then((window) => {
      const render = window.frappe.router.render;
      cy.stub(window.frappe.router, "render").callsFake(function (...args) {
        renders.push(window.location.pathname);
        return render.apply(this, args);
      });
      cy.spy(window.history, "pushState").as("programmaticHistory");
      window.frappe.set_route();
    });
    cy.location("pathname").should("eq", routeA);
    cy.get("@programmaticHistory").should((spy) => {
      expect(spy.getCalls().map((call) => call.args[2])).not.to.include(
        "/desk"
      );
    });
    cy.wrap(renders).should("deep.equal", [routeA]);
    cy.window().then((window) => {
      window.history.pushState(null, "", "/desk");
      window.dispatchEvent(new window.PopStateEvent("popstate"));
    });
    cy.location("pathname").should("eq", routeA);
    cy.wrap(renders).should("deep.equal", [routeA, routeA]);
  });

  it("filters workspace entries and remembers an explicitly chosen Home", () => {
    cy.login(SYSTEM, PASSWORD);
    cy.visit("/desk/workspace-directory");
    cy.get(".whitelabel-workspace-link").should("not.contain.text", RESTRICTED);
    cy.get("input[type=search]").type(B);
    cy.get(".whitelabel-workspace-row")
      .should("have.length", 1)
      .within(() => {
        cy.contains("button", "Set as my Home").click();
      });
    menuAction("Home");
    cy.location("pathname").should("eq", routeB);
    cy.get(".page-container:visible .navbar-breadcrumbs li:first-child a")
      .should("have.attr", "href")
      .and("contain", routeB);
    cy.visit("/");
    cy.location("pathname").should("eq", routeB);
  });

  it("keeps an explicit desktop escape and works on mobile", () => {
    cy.login(SYSTEM, PASSWORD);
    cy.visit(routeB);
    cy.viewport(390, 844);
    cy.get(".sidebar-header").should("exist");
    menuAction("Workspaces");
    cy.get(".modal:visible .whitelabel-workspace-link")
      .first()
      .should("be.visible");
    cy.get(".modal:visible .btn-modal-close").click();
    menuAction("All Apps");
    cy.location("pathname").should("eq", "/desk/desktop");
    menuAction("Home");
    cy.location("pathname").should("eq", routeB);
    cy.viewport(1400, 960);
  });

  it("keeps native form actions accessible without an extra bar on desktop and mobile", () => {
    cy.window().then(
      (window) =>
        new Cypress.Promise((resolve) => window.frappe.after_ajax(resolve))
    );
    cy.login("Administrator", ADMIN);
    cy.visit(`/desk/workspace/${encodeURIComponent(A)}`);
    cy.window().should((window) => {
      expect(window.cur_frm?.doc.name).to.eq(A);
    });
    cy.window().then((window) => window.cur_frm.dirty());

    function checkActions() {
      cy.get(".page-container:visible .page-head .primary-action")
        .should("be.visible")
        .should(($button) => {
          const button = $button[0];
          const window = button.ownerDocument.defaultView;
          const bounds = button.getBoundingClientRect();
          expect(window.document.getElementById("whitelabel-navigation")).to.eq(
            null
          );
          expect(bounds.top, "Save is inside the viewport").to.be.at.least(0);
          expect(bounds.bottom, "Save is inside the viewport").to.be.at.most(
            window.innerHeight
          );
          const target = window.document.elementFromPoint(
            bounds.x + bounds.width / 2,
            bounds.y + bounds.height / 2
          );
          expect(button.contains(target), "Save receives clicks").to.eq(true);
        });
    }

    [1400, 390].forEach((width) => {
      cy.viewport(width, 844);
      if (width < 992) {
        // Resizing an expanded desktop sidebar opens the native mobile overlay.
        cy.get(".body-sidebar-container .overlay:visible").click("right");
      }
      checkActions();
      cy.window().then((window) => {
        // Browser focus/scrollIntoView can scroll both the Desk and the document.
        window.document.querySelector(".main-section").scrollTop = 500;
        window.scrollTo(0, 500);
      });
      checkActions();
      cy.get(".main-section").should(($section) => {
        expect($section[0].getBoundingClientRect().bottom).to.be.at.most(844);
      });
      cy.screenshot(`workspace-form-actions-${width}`, { capture: "viewport" });
    });
    cy.get(".page-container:visible .page-head .primary-action").click();
    cy.window().should((window) =>
      expect(window.cur_frm.is_dirty()).to.eq(false)
    );
    cy.viewport(1400, 960);
  });

  it("preserves Website User portal login, root and explicit links", () => {
    cy.clearAllCookies();
    api("login", { usr: WEBSITE, pwd: PASSWORD }).then(({ body }) => {
      expect(body.message).to.eq("No App");
      expect(body.home_page).to.contain("navigation-portal-test");
    });
    cy.visit("/");
    cy.contains("Navigation portal destination").should("be.visible");
    cy.get("#whitelabel-navigation").should("not.exist");
    api("whitelabel.navigation.get_context", {}).then(({ body }) => {
      expect(body.message ?? null).to.be.null;
    });
    cy.request({ url: "/desk", failOnStatusCode: false })
      .its("status")
      .should("eq", 403);
    cy.request({
      method: "POST",
      url: "/api/method/whitelabel.navigation.set_my_home",
      body: { workspace: A },
      failOnStatusCode: false,
    })
      .its("status")
      .should("eq", 403);
    cy.visit("/navigation-portal-test");
    cy.get("#whitelabel-navigation").should("not.exist");
  });

  it("preserves explicit login destinations and restores native Desk when disabled", () => {
    cy.clearAllCookies();
    cy.visit(
      `/login?redirect-to=${encodeURIComponent(`/desk/user/${SYSTEM}`)}`
    );
    cy.get("#login_email").type(SYSTEM);
    cy.get("#login_password").type(PASSWORD, { log: false });
    cy.get(".btn-login:visible").click();
    cy.location("pathname").should("eq", `/desk/user/${SYSTEM}`);
    cy.get(".sidebar-header").should("exist");
    cy.window().then(
      (window) =>
        new Cypress.Promise((resolve) => window.frappe.after_ajax(resolve))
    );
    cy.login("Administrator", ADMIN);
    cy.visit("/desk/workspace-directory");
    cy.window().its("frappe.session.user").should("eq", "Administrator");
    update("Whitelabel Setting", "Whitelabel Setting", {
      enable_workspace_navigation: 0,
    });
    cy.request({ url: "/desk", followRedirect: false })
      .its("status")
      .should("eq", 200);
    cy.visit(routeB);
    cy.location("pathname").should("eq", routeB);
    cy.get("#whitelabel-navigation").should("not.exist");
    cy.get(
      ".page-container:visible .navbar-breadcrumbs li:first-child a"
    ).should("have.attr", "href", "/desk");
  });
});
