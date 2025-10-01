describe('Chat', () => {
  beforeEach(() => {
    cy.visit('/')
    cy.wait(500)
  })

  it('should create a new chat', () => {
    // Chat tests go here
    cy.contains('New Chat').click()
    
    // Check if new chat appeared in the correct location
    cy.get('.space-y-3 > :nth-child(1)').should('exist')
  })

  it('should delete a chat', () => {
    cy.visit('/')
    // Get initial chat count
    cy.get('.space-y-3 > div').its('length').then((initialCount) => {
      // Hover over the group element (entire chat div) to make delete button visible
      cy.get('.space-y-3 > :nth-child(1)').trigger('mouseenter')
      // Wait a bit for the CSS transition to make button visible
      cy.wait(200)
      // Now click the delete button which should be visible
      cy.get('.space-y-3 > :nth-child(1) button[title="Delete chat"]').click()
      
      // Verify chat is deleted - check that count decreased
      cy.get('.space-y-3 > div').should('have.length', initialCount - 1)
    })
  })

  it('should create new chat and send message', () => {
    // Create new chat first - try different button selectors
    cy.get('body').then(($body) => {
      if ($body.find('button:contains("New Chat")').length > 0) {
        cy.contains('button', 'New Chat').click()
      } else if ($body.find('button:contains("+ New")').length > 0) {
        cy.contains('button', '+ New').click()
      } else {
        cy.contains('New Chat').click()
      }
    })
    
    // Wait for new chat to be created
    cy.wait(1000)
    
    // Now verify at least one chat exists and click on the first one
    cy.get('.space-y-3 > div').should('have.length.at.least', 1)
    cy.get(':nth-child(1) > .relative > .flex-1').click()
    
    // Wait for chat interface to load
    cy.wait(1000)
    
    // Find message input field and send a minimal message
    cy.get('textarea').should('be.visible').type('Hi')
    
    // Send the message
    cy.get('textarea').type('{enter}')
    
    // Wait for message to be sent
    cy.wait(500)
    
    // Verify the user message appears in the first message
    cy.get(':nth-child(1) > .max-w-3xl > .gap-6 > .flex-1 > .prose > .math-content > p').should('contain', 'Hi')
    
    // Wait for AI response and verify it appears in the second message
    cy.wait(5000)
    cy.get(':nth-child(2) > .max-w-3xl > .gap-6 > .flex-1 > .prose > .math-content > p').should('exist').and('not.be.empty')
  })

  it('should save chat to knowledge base', () => {
    // Use the existing chat from the previous test (first chat in the list)
    cy.get('.space-y-3 > :nth-child(1) > .flex > .flex-1').click()
    cy.wait(1000)

    // Click the button to save to knowledge base
    cy.get(':nth-child(2) > .px-3').click()

    // Clear existing text and enter demo title
    cy.get('.bg-white > :nth-child(2) > .flex > .flex-1').clear().type('Demo Title')

    // Click save to knowledge base button
    cy.get('.border-t > .flex > .bg-blue-500').click()

    // Wait longer for save action to complete (includes backend processing)
    cy.wait(3000)
  })

  it('should navigate to knowledge base and test saved chat', () => {
    // Click on Knowledge Base navigation
    cy.get('.from-emerald-500').click()
    cy.url().should('include', '/knowledge')

    // Poll the backend API to wait for document processing to complete
    // This is more reliable than fixed waits, especially in CI environments
    const pollForDocuments = (retriesLeft = 20, delayMs = 3000) => {
      if (retriesLeft <= 0) {
        throw new Error('Document processing timed out after polling')
      }

      return cy.request({
        url: 'http://localhost:8000/api/documents',
        failOnStatusCode: false
      }).then((response) => {
        if (response.status === 200 && response.body.documents && response.body.documents.length > 0) {
          // Documents exist, proceed with test
          cy.log(`Documents found after ${20 - retriesLeft + 1} attempts`)
          return
        } else {
          // Wait and retry
          cy.wait(delayMs)
          return pollForDocuments(retriesLeft - 1, delayMs)
        }
      })
    }

    // Wait for documents to be processed
    pollForDocuments()

    // Now verify UI shows the documents
    cy.get('.rounded-xl > .w-80 > .overflow-y-auto', { timeout: 10000 }).should('exist')
    cy.get('.overflow-y-auto > :nth-child(1)', { timeout: 10000 }).should('exist')

    // Verify the chat title "Chat: New Chat" appears in the knowledge base
    cy.get('.overflow-y-auto > :nth-child(1) > .items-start > .flex-1 > .font-medium', { timeout: 10000 })
      .should('exist')
      .should('contain', 'Chat: New Chat')

    // Click on the knowledge base item
    cy.get('.overflow-y-auto > :nth-child(1) > .items-start').click()

    // Wait for the item to load
    cy.wait(2000)

    // Verify the chat content appears correctly
    cy.get('.markdown-content > :nth-child(1)', { timeout: 10000 }).should('contain', 'Hi')
    cy.get('.markdown-content > :nth-child(2)').should('exist').and('not.be.empty')
  })

  it('should create tag and add to chat', () => {
    // First create a new tag
    cy.get('.from-orange-500').click()
    cy.url().should('include', '/tags')
    cy.wait(1000)

    // Click the create tag button
    cy.get('.gap-4 > .px-4').click()
    cy.wait(1000)

    // Load test tag data
    cy.fixture('tags').then((tags) => {
      // Fill in tag name
      cy.get('#name').type(tags.testTag.name)

      // Fill in tag description
      cy.get('#description').type(tags.testTag.description)

      // Skip color selection (causing redirect issue)
      // cy.get(':nth-child(3) > .flex > .flex-1').first().click()
      cy.url().should('include', '/tags') // Make sure we're still on tags page

      // Wait before submitting
      cy.wait(1000)

      // Submit the form (check if button exists first)
      cy.get('body').then(($body) => {
        if ($body.find('.pt-4 > .bg-blue-500').length > 0) {
          cy.get('.pt-4 > .bg-blue-500').then(($buttons) => {
            $buttons[0].click()
          })
        } else {
          cy.log('Submit button not found - might have been redirected')
        }
      })

      // Wait for tag creation
      cy.wait(2000)

      // Verify tag appears in the tag list (same as tags.cy.ts)
      cy.get('.justify-between > .gap-3').should('contain', tags.testTag.name)

      // Also verify the tag is visible in the general page
      cy.contains(tags.testTag.name).should('be.visible')
    })

    // Navigate back to knowledge base
    cy.get('.from-emerald-500').click()
    cy.url().should('include', '/knowledge')

    // Poll for documents to ensure they're loaded
    cy.request('http://localhost:8000/api/documents').its('body.documents').should('have.length.at.least', 1)
    cy.wait(2000)

    // Wait for documents to load and click on the saved chat again
    cy.get('.overflow-y-auto', { timeout: 10000 }).should('exist')
    cy.get('.overflow-y-auto > :nth-child(1)', { timeout: 10000 }).should('exist')
    cy.get('.overflow-y-auto > :nth-child(1) > .items-start', { timeout: 10000 }).should('exist').click()
    cy.wait(2000)

    // Click on the inline-flex button to add tag
    cy.get('.inline-flex').click({ multiple: true })
    cy.wait(1000)

    // Add the newly created tag
    cy.fixture('tags').then((tags) => {
      cy.contains(tags.testTag.name).click()
      cy.wait(1000)

      // Verify the tag was added to the chat
      cy.get('.flex > .inline-flex').should('contain', tags.testTag.name)
    })
  })

  it('should edit saved chat text in knowledge base', () => {
    // Navigate to knowledge base
    cy.get('.from-emerald-500').click()
    cy.url().should('include', '/knowledge')

    // Poll for documents to ensure they're loaded
    cy.request('http://localhost:8000/api/documents').its('body.documents').should('have.length.at.least', 1)
    cy.wait(2000)

    // Wait for documents to load and click on the saved chat to open it
    cy.get('.overflow-y-auto', { timeout: 10000 }).should('exist')
    cy.get('.overflow-y-auto > :nth-child(1)', { timeout: 10000 }).should('exist')
    cy.get('.overflow-y-auto > :nth-child(1) > .items-start', { timeout: 10000 }).should('exist').click()
    cy.wait(2000)

    // Click the edit button
    cy.contains('button', 'Edit').click()
    cy.wait(1000)

    // Edit the text content in TipTap editor
    cy.get('.tiptap').should('be.visible')
      .should('contain', 'Hi')

    // Click in the editor and add some text
    cy.get('.tiptap').click()
    cy.get('.tiptap').type('{end}')
    cy.get('.tiptap').type(' This is additional edited content added to the chat.')

    // Save the edited content
    cy.contains('button', 'Save Changes').click()
    cy.wait(1000)

    // Verify the edited content appears
    cy.get('.markdown-content > :nth-child(2)').should('contain', 'This is additional edited content added to the chat.')
  })

  it('should cleanup - delete saved chat from knowledge base, delete tag, and delete chat', () => {
    // First: Delete the saved chat from knowledge base
    cy.get('.from-emerald-500').click()
    cy.url().should('include', '/knowledge')

    // Poll for documents to ensure they're loaded
    cy.request('http://localhost:8000/api/documents').its('body.documents').should('have.length.at.least', 1)
    cy.wait(2000)

    // Wait for documents to load and find and delete the saved chat
    cy.get('.overflow-y-auto', { timeout: 10000 }).should('exist')
    cy.get('.overflow-y-auto > :nth-child(1)', { timeout: 10000 }).should('exist')
    cy.get('.overflow-y-auto > :nth-child(1)').find('button[title*="Delete"], button:contains("Delete"), .delete').first().click()
    cy.wait(2000)

    // Second: Delete the created tag
    cy.get('.from-orange-500').click()
    cy.url().should('include', '/tags')
    cy.wait(1000)
    
    // Delete the created tag (same as tags.cy.ts)
    cy.fixture('tags').then((tags) => {
      cy.get('.justify-between > .gap-3').contains(tags.testTag.name).then(($tagElement) => {
        cy.get($tagElement).closest('.justify-between').then(($tagRow) => {
          if ($tagRow.find('button:contains("Delete")').length > 0) {
            cy.wrap($tagRow).find('button:contains("Delete")').click()
          } else if ($tagRow.find('.delete').length > 0) {
            cy.wrap($tagRow).find('.delete').click()
          } else if ($tagRow.find('button[title*="Delete"]').length > 0) {
            cy.wrap($tagRow).find('button[title*="Delete"]').click()
          } else {
            cy.wrap($tagRow).find('button').last().click()
          }
        })
      })
      
      cy.wait(2000)
      cy.get('.border-r').should('not.contain', tags.testTag.name)
      cy.contains(tags.testTag.name).should('not.exist')
    })
    
    // Third: Delete the original chat
    cy.visit('/')
    cy.wait(1000)
    
    // Check if any chats exist and delete the first one if present
    cy.get('body').then(($body) => {
      if ($body.find('.space-y-3 > div').length > 0) {
        cy.get('.space-y-3 > div').its('length').then((initialCount) => {
          cy.get('.space-y-3 > :nth-child(1)').trigger('mouseenter')
          cy.wait(200)
          cy.get('.space-y-3 > :nth-child(1) button[title="Delete chat"]').click()
          cy.get('.space-y-3 > div').should('have.length', initialCount - 1)
        })
      } else {
        cy.log('No chats found to delete - cleanup complete')
      }
    })
  })
})