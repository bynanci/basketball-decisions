import { describe, expect, it } from 'vitest'
import { normalizeApiErrorPayload } from '../client'

describe('normalizeApiErrorPayload', () => {
  it('keeps typed API errors intact', () => {
    expect(normalizeApiErrorPayload(404, { code: 'PROJECT_NOT_FOUND', message: 'Missing', details: { project_id: 'x' }, debug_hint: 'Create it first.' })).toEqual({
      code: 'PROJECT_NOT_FOUND',
      message: 'Missing',
      details: { project_id: 'x' },
      debug_hint: 'Create it first.'
    })
  })

  it('fills defaults when response body is not a typed API error', () => {
    expect(normalizeApiErrorPayload(500, null)).toEqual({
      code: 'HTTP_ERROR',
      message: 'API request failed with status 500',
      details: {},
      debug_hint: null
    })
  })
})
