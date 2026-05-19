import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

function readPage(name: string) {
  return readFileSync(resolve(__dirname, '..', name), 'utf-8')
}

describe('trust caveat gate placement and copy', () => {
  it('uses required caveat copy on high-stakes interpretation surfaces', () => {
    const requiredCopy = 'Court IQ outputs are decision-support signals based on local sample data, aliases, decision events, rules, and available evidence. Player Value is not an official scouting grade. Review confidence, warnings, and evidence before using recommendations.'

    expect(readPage('PlayerValuePage.vue')).toContain(requiredCopy)
    expect(readPage('CoachReportsPage.vue')).toContain(requiredCopy)
    expect(readPage('DrillsPage.vue')).toContain(requiredCopy)
    expect(readPage('PracticePlansPage.vue')).toContain(requiredCopy)
  })

  it('uses player-friendly caveat copy on Player Home near score context', () => {
    const playerFriendlyCopy = 'This score is a training signal, not a final grade. Use it with the confidence and warnings shown here.'
    const page = readPage('PlayerHomePage.vue')

    expect(page).toContain('<TrustCaveatGate')
    expect(page).toContain('surface="player-home"')
    expect(page).toContain(playerFriendlyCopy)
    expect(page).toContain('<h2>Today’s Focus</h2>')
    expect(page).toContain('<h2>Confidence</h2>')
  })
})
