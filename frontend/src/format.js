export const pct = (v) => (v == null ? '–' : `${Math.round(v * 100)}%`)

export function duration(sec) {
  if (sec == null) return '–'
  if (sec < 1) return `${Math.round(sec * 1000)} ms`
  if (sec < 60) return `${sec.toFixed(1)} s`
  if (sec < 3600) return `${Math.round(sec / 60)} min`
  return `${(sec / 3600).toFixed(1)} h`
}

export function ago(iso) {
  if (!iso) return ''
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return `${Math.floor(s / 86400)} d ago`
}

export const CATEGORY_LABEL = {
  account_security: 'Account security', billing: 'Billing', returns_refunds: 'Returns & refunds',
  shipping: 'Shipping', technical: 'Technical', account_management: 'Account changes', general: 'General',
}
export const label = (c) => CATEGORY_LABEL[c] || c || 'Unclassified'

export const STATUS = {
  open: { text: 'Queued', cls: 'bg-paper text-ink-soft border-line' },
  in_progress: { text: 'Working', cls: 'bg-paper text-ink-soft border-line' },
  auto_resolved: { text: 'Answered by AI', cls: 'bg-signal-tint text-signal border-signal/30' },
  escalated: { text: 'Needs a human', cls: 'bg-flag-tint text-flag border-flag/30' },
  resolved: { text: 'Closed by team', cls: 'bg-done-tint text-done border-done/30' },
}
