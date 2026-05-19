// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import TrustCaveatGate from './TrustCaveatGate.vue'

describe('TrustCaveatGate', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
  })

  it('shows caveat and persists acknowledgement to localStorage by default', async () => {
    const wrapper = mount(TrustCaveatGate, { props: { surface: 'player-value' } })
    expect(wrapper.text()).toContain('I understand')

    await wrapper.get('button').trigger('click')

    expect(window.localStorage.getItem('court-iq-trust-caveat:player-value')).toBe('1')
    expect(wrapper.text()).toContain('acknowledged')
    expect(wrapper.text()).toContain('Player Value is not an official scouting grade')
  })

  it('falls back to localStorage for compact mode and keeps badge visible on reload', async () => {
    const storageKey = 'trust-check'
    const wrapper = mount(TrustCaveatGate, { props: { surface: 'player-home', compact: true, storageKey, message: 'Training signal' } })
    await wrapper.get('button').trigger('click')
    expect(window.localStorage.getItem(`${storageKey}:player-home`)).toBe('1')

    const reopened = mount(TrustCaveatGate, { props: { surface: 'player-home', compact: true, storageKey, message: 'Training signal' } })
    expect(reopened.find('.trust-caveat-panel').exists()).toBe(false)
    expect(reopened.find('.link-button').exists()).toBe(true)
    expect(reopened.text()).toContain('Training signal')
  })

  it('keeps a visible compact badge with review link after acknowledgement', async () => {
    const wrapper = mount(TrustCaveatGate, { props: { surface: 'coach-reports', compact: true } })
    await wrapper.get('button').trigger('click')

    expect(wrapper.text()).toContain('acknowledged')
    expect(wrapper.text()).toContain('Review caveat')

    await wrapper.get('.link-button').trigger('click')
    expect(wrapper.text()).toContain('Hide details')
  })
})
