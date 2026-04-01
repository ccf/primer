export function parseApiUtcDate(value: string): Date {
  if (/[zZ]$|[+-]\d{2}:\d{2}$/.test(value)) {
    return new Date(value)
  }
  return new Date(`${value}Z`)
}
