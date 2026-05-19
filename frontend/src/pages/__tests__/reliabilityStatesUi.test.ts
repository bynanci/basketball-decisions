import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function readPage(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('S14 reliability state coverage', () => {
  it('has development dashboard empty state with recovery action', () => {
    const page = readPage('DevelopmentDashboardPage.vue')
    expect(page).toContain('No blocking artifact follow-ups')
    expect(page).toContain('verify Artifact Map freshness')
    expect(page).toContain('Load sample or start project')
  })

  it('has player home empty state guidance', () => {
    const page = readPage('PlayerHomePage.vue')
    expect(page).toContain('No player context yet')
    expect(page).toContain('Load Sample Project')
    expect(page).toContain('no usable signal')
  })

  it('has coach reports api error state', () => {
    const page = readPage('CoachReportsPage.vue')
    expect(page).toContain('Coach reports API error')
    expect(page).toContain('ErrorState')
  })

  it('has drills empty recommendation state', () => {
    const page = readPage('DrillsPage.vue')
    expect(page).toContain('No drill recommendations yet')
    expect(page).toContain('Review practice plan options instead')
  })

  it('has practice plans no recommendations state', () => {
    const page = readPage('PracticePlansPage.vue')
    expect(page).toContain('No recommendations in this plan')
  })

  it('has workflows blocked-state recovery link', () => {
    const page = readPage('WorkflowsPage.vue')
    expect(page).toContain('Resolve blocked steps')
  })

  it('has review queue empty-state next-best-action guidance', () => {
    const page = readPage('ReviewQueuePage.vue')
    expect(page).toContain('Review Queue is empty')
    expect(page).toContain('Generate review queue')
    expect(page).toContain('Open Artifact Map')
  })

  it('has local lab missing-data guidance copy', () => {
    const page = readPage('LocalLabPage.vue')
    expect(page).toContain('No local projects found yet.')
    expect(page).toContain('dataset/export/model health states will remain low-signal')
  })
})
