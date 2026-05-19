import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('review queue action UI wiring', () => {
  it('renders multi-select and batch-safe action affordances', () => {
    const page = readFileSync(resolve(__dirname, '..', 'ReviewQueuePage.vue'), 'utf-8')

    expect(page).toContain('selectedItemIds')
    expect(page).toContain('batchSafeActions')
    expect(page).toContain('DISMISS_WITH_NOTE')
    expect(page).not.toContain('UPDATE_PROMPT_EXPECTED_VALUE\'')
    expect(page).toContain('batch-confirmation-modal')
    expect(page).toContain('batch-partial-summary')
    expect(page).toContain('apiClient.performReviewBatchAction')
  })
})
