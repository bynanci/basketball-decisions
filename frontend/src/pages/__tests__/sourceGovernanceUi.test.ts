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
})
