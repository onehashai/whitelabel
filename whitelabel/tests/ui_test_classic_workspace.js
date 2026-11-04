const ADMIN = Cypress.env("adminPassword") || "admin";
const USER = "classic-browser@example.test";
const PASSWORD = "Classic-browser-Password1";
const OPERATOR = "Classic Operator";
const MANAGER = "Classic Manager";
const BOARD = "Classic Board";
const CHILD = "Classic Detail";
const GRANDCHILD = "Classic Daily Detail";
const RESTRICTED = "Classic Restricted";
const UNLISTED = "Classic Unlisted";
const PERSONAL = "Classic Personal";
const CREATED = "Classic Created";
const PROFILE = "Classic Operator View";
const MANAGER_PROFILE = "Classic Manager View";
const ADMIN_PROFILE = "Classic Admin View";
const CARD = "Classic Browser Count";
const BLOCK = "Classic Browser Block";
const route = (name) => `/desk/${name.toLowerCase().replaceAll(" ", "-")}`;
const fields = [
  "enable_workspace_navigation",
  "desk_layout",
  "default_navigation_profile",
  "show_personal_workspaces",
  "route_root_to_workspace",
  "allow_user_workspace_home",
  "default_workspace",
  "default_workspace_sidebar",
];
let original;

function api(method, args, failOnStatusCode = true) {
  return cy.window().then((window) =>
    cy.request({
      method: "POST",
      url: `/api/method/${method}`,
      body: args,
      failOnStatusCode,
      headers: window.frappe?.csrf_token
        ? { "X-Frappe-CSRF-Token": window.frappe.csrf_token }
        : {},
    })
  );
}
const insert = (doc) =>
  api("frappe.client.insert", { doc: JSON.stringify(doc) });
const update = (doctype, name, values) =>
  api("frappe.client.set_value", {
    doctype,
    name,
    fieldname: JSON.stringify(values),
  });
const node = (name) =>
  cy.get(`.whitelabel-tree-node[data-workspace="${name}"]`);
const link = (name) =>
  node(name).children(".whitelabel-tree-row").find(".whitelabel-tree-link");
const toggle = (name) =>
  node(name).children(".whitelabel-tree-row").find(".whitelabel-tree-toggle");

