describe('Chat Message Deletion', () => {
  beforeEach(() => {
    cy.visit('/')
    cy.wait(500)
  })
  
  it('should create chat, send message, delete assistant response, then delete chat', () => {
    // Create new chat first
    cy.contains('New Chat').click()
    cy.wait(1000)
    
    // Verify at least one chat exists and click on the first one
    cy.get('.space-y-3 > div').should('have.length.at.least', 1)
    cy.get(':nth-child(1) > .relative > .flex-1').click()
    
    // Wait for chat interface to load
    cy.wait(1000)
    
    // Send "Hi" message
    cy.get('textarea').should('be.visible').type('Hi')
    cy.get('textarea').type('{enter}')
    
    // Wait for message to be sent
    cy.wait(500)
    
    // Verify the user message appears
    cy.get(':nth-child(1) > .max-w-3xl > .gap-6 > .flex-1 > .prose > .math-content > p').should('contain', 'Hi')
    
    // Wait for AI response
    cy.wait(5000)
    cy.get(':nth-child(2) > .max-w-3xl > .gap-6 > .flex-1 > .prose > .math-content > p').should('exist').and('not.be.empty')
    
    // Delete the assistant response by hovering over the message block and clicking delete button
    cy.get(':nth-child(2) > .max-w-3xl').trigger('mouseenter')
    cy.wait(200)
    
    // Click the delete button that becomes visible on hover
    cy.get(':nth-child(2) > .max-w-3xl > .gap-6 > .flex-1 > .mt-4 > .text-red-600').click()
    
    // Wait for popup to appear
    cy.wait(1000)
    
    // Click the "Delete Message" button in the confirmation popup
    cy.contains('button', 'Delete Message').click()
    
    // Wait for deletion to process
    cy.wait(2000)
    
    // Verify the assistant response is gone - check in the correct message container
    cy.get('.flex-1.flex-col > .flex-col > .overflow-y-auto').within(() => {
      // Should only have the "You" message left
      cy.get('div').should('contain', 'You')
      cy.get('div').should('contain', 'Hi')
      // Verify no assistant message exists
      cy.get('div').should('not.contain', 'Assistant')
    })
    
    // Now delete the entire chat
    cy.visit('/')
    cy.wait(1000)
    
    // Get chat count and delete the first chat
    cy.get('.space-y-3 > div').its('length').then((initialCount) => {
      // Hover over the chat to make delete button visible
      cy.get('.space-y-3 > :nth-child(1)').trigger('mouseenter')
      cy.wait(200)
      // Click the delete chat button
      cy.get('.space-y-3 > :nth-child(1) button[title="Delete chat"]').click()
      
      // Verify chat is deleted
      cy.get('.space-y-3 > div').should('have.length', initialCount - 1)
    })
  })
})