describe('Tags', () => {
  beforeEach(() => {
    cy.visit('/')
    cy.wait(500)
  })

  it("create and delete a tag", () => {
    // Open tags page
    cy.get('.from-orange-500').click()
    cy.url().should('include', '/tags')
    
    // Wait for page to load
    cy.wait(1000)
    
    // Set up network intercept for creating tag
    cy.intercept('POST', '**/tags').as('createTagRequest')
    
    // Click the create tag button
    cy.get('.gap-4 > .px-4').click()
    
    // Wait for modal to open
    cy.wait(1000)
    
    // Load test tag data
    cy.fixture('tags').then((tags) => {
      // Fill in tag name
      cy.get('#name').type(tags.testTag.name)
      
      // Fill in tag description
      cy.get('#description').type(tags.testTag.description)
      
      // Select tag color
      cy.get(':nth-child(3) > .flex > .flex-1').click()
      
      // Wait before submitting
      cy.wait(1000)
      
      // Submit the form
      cy.get('.pt-4 > .bg-blue-500').click()
      
      // Wait for tag creation
      cy.wait(2000)
      
      // Verify tag appears in the tag list
      cy.get('.justify-between > .gap-3').should('contain', tags.testTag.name)
      
      // Also verify the tag is visible in the general page
      cy.contains(tags.testTag.name).should('be.visible')
    })
    
    // Set up network intercept for deleting tag
    cy.intercept('DELETE', '**/tags/**').as('deleteTagRequest')
    
    // Delete the created tag
    cy.fixture('tags').then((tags) => {
      // Find the tag in the list and delete it
      cy.get('.justify-between > .gap-3').contains(tags.testTag.name).then(($tagElement) => {
        // Find delete button near the tag
        cy.get($tagElement).closest('.justify-between').then(($tagRow) => {
          if ($tagRow.find('button:contains("Delete")').length > 0) {
            cy.wrap($tagRow).find('button:contains("Delete")').click()
          } else if ($tagRow.find('.delete').length > 0) {
            cy.wrap($tagRow).find('.delete').click()
          } else if ($tagRow.find('button[title*="Delete"]').length > 0) {
            cy.wrap($tagRow).find('button[title*="Delete"]').click()
          } else {
            // Look for any button in the tag row as fallback
            cy.wrap($tagRow).find('button').last().click()
          }
        })
      })
      
      // Wait for deletion
      cy.wait(2000)
      
      // Verify it's not in the border-r container
      cy.get('.border-r').should('not.contain', tags.testTag.name)
      
      // Final verification that tag doesn't exist anywhere on the page
      cy.contains(tags.testTag.name).should('not.exist')
      
    })
  })

  it("search tags", () => {
    // Open tags page
    cy.get('.from-orange-500').click()
    cy.url().should('include', '/tags')
    
    // Wait for page to load
    cy.wait(1000)
    
    // Set up network intercept for creating tag
    cy.intercept('POST', '**/tags').as('createTagRequest')
    
    // Click the create tag button
    cy.get('.gap-4 > .px-4').click()
    
    // Wait for modal to open
    cy.wait(1000)
    
    // Load test tag data and create a tag first
    cy.fixture('tags').then((tags) => {
      // Fill in tag name
      cy.get('#name').type(tags.testTag.name)
      
      // Fill in tag description
      cy.get('#description').type(tags.testTag.description)
      
      // Select tag color
      cy.get(':nth-child(3) > .flex > .flex-1').click()
      
      // Wait before submitting
      cy.wait(1000)
      
      // Submit the form
      cy.get('.pt-4 > .bg-blue-500').click()
      
      // Wait for tag creation
      cy.wait(2000)
      
      // Verify tag appears in the tag list
      cy.get('.justify-between > .gap-3').should('contain', tags.testTag.name)
      
      // Test search functionality - search with similar name (should find the tag)
      cy.get('.w-full').type(tags.testTag.name.substring(0, 3)) // Search with first 3 characters
      cy.wait(1000)
      
      // Verify tag is still visible after search in the correct container
      cy.get('.divide-y > .p-4').should('contain', tags.testTag.name)
      
      // Clear search and test with non-existing tag name
      cy.get('.w-full').clear()
      cy.get('.w-full').type('NonExistingTag123')
      cy.wait(1000)
      
      // Verify no tags are shown when searching for non-existing name
      cy.get('.border-r').should('not.contain', tags.testTag.name)
      
      // Clear search to restore all tags
      cy.get('.w-full').clear()
      cy.wait(1000)
      
      // Verify tag is visible again after clearing search
      cy.get('.divide-y > .p-4').should('contain', tags.testTag.name)
    })
    
    // Set up network intercept for deleting tag
    cy.intercept('DELETE', '**/tags/**').as('deleteTagRequest')
    
    // Delete the created tag
    cy.fixture('tags').then((tags) => {
      // Find the tag in the list and delete it
      cy.get('.justify-between > .gap-3').contains(tags.testTag.name).then(($tagElement) => {
        // Find delete button near the tag
        cy.get($tagElement).closest('.justify-between').then(($tagRow) => {
          if ($tagRow.find('button:contains("Delete")').length > 0) {
            cy.wrap($tagRow).find('button:contains("Delete")').click()
          } else if ($tagRow.find('.delete').length > 0) {
            cy.wrap($tagRow).find('.delete').click()
          } else if ($tagRow.find('button[title*="Delete"]').length > 0) {
            cy.wrap($tagRow).find('button[title*="Delete"]').click()
          } else {
            // Look for any button in the tag row as fallback
            cy.wrap($tagRow).find('button').last().click()
          }
        })
      })
      
      // Wait for deletion
      cy.wait(2000)
      
      // Verify it's not in the border-r container
      cy.get('.border-r').should('not.contain', tags.testTag.name)
      
      // Final verification that tag doesn't exist anywhere on the page
      cy.contains(tags.testTag.name).should('not.exist')
    })
  })

  it("close tag management", () => {
    // Open tags page
    cy.get('.from-orange-500').click()
    cy.url().should('include', '/tags')
    
    // Wait for page to load
    cy.wait(1000)
    
    // Close the tag management with the close button
    cy.get('.py-4 > .flex > .p-2').click()
    
    // Wait for close action
    cy.wait(1000)
    
    // Verify we're back to the main page (not on tags page anymore)
    cy.url().should('not.include', '/tags')
  })

})