describe("Classic workspace", () => {
  before(() => {
    cy.login("Administrator", ADMIN);
    api("frappe.client.get", { doctype: "Whitelabel Setting" }).then(
      ({ body }) => {
        original = Object.fromEntries(
          fields.map((field) => [field, body.message[field]])
        );
      }
    );
    ["Classic Operator Role", "Classic Manager Role"].forEach((role) =>
      insert({ doctype: "Role", role_name: role, desk_access: 1 })
    );
    insert({
      doctype: "User",
      email: USER,
      first_name: "Classic Browser",
      new_password: PASSWORD,
      send_welcome_email: 0,
      roles: [
        { role: "Classic Operator Role" },
        { role: "Classic Manager Role" },
      ],
    });
    insert({
      doctype: "Number Card",
      name: CARD,
      label: CARD,
      type: "Document Type",
      document_type: "User",
      function: "Count",
      filters_json: "[]",
      is_public: 1,
    });
    insert({
      doctype: "Custom HTML Block",
      name: BLOCK,
      html: "<p>Classic workspace content is native</p>",
      private: 0,
    });
    [OPERATOR, MANAGER, BOARD, CHILD, GRANDCHILD, RESTRICTED, UNLISTED].forEach(
      (name) =>
        insert({
          doctype: "Workspace",
          label: name,
          title: name,
          module: "Core",
          public: 1,
          content: JSON.stringify([
            {
              id: "classicheader",
              type: "header",
              data: { text: name, col: 12 },
            },
            {
              id: "classiccard",
              type: "number_card",
              data: { number_card_name: CARD, col: 6 },
            },
            {
              id: "classicblock",
              type: "custom_block",
              data: { custom_block_name: BLOCK, col: 12 },
            },
          ]),
          number_cards: [{ number_card_name: CARD, label: CARD }],
          custom_blocks: [{ custom_block_name: BLOCK, label: BLOCK }],
          roles: [
            {
              role:
                name === RESTRICTED
                  ? "System Manager"
                  : "Classic Operator Role",
            },
          ],
        })
    );
    insert({
      doctype: "Workspace",
      label: PERSONAL,
      title: PERSONAL,
      module: "Core",
      public: 0,
      for_user: USER,
      content: "[]",
    });
    const rows = [
      { workspace: OPERATOR },
      { workspace: CHILD, parent_workspace: OPERATOR },
      { workspace: GRANDCHILD, parent_workspace: CHILD },
      { workspace: BOARD },
      { workspace: RESTRICTED },
    ];
    insert({
      doctype: "Whitelabel Navigation Profile",
      title: PROFILE,
      enabled: 1,
      priority: 10,
      default_workspace: OPERATOR,
      assignments: [{ applies_to: "Role", role: "Classic Operator Role" }],
      workspaces: rows,
    });
    insert({
      doctype: "Whitelabel Navigation Profile",
      title: MANAGER_PROFILE,
      enabled: 1,
      priority: 20,
      default_workspace: MANAGER,
      assignments: [{ applies_to: "Role", role: "Classic Manager Role" }],
      workspaces: [{ workspace: MANAGER }, { workspace: BOARD }],
    });
    insert({
      doctype: "Whitelabel Navigation Profile",
      title: ADMIN_PROFILE,
      enabled: 1,
      default_workspace: OPERATOR,
      assignments: [{ applies_to: "User", user: "Administrator" }],
      workspaces: [...rows, { workspace: MANAGER }],
    });
    update("Whitelabel Setting", "Whitelabel Setting", {
      enable_workspace_navigation: 1,
      desk_layout: "Classic",
      show_personal_workspaces: 1,
      default_navigation_profile: null,
      route_root_to_workspace: 1,
      allow_user_workspace_home: 1,
      default_workspace: null,
      default_workspace_sidebar: null,
    });
  });

  after(() => {
    cy.login("Administrator", ADMIN);
    cy.visit(route(OPERATOR));
    if (original) update("Whitelabel Setting", "Whitelabel Setting", original);
    [
      ["Whitelabel Navigation Profile", PROFILE],
      ["Whitelabel Navigation Profile", MANAGER_PROFILE],
      ["Whitelabel Navigation Profile", ADMIN_PROFILE],
      ["User", USER],
      ...[
        OPERATOR,
        MANAGER,
        BOARD,
        CHILD,
        GRANDCHILD,
        RESTRICTED,
        UNLISTED,
        PERSONAL,
        `${CREATED}-${USER}`,
      ].map((name) => ["Workspace", name]),
      ["Number Card", CARD],
      ["Custom HTML Block", BLOCK],
      ["Role", "Classic Operator Role"],
      ["Role", "Classic Manager Role"],
    ].forEach(([doctype, name]) =>
      api("frappe.client.delete", { doctype, name }, false)
    );
  });

  it("opens the role Home with a merged, curated tree and native dashboard content", () => {
    cy.login(USER, PASSWORD);
    cy.visit("/");
    cy.location("pathname").should("eq", route(OPERATOR));
    cy.get("body").should("have.class", "whitelabel-classic");
    [OPERATOR, BOARD, MANAGER, PERSONAL].forEach((name) =>
      link(name).should("be.visible")
    );
    cy.get(`.whitelabel-tree-node[data-workspace="${BOARD}"]`).should(
      "have.length",
      1
    );
    cy.get(".whitelabel-classic-tree")
      .should("not.contain.text", RESTRICTED)
      .and("not.contain.text", UNLISTED)
      .and("not.contain.text", "Core");
    cy.contains("Classic workspace content is native", {
      includeShadowDom: true,
    }).should("be.visible");
    cy.get("#whitelabel-navigation").should("not.exist");
    cy.screenshot("classic-workspace-desktop", { capture: "viewport" });
  });

  it("expands without navigation, searches nested workspaces, and remembers the selected branch", () => {
    cy.login(USER, PASSWORD);
    cy.visit(route(OPERATOR));
    link(CHILD).should("not.be.visible");
    toggle(OPERATOR).click();
    cy.location("pathname").should("eq", route(OPERATOR));
    link(CHILD).should("be.visible");
    toggle(CHILD).click();
    link(GRANDCHILD).should("be.visible").click();
    cy.location("pathname").should("eq", route(GRANDCHILD));
    link(GRANDCHILD).should("have.attr", "aria-current", "page");
    cy.reload();
    link(GRANDCHILD).should("be.visible");
    cy.get(".whitelabel-tree-search").type(MANAGER);
    link(MANAGER).should("be.visible");
    link(OPERATOR).should("not.be.visible");
    cy.get(".whitelabel-tree-search").clear().type(GRANDCHILD);
    link(OPERATOR).should("be.visible");
    link(GRANDCHILD).should("be.visible");
    cy.get(".whitelabel-tree-search").clear();
    link(OPERATOR).click();
    cy.location("pathname").should("eq", route(OPERATOR));
    link(CHILD).should("be.visible");
  });

  it("keeps the same tree on forms and returns directly Home from the native breadcrumb", () => {
    cy.login(USER, PASSWORD);
    cy.visit(route(MANAGER));
    cy.window().then((window) => window.frappe.set_route("Form", "User", USER));
    cy.location("pathname").should(
      "eq",
      `/desk/user/${encodeURIComponent(USER)}`
    );
    [OPERATOR, MANAGER, BOARD].forEach((name) =>
      link(name).should("be.visible")
    );
    link(MANAGER).should("have.attr", "aria-current", "page");
    cy.get(".page-container:visible .navbar-breadcrumbs li:first-child a")
      .should("have.attr", "href", route(OPERATOR))
      .click();
    cy.location("pathname").should("eq", route(OPERATOR));
    cy.go("back");
    cy.location("pathname").should(
      "eq",
      `/desk/user/${encodeURIComponent(USER)}`
    );
  });

  it("uses the mobile sidebar without covering native page actions", () => {
    cy.login(USER, PASSWORD);
    cy.visit(route(OPERATOR));
    cy.viewport(390, 844);
    cy.window().then((window) => window.frappe.app.sidebar.open());
    link(BOARD).should("be.visible").click();
    cy.location("pathname").should("eq", route(BOARD));
    cy.get(".body-sidebar-container").should("not.have.class", "expanded");
    cy.screenshot("classic-workspace-mobile", { capture: "viewport" });
    cy.viewport(1400, 960);
  });

  it("creates a personal workspace and opens it without a reload", () => {
    cy.login(USER, PASSWORD);
    cy.visit(route(OPERATOR));
    cy.get(".whitelabel-tree-new").click();
    cy.get(".modal:visible input[data-fieldname=title]").type(CREATED);
    cy.get(".modal:visible .btn-primary").click();
    cy.location("pathname").should("contain", "/desk/private/classic-created-");
    link(`${CREATED}-${USER}`)
      .should("be.visible")
      .and("contain.text", CREATED);
    cy.get(".page-container:visible .editor-js-container").should(
      "contain.text",
      CREATED
    );
  });

  it("preserves native workspace editing, widgets, and Save", () => {
    cy.window().then(
      (window) =>
        new Cypress.Promise((resolve) => window.frappe.after_ajax(resolve))
    );
    cy.login("Administrator", ADMIN);
    cy.visit(route(OPERATOR));
    cy.contains(CARD).should("be.visible");
    cy.contains("Classic workspace content is native", {
      includeShadowDom: true,
    }).should("be.visible");
    cy.window().then((window) =>
      cy.wrap(window.frappe.workspace.workspace_actions_button).click()
    );
    cy.contains(".frappe-menu:visible .menu-item-title", /^Edit$/).click();
    cy.intercept(
      "POST",
      "/api/method/frappe.desk.doctype.workspace.workspace.save_page"
    ).as("saveClassicWorkspace");
    cy.get(".page-container:visible .primary-action")
      .should("be.visible")
      .click();
    cy.wait("@saveClassicWorkspace").then(({ request }) => {
      const body =
        typeof request.body === "string"
          ? Object.fromEntries(new URLSearchParams(request.body))
          : request.body;
      expect(JSON.parse(body.blocks).map((block) => block.type)).to.include(
        "custom_block"
      );
    });
    cy.get(".whitelabel-classic-tree").should("be.visible");
    cy.reload();
    cy.contains(CARD).should("be.visible");
    cy.contains("Classic workspace content is native", {
      includeShadowDom: true,
    }).should("be.visible");
  });

  it("restores the native sidebar when Classic mode is switched off", () => {
    update("Whitelabel Setting", "Whitelabel Setting", {
      desk_layout: "Standard",
    });
    cy.window().then((window) => window.whitelabel.navigation.refresh());
    cy.get("body").should("not.have.class", "whitelabel-classic");
    cy.get(".whitelabel-classic-tree").should("not.exist");
    cy.get(".sidebar-header").should("be.visible");
  });
});
