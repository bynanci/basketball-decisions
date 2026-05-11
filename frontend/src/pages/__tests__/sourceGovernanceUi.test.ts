import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function readPage(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('source governance UI wiring', () => {
  it('renders editable source governance fields on the project page', () => {
    const projectPage = readPage('ProjectPage.vue')

    expect(projectPage).toContain('Source Governance')
    expect(projectPage).toContain('sourceForm.license_type')
    expect(projectPage).toContain('sourceForm.rights_confirmed')
    expect(projectPage).toContain('sourceForm.allowed_for_training')
    expect(projectPage).toContain('sourceForm.allowed_for_local_storage')
    expect(projectPage).toContain('sourceForm.usage_scope')
    expect(projectPage).toContain('sourceForm.league_tag')
    expect(projectPage).toContain('sourceForm.notes')
  })

  it('displays training eligibility columns on the Local Lab project table', () => {
    const localLabPage = readPage('LocalLabPage.vue')

    expect(localLabPage).toContain('<th>License</th>')
    expect(localLabPage).toContain('<th>Usage</th>')
    expect(localLabPage).toContain('<th>Training</th>')
    expect(localLabPage).toContain('<th>League</th>')
    expect(localLabPage).toContain('allowed_for_training')
    expect(localLabPage).toContain('Reference only')
  })

  it('surfaces dataset curation controls and imbalance warnings', () => {
    const localLabPage = readPage('LocalLabPage.vue')

    expect(localLabPage).toContain('Curate Recognition Dataset')
    expect(localLabPage).toContain('Curate Decision Dataset')
    expect(localLabPage).toContain('positive_sample_count')
    expect(localLabPage).toContain('negative_sample_count')
    expect(localLabPage).toContain('Negative samples are under 20% of curated labels')
    expect(localLabPage).toContain('Positive/negative sample imbalance is greater than 5:1')
  })

  it('renders dataset health readiness when the health API returns data', () => {
    const localLabPage = readPage('LocalLabPage.vue')

    expect(localLabPage).toContain('apiClient.getDatasetHealth()')
    expect(localLabPage).toContain('Dataset Health')
    expect(localLabPage).toContain('Pre-training readiness gate')
    expect(localLabPage).toContain('Ready for baseline training')
    expect(localLabPage).toContain('Needs more labels')
    expect(localLabPage).toContain('Needs more negative samples')
    expect(localLabPage).toContain('Needs better role coverage')
    expect(localLabPage).toContain('datasetHealth.recognition.warnings')
    expect(localLabPage).toContain('datasetHealth.decision.warnings')
    expect(localLabPage).toContain('severity-badge')
  })
})

describe('player value evidence UI wiring', () => {
  it('links Player Value rows to the detail evidence route', () => {
    const playerValuePage = readPage('PlayerValuePage.vue')

    expect(playerValuePage).toContain('View Evidence')
    expect(playerValuePage).toContain("name: 'player-value-detail'")
    expect(playerValuePage).toContain('projectId: summary.project_id')
    expect(playerValuePage).toContain('playerKey: summary.player_key')
  })

  it('renders the evidence dashboard tables, warnings, and source/context track explanation', () => {
    const detailPage = readPage('PlayerValueDetailPage.vue')

    expect(detailPage).toContain('source_track_ids are identity-bearing. context_track_ids are frame context only.')
    expect(detailPage).toContain('Role Breakdown')
    expect(detailPage).toContain('Situation Breakdown')
    expect(detailPage).toContain('Decision Event Evidence')
    expect(detailPage).toContain('Evidence Warning Panel')
    expect(detailPage).toContain('No decision event evidence was found for this summary.')
    expect(detailPage).toContain('formatNumber(value?: number | null')
  })
})
