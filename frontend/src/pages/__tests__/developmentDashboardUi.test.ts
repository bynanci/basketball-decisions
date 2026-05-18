import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function readPage(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('development dashboard UI wiring', () => {
  it('renders the M26 dashboard sections and API call', () => {
    const page = readPage('DevelopmentDashboardPage.vue')

    expect(page).toContain('apiClient.getDevelopmentDashboard()')
    expect(page).toContain('Development Progress Dashboard')
    expect(page).toContain('Next-best-actions')
    expect(page).toContain('Team Summary')
    expect(page).toContain('Player Development Table')
    expect(page).toContain('Practice Feedback Summary')
    expect(page).toContain('Data / Model Health Summary')
    expect(page).toContain('not an official scouting-grade evaluation')
  })

  it('adds route and navigation link', () => {
    const router = readFileSync(resolve(__dirname, '../../router/index.ts'), 'utf-8')
    const app = readFileSync(resolve(__dirname, '../../App.vue'), 'utf-8')

    expect(router).toContain('/development-dashboard')
    expect(router).toContain('DevelopmentDashboardPage')
    expect(app).toContain('Development Dashboard')
  })
})
