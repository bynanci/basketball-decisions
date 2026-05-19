import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function readPage(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('confidence helper text wiring', () => {
  it('defines role-aware confidence helper copy', () => {
    const component = readFileSync(resolve(__dirname, '../../components/ConfidenceHelp.vue'), 'utf-8')
    expect(component).toContain("variant: 'player' | 'coach' | 'analyst'")
    expect(component).toContain('Confidence estimates how complete and reliable the local evidence is for this score.')
    expect(component).toContain('It can decrease when sample size is low, player identity is UNKNOWN, attribution is ambiguous, artifacts are stale, or model/data baselines differ.')
    expect(component).toContain('Confidence shows how much local evidence supports this training signal. Low confidence means you should review warnings before acting on it.')
    expect(component).toContain('Use this with coach judgment and review warnings before acting.')
    expect(component).toContain('Compare confidence with warning context before interpreting score differences.')
  })

  it('renders confidence helper across first score views', () => {
    expect(readPage('PlayerValuePage.vue')).toContain('<ConfidenceHelp variant="analyst" compact />')
    expect(readPage('PlayerValueDetailPage.vue')).toContain('<ConfidenceHelp variant="analyst" compact />')
    expect(readPage('CoachReportsPage.vue')).toContain('<ConfidenceHelp v-if="currentReport" variant="coach" compact />')
    expect(readPage('PlayerValueTrendsPage.vue')).toContain('<ConfidenceHelp variant="analyst" compact />')
  })
})
