import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('review queue action UI wiring', () => {
  it('renders allowed actions, alias payload fields, and recent action logs', () => {
    const page = readFileSync(resolve(__dirname, '..', 'ReviewQueuePage.vue'), 'utf-8')

    expect(page).toContain('item.allowed_actions')
    expect(page).toContain('ASSIGN_TRACK_TO_PLAYER_ALIAS')
    expect(page).toContain('aliasPlayerKeys')
    expect(page).toContain('aliasTrackIds')
    expect(page).toContain('DISMISS_WITH_NOTE requires a note')
    expect(page).toContain('apiClient.performReviewAction')
    expect(page).toContain('Recent Review Actions')
  })
})
