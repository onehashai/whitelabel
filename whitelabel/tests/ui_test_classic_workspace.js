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
const PICKER_PROFILE = "Classic Picker View";
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
const node = (name, parent) =>
  parent
    ? node(parent)
        .children(".whitelabel-tree-children")
        .children(`.whitelabel-tree-node[data-workspace="${name}"]`)
    : cy.get(`.whitelabel-tree-node[data-workspace="${name}"]`);
const link = (name, parent) =>
  node(name, parent)
    .children(".whitelabel-tree-row")
    .find(".whitelabel-tree-link");
const toggle = (name, parent) =>
  node(name, parent)
    .children(".whitelabel-tree-row")
    .find(".whitelabel-tree-toggle");
const openBranch = (name) =>
  node(name).then(($node) => {
    if ($node.attr("aria-expanded") !== "true") toggle(name).click();
  });

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
      workspaces: [
        { workspace: MANAGER },
        { workspace: CHILD, parent_workspace: MANAGER },
        { workspace: BOARD },
      ],
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
      ["Whitelabel Navigation Profile", PICKER_PROFILE],
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
    cy.get(".whitelabel-tree-section")
      .last()
      .children(".whitelabel-tree-node")
      .should(($nodes) => {
        expect([...$nodes].map((node) => node.dataset.workspace)).to.deep.eq([
          OPERATOR,
          MANAGER,
          BOARD,
        ]);
      });
    cy.get(".whitelabel-classic-tree")
      .should("not.contain.text", RESTRICTED)
      .and("not.contain.text", UNLISTED)
      .and("not.contain.text", "Core");
    cy.contains("Classic workspace content is native", {
      includeShadowDom: true,
    }).should("be.visible");
    cy.get("#whitelabel-navigation").should("not.exist");
    cy.get(
      ".whitelabel-tree-home, .whitelabel-tree-search, .whitelabel-tree-manage"
    ).should("not.exist");
    cy.get(".sidebar-header").click();
    cy.get(".frappe-menu:visible .menu-item-title").should(($items) => {
      const labels = [...$items].map((item) => item.textContent.trim());
      expect(labels).not.to.include("Workspaces");
      expect(labels).not.to.include("All Workspaces");
      expect(labels).to.include("Home");
      expect(labels).to.include("All Apps");
    });
    cy.get("body").type("{esc}");
    cy.screenshot("classic-workspace-desktop", { capture: "viewport" });
  });

  it("uses the available workspace width on wide screens and mobile without page overflow", () => {
    cy.login(USER, PASSWORD);
    cy.visit(route(OPERATOR));
    [1920, 1440, 1024, 390].forEach((width) => {
      cy.viewport(width, 900);
      cy.get('[data-page-route="Workspaces"]:visible .layout-main').should(
        ($layout) => {
          const document = $layout[0].ownerDocument;
          const main = document.querySelector(".main-section");
          const bounds = $layout[0].getBoundingClientRect();
          expect(bounds.width, `workspace width at ${width}px`).to.be.at.least(
            main.clientWidth - 2
          );
          expect(
            bounds.left - main.getBoundingClientRect().left,
            "left gutter"
          ).to.be.within(0, 2);
          expect(main.scrollWidth, "no horizontal page overflow").to.be.at.most(
            main.clientWidth + 1
          );
        }
      );
      cy.get(".custom-block-widget-box:visible").should(($block) => {
        const main = $block[0].ownerDocument.querySelector(".main-section");
        expect(
          $block[0].getBoundingClientRect().width,
          "full-column custom block"
        ).to.be.at.least(main.clientWidth - 64);
      });
    });
    cy.viewport(1400, 960);
  });

  it("expands without navigation and remembers the selected branch", () => {
    cy.login(USER, PASSWORD);
    cy.visit(route(OPERATOR));
    link(CHILD, OPERATOR).should("not.be.visible");
    toggle(OPERATOR).click();
    cy.location("pathname").should("eq", route(OPERATOR));
    link(CHILD, OPERATOR).should("be.visible");
    toggle(CHILD, OPERATOR).click();
    link(GRANDCHILD).should("be.visible").click();
    cy.location("pathname").should("eq", route(GRANDCHILD));
    link(GRANDCHILD).should("have.attr", "aria-current", "page");
    cy.reload();
    link(GRANDCHILD).should("be.visible");
    link(OPERATOR).click();
    cy.location("pathname").should("eq", route(OPERATOR));
    link(CHILD, OPERATOR).should("be.visible");
  });

  it("shows a shared workspace under both parents and retains the chosen branch", () => {
    cy.login(USER, PASSWORD);
    cy.visit(route(OPERATOR));
    openBranch(OPERATOR);
    openBranch(MANAGER);
    link(CHILD, OPERATOR).should("be.visible");
    link(CHILD, MANAGER).should("be.visible").click();
    cy.location("pathname").should("eq", route(CHILD));
    cy.location("search").should("contain", "navigation_path=");
    let managerPath;
    cy.location("search").then((search) => {
      managerPath = search;
    });
    link(CHILD, MANAGER).should("have.attr", "aria-current", "page");
    cy.window().should((window) => {
      expect(window.frappe.route_options?.navigation_path).to.eq(undefined);
    });
    link(CHILD, OPERATOR).should("not.have.attr", "aria-current");
    cy.reload();
    link(CHILD, MANAGER)
      .should("be.visible")
      .and("have.attr", "aria-current", "page");
    openBranch(OPERATOR);
    link(CHILD, OPERATOR).click();
    cy.location("search").should((search) =>
      expect(search).not.to.eq(managerPath)
    );
    link(CHILD, OPERATOR).should("have.attr", "aria-current", "page");
    cy.go("back");
    cy.location("search").should((search) => expect(search).to.eq(managerPath));
    link(CHILD, MANAGER).should("have.attr", "aria-current", "page");
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
    cy.window().then(
      (window) =>
        new Cypress.Promise((resolve) => window.frappe.after_ajax(resolve))
    );
    cy.window().then((window) => window.frappe.workspace.editor.isReady);
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

  it("lets a manager choose Home before adding workspace rows", () => {
    cy.window().then((window) =>
      window.frappe.new_doc("Whitelabel Navigation Profile")
    );
    cy.get('.frappe-control[data-fieldname="title"] input').type(
      PICKER_PROFILE
    );
    cy.get('.frappe-control[data-fieldname="default_workspace"] input').type(
      OPERATOR
    );
    cy.contains('.awesomplete [role="option"]:visible', OPERATOR).click();
    cy.window().should((window) => {
      expect(window.cur_frm.doc.default_workspace).to.eq(OPERATOR);
      expect(
        window.cur_frm.doc.workspaces.map((row) => row.workspace)
      ).to.deep.eq([OPERATOR]);
    });
    cy.get(".page-container:visible .primary-action").click();
    cy.window().should((window) =>
      expect(window.cur_frm.is_dirty()).to.eq(false)
    );
  });

  it("finds settings and navigation profiles through Ctrl+K aliases", () => {
    cy.window().then((window) => {
      // Reproduce a blocked Whitelabel module: the native doctype search list
      // no longer advertises the app's management doctypes.
      window.frappe.boot.user.can_read =
        window.frappe.boot.user.can_read.filter(
          (name) => !name.startsWith("Whitelabel")
        );
    });
    cy.get("#navbar-modal-search").click();
    cy.get("#navbar-search:visible").type("whitelabel settings");
    cy.contains(".modal:visible .awesomplete li", "Brand Settings").click();
    cy.window().should((window) =>
      expect(window.cur_frm?.doctype).to.eq("Whitelabel Setting")
    );
    cy.window().should((window) => {
      const results = window.frappe.search.utils.get_doctypes(
        "navigation profiles"
      );
      expect(
        results.some(
          (entry) => entry.route?.[1] === "Whitelabel Navigation Profile"
        )
      ).to.eq(true);
    });
    cy.get("#navbar-modal-search").click();
    cy.get("#navbar-search:visible").type("brand settings");
    cy.contains(".modal:visible .awesomplete li", "Brand Settings").should(
      "be.visible"
    );
    cy.get("#navbar-search:visible").type("{esc}");
    cy.get(".modal:visible").should("not.exist");
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
