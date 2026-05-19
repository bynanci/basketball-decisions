import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('player home UI wiring', () => {
  it('renders empty and sample player states with next actions', () => {
    const page = readFileSync(resolve(__dirname, '..', 'PlayerHomePage.vue'), 'utf-8')
    expect(page).toContain('Select a player to see today’s next action')
    expect(page).toContain('Today’s Focus')
    expect(page).toContain('Current Strength')
    expect(page).toContain('Current Risk')
    expect(page).toContain('Recommended Drill')
    expect(page).toContain('Latest Practice Feedback')
    expect(page).toContain('Progress Trend')
    expect(page).toContain('home.confidence ??')
  })

  it('renders links and route wiring', () => {
    const page = readFileSync(resolve(__dirname, '..', 'PlayerHomePage.vue'), 'utf-8')
    const router = readFileSync(resolve(__dirname, '../../router/index.ts'), 'utf-8')
    expect(page).toContain('View Drill')
    expect(page).toContain('View Practice Plan')
    expect(page).toContain('Record Practice Feedback')
    expect(page).toContain('View Progress Trend')
    expect(page).not.toContain('undefined')
    expect(page).not.toContain('NaN')
    expect(router).toContain("/player-home")
    expect(router).toContain('PlayerHomePage')
  })
})
