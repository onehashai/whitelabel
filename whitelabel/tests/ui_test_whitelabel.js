const UPSTREAM_TEXT =
  /\b(Frappe Framework|Frappe Support|ERPNext|Whitelabel)\b/i;
const UPSTREAM_DESTINATION =
  /(?:docs\.(?:frappe|erpnext)|discuss\.frappe|support\.frappe|frappecloud|github\.com\/frappe)/i;

function assertVisibleBranding() {
  cy.document().should((document) => {
    const visibleText = [...document.body.querySelectorAll("*")]
      .filter((element) => Cypress.$(element).is(":visible"))
      .flatMap((element) => [...element.childNodes])
      .filter((node) => node.nodeType === Node.TEXT_NODE)
      .map((node) => node.textContent)
      .join(" ");
    const visibleLabels = [
      ...document.querySelectorAll("[title], [aria-label], [placeholder]"),
    ]
      .filter((element) => Cypress.$(element).is(":visible"))
      .flatMap((element) => [
        element.getAttribute("title"),
        element.getAttribute("aria-label"),
        element.getAttribute("placeholder"),
      ])
      .filter(Boolean)
      .join(" ");

    expect(`${visibleText} ${visibleLabels}`).not.to.match(UPSTREAM_TEXT);
  });
  cy.get("a:visible").each(($link) => {
    expect($link.attr("href") || "").not.to.match(UPSTREAM_DESTINATION);
  });
}

describe("Whitelabel visible product surfaces", () => {
  it("brands the guest login page", () => {
    cy.visit("/login");
    cy.title().should("eq", "Login to OneHash");
    cy.get('img[src*="/assets/whitelabel/images/whitelabel_logo.svg"]').should(
      "be.visible"
    );
    assertVisibleBranding();
  });

  it("brands Desk and removes upstream menus", () => {
    cy.login("Administrator", Cypress.env("adminPassword") || "admin");
    cy.visit("/desk");
    cy.window()
      .its("frappe.boot.whitelabel_setting.brand_name")
      .should("eq", "OneHash");
    assertVisibleBranding();

    cy.get(".desktop-avatar:visible, .avatar-frame:visible").first().click();
    cy.get(".frappe-menu:visible").should("not.contain.text", "About");
    cy.get(".frappe-menu:visible").should("not.contain.text", "Frappe Support");
  });
});
