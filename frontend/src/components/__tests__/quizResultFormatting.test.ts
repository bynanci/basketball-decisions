import { describe, expect, it } from 'vitest'
import { formatResultNumber, formatScore } from '../quizResultFormatting'

describe('quiz result formatting', () => {
  it('avoids rendering NaN for missing or invalid numeric values', () => {
    expect(formatResultNumber(Number.NaN)).toBe('—')
    expect(formatResultNumber(null)).toBe('—')
    expect(formatScore(Number.NaN)).toBe('—')
  })

  it('formats finite score and expected-value numbers', () => {
    expect(formatResultNumber(0.361)).toBe('0.36')
    expect(formatScore(27.6)).toBe('28')
  })
})
