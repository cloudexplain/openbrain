import { defineConfig } from 'cypress'
import { viteDevServer } from '@cypress/vite-dev-server'
import path from 'path'

export default defineConfig({
  component: {
    devServer: (devServerConfig) => {
      return viteDevServer({
        ...devServerConfig,
        viteConfig: {
          resolve: {
            alias: {
              $lib: path.resolve(__dirname, './src/lib'),
              '$lib/*': path.resolve(__dirname, './src/lib/*')
            }
          }
        }
      })
    },
    specPattern: 'src/**/*.cy.{js,ts,jsx,tsx}',
    supportFile: 'cypress/support/component.ts'
  },
  e2e: {
    baseUrl: process.env.CYPRESS_baseUrl || 'http://localhost:3000',
    specPattern: 'cypress/e2e/**/*.cy.{js,ts}',
    supportFile: 'cypress/support/e2e.ts',
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    video: false,
    screenshotOnRunFailure: true,
    viewportWidth: 1280,
    viewportHeight: 720,
    // Wait for server to be ready
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 30000
  },
  retries: {
    runMode: 2,
    openMode: 0
  }
})