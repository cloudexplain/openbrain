describe('Application E2E Tests', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  it('should load the homepage', () => {
    cy.get('body').should('be.visible')
    cy.title().should('not.be.empty')
  })

  it('should display the main navigation', () => {
    cy.get('nav').should('be.visible')
  })

  it('should be responsive', () => {
    cy.viewport(375, 667) // Mobile
    cy.get('body').should('be.visible')

    cy.viewport(768, 1024) // Tablet
    cy.get('body').should('be.visible')

    cy.viewport(1280, 720) // Desktop
    cy.get('body').should('be.visible')
  })
})