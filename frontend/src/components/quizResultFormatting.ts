export function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

export function formatResultNumber(value: number | null | undefined, digits = 2) {
  return isFiniteNumber(value) ? value.toFixed(digits) : '—'
}

export function formatScore(value: number | null | undefined) {
  return isFiniteNumber(value) ? String(Math.max(0, Math.min(100, Math.round(value)))) : '—'
}
