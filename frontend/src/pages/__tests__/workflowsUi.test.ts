import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function readPage(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('guided workflow UI wiring', () => {
  it('renders workflow list and detail pages without auto-running operations', () => {
    const listPage = readPage('WorkflowsPage.vue')
    const detailPage = readPage('WorkflowDetailPage.vue')

    expect(listPage).toContain('apiClient.createWorkflow')
    expect(listPage).toContain('M27 Guided Workflow Orchestrator')
    expect(listPage).toContain('never execute underlying operations automatically')
    expect(detailPage).toContain('apiClient.refreshWorkflow')
    expect(detailPage).toContain('Prerequisite checks')
    expect(detailPage).toContain('Mark complete')
    expect(listPage).not.toContain('replaceAll')
    expect(detailPage).not.toContain('replaceAll')
  })

  it('adds routes, navigation, and dashboard start workflow integration', () => {
    const router = readFileSync(resolve(__dirname, '../../router/index.ts'), 'utf-8')
    const app = readFileSync(resolve(__dirname, '../../App.vue'), 'utf-8')
    const dashboard = readPage('DevelopmentDashboardPage.vue')
    const client = readFileSync(resolve(__dirname, '../../api/client.ts'), 'utf-8')

    expect(router).toContain('/workflows')
    expect(router).toContain('/workflows/:workflowId')
    expect(app).toContain('Workflows')
    expect(dashboard).toContain('startWorkflowFromAction')
    expect(client).toContain('/workflows/from-action')
  })
})
