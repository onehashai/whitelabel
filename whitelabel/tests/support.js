Cypress.Commands.add("login", (email = "Administrator", password) => {
  return cy.session([email, password], () => {
    cy.request({
      method: "POST",
      url: "/api/method/login",
      body: {
        usr: email,
        pwd: password || Cypress.env("adminPassword"),
      },
    });
  });
});

// Third-party integrations can throw asynchronously without changing branding.
Cypress.on("uncaught:exception", () => false);
