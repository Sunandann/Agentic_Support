import { STATUS } from '../format.js'

export function StatusBadge({ status }) {
  const s = STATUS[status] || STATUS.open
  return <span className={`inline-block whitespace-nowrap rounded-sm border px-2 py-0.5 text-xs font-semibold ${s.cls}`}>{s.text}</span>
}

/** Escalation gauge: where the score X sits against the threshold tau (paper Eq. 5-6). */
export function Gauge({ score, tau = 0.5, compact = false }) {
  if (score == null) return <span className="text-ink-faint">–</span>
  const x = Math.min(1, Math.max(0, score)) * 100
  const t = tau * 100
  const over = score > tau
  const clampedX = Math.min(100, Math.max(0, x))
  const clampedT = Math.min(100, Math.max(0, t))
  return (
    <div className={compact ? 'w-28' : 'w-full'} role="img"
         aria-label={`Escalation score ${score.toFixed(2)}, handoff threshold ${tau.toFixed(2)}, ${over ? 'above threshold: handed to a human' : 'below threshold: safe to answer'}`}>
      <div className="relative h-2 overflow-visible rounded-full bg-line">
        <div className="absolute inset-y-0 left-0 rounded-l-full bg-signal-tint" style={{ width: `${clampedT}%` }} />
        <div className="absolute inset-y-0 right-0 rounded-r-full bg-flag-tint" style={{ width: `${100 - clampedT}%` }} />
        <div className="absolute -top-1 h-4 w-px bg-ink" style={{ left: `${clampedT}%` }} />
        <div className={`absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface ${over ? 'bg-flag' : 'bg-signal'}`}
             style={{ left: `${clampedX}%` }} />
      </div>
      {!compact && (
        <div className="mt-1.5 flex justify-between font-mono text-xs text-ink-soft">
          <span>0</span><span>handoff threshold {tau.toFixed(2)}</span><span>1</span>
        </div>
      )}
    </div>
  )
}

export function Meter({ value, tone = 'ink' }) {
  const numeric = Number.isFinite(value) ? value : 0
  const v = Math.min(100, Math.max(0, Math.round(numeric * 100)))
  const color = tone === 'flag' ? 'bg-flag' : tone === 'signal' ? 'bg-signal' : 'bg-ink'
  return (
    <div className="h-1.5 w-16 rounded-full bg-line" aria-hidden="true">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${v}%` }} />
    </div>
  )
}

export function Empty({ title, children }) {
  return (
    <div className="px-6 py-14 text-center">
      <p className="font-semibold">{title}</p>
      <p className="mx-auto mt-1 max-w-sm text-sm text-ink-soft">{children}</p>
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-md bg-line/80 ${className}`} aria-hidden="true" />
}
