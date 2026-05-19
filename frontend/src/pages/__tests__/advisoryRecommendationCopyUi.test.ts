import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function page(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('advisory recommendation wording', () => {
  it('shows advisory helper copy near recommendation surfaces', () => {
    const helper = 'Recommendations are generated from available local evidence and should be reviewed by a coach or analyst before use.'
    expect(page('PlayerHomePage.vue')).toContain(helper)
    expect(page('DrillsPage.vue')).toContain(helper)
    expect(page('PracticePlansPage.vue')).toContain(helper)
    expect(page('CoachReportsPage.vue')).toContain(helper)
  })

  it('uses advisory wording on dashboard and workflow copy', () => {
    expect(page('DevelopmentDashboardPage.vue')).toContain('Recommended next steps (advisory)')
    expect(page('DevelopmentDashboardPage.vue')).toContain('Recommended next step: verify Artifact Map freshness before acting on downstream decisions.')
  })
})
