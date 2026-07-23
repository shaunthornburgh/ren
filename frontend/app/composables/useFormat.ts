/** Formatting helpers for dates and prices, shared across pages. */
export function useFormat() {
  const formatDate = (iso: string): string =>
    new Date(iso).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })

  const formatDateTime = (iso: string): string =>
    new Date(iso).toLocaleString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })

  const formatTime = (iso: string): string =>
    new Date(iso).toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
    })

  const formatPrice = (value: number | string): string => {
    const n = typeof value === 'string' ? parseFloat(value) : value
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
    }).format(Number.isFinite(n) ? n : 0)
  }

  return { formatDate, formatDateTime, formatTime, formatPrice }
}
