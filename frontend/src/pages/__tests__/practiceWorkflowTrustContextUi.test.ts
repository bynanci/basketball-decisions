import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function readPage(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('practice/workflow trust context wiring', () => {
  it('shows compact trust caveat context on practice execution surfaces', () => {
    const practiceListPage = readPage('PracticeExecutionsPage.vue')
    const practiceDetailPage = readPage('PracticeExecutionDetailPage.vue')

    expect(practiceListPage).toContain('TrustCaveatGate')
    expect(practiceListPage).toContain('surface="practice-execution"')
    expect(practiceListPage).toContain('Practice feedback signals are decision-support cues')
    expect(practiceDetailPage).toContain('TrustCaveatGate')
    expect(practiceDetailPage).toContain('surface="practice-execution"')
  })

  it('shows compact trust caveat context on workflow surfaces and keeps warnings visible', () => {
    const workflowsPage = readPage('WorkflowsPage.vue')
    const workflowDetailPage = readPage('WorkflowDetailPage.vue')

    expect(workflowsPage).toContain('TrustCaveatGate')
    expect(workflowsPage).toContain('surface="workflow"')
    expect(workflowDetailPage).toContain('TrustCaveatGate')
    expect(workflowDetailPage).toContain('surface="workflow"')
    expect(workflowDetailPage).toContain('v-if="workflow.warnings.length"')
    expect(workflowDetailPage).toContain('Mark complete')
    expect(workflowDetailPage).toContain('Skip')
  })
})
