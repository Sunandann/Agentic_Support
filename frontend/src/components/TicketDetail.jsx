import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ago, label } from '../format.js'
import { Gauge, StatusBadge } from './ui.jsx'

const AGENT_NAME = { triage: 'Triage', retrieval: 'Retrieval', resolution: 'Resolution', escalation: 'Escalation', finalize: 'Decision', orchestrator: 'Orchestrator' }

function Block({ title, children }) {
  return (
    <section className="border-t border-line px-6 py-5">
      <h3 className="mb-3 text-sm font-semibold text-ink">{title}</h3>
      {children}
    </section>
  )
}

function Factor({ name, value, hint }) {
  return (
    <div>
      <dt className="text-xs text-ink-soft">{name}</dt>
      <dd className="font-mono text-lg text-ink">{value == null ? '–' : value.toFixed(2)}</dd>
      <p className="text-xs text-ink-faint">{hint}</p>
    </div>
  )
}

export default function TicketDetail({ id, tau, onClose, onChanged }) {
  const [t, setT] = useState(null)
  const [error, setError] = useState('')
  const [text, setText] = useState('')
  const [justified, setJustified] = useState(true)
  const [addKb, setAddKb] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let ignore = false
    api.ticket(id).then((data) => {
      if (!ignore) setT(data)
    }).catch((e) => {
      if (!ignore) setError(e.message)
    })
    return () => { ignore = true }
  }, [id])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function resolve() {
    if (text.trim().length < 3) {
      setError('Add a short customer-facing resolution before closing this ticket.')
      return
    }

    setBusy(true); setError('')
    try {
      const updated = await api.resolve(id, { resolution: text, escalation_justified: justified, add_to_kb: addKb })
      setT(updated); onChanged()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  const evidenceCats = t?.evidence?.map((e) => e.category) || []
  return (
    <div className="fixed inset-0 z-30 flex justify-end bg-ink/40" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label={`Ticket ${id}`} onClick={(e) => e.stopPropagation()}
             className="h-full w-full max-w-2xl overflow-y-auto bg-surface shadow-2xl">
        <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-line bg-surface px-6 py-4">
          <div>
            <p className="font-mono text-xs text-ink-soft">Ticket #{id}</p>
            <h2 className="text-lg font-semibold text-ink">{t?.subject || 'No subject'}</h2>
            {t && <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink-soft"><StatusBadge status={t.status} /><span>{label(t.category)}</span><span>via {t.channel}</span><span>{ago(t.created_at)}</span></p>}
          </div>
          <button className="btn-quiet" onClick={onClose} aria-label="Close ticket">Close</button>
        </header>

        {!t && !error && <p className="p-6 text-ink-soft">Loading…</p>}
        {error && <p role="alert" className="px-6 py-4 text-sm text-flag">{error}</p>}

        {t && (<>
          <Block title="Customer message"><p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">{t.body}</p></Block>

          <Block title={t.decision === 'escalate' ? 'Why a human is needed' : 'Why the AI answered'}>
            <Gauge score={t.escalation_score} tau={tau} />
            <p className="mt-3 text-sm text-ink-soft"><span className="font-semibold text-ink">Rule applied: </span>{t.decision_rule}</p>
            <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Factor name="Confidence" value={t.confidence} hint="retrieval strength and agreement" />
              <Factor name="Complexity" value={t.complexity} hint="evidence conflict, urgency, scope" />
              <Factor name="Urgency" value={t.urgency} hint="from the ticket wording" />
              <Factor name="Sentiment" value={t.sentiment} hint="−1 angry to +1 happy" />
            </dl>
          </Block>

          <Block title={t.status === 'escalated' ? 'Draft reply (not sent)' : t.status === 'resolved' ? 'Original AI draft (not sent)' : 'Reply sent to the customer'}>
            <pre className="whitespace-pre-wrap rounded-md bg-paper p-4 font-sans text-sm leading-relaxed text-ink">{t.reply}</pre>
            {t.action && (
              <p className="mt-3 text-sm text-ink-soft">
                <span className="font-semibold text-ink">Routine action: </span>{t.action.replace('_', ' ')} — {t.action_result?.executed
                  ? <span className="text-signal">{t.action_result.detail} ({t.action_result.reference})</span>
                  : <span>not run{t.action_result?.reason ? `: ${t.action_result.reason}` : ''}</span>}
              </p>
            )}
          </Block>

          {t.status === 'escalated' && (
            <Block title="Resolve as a team member">
              <label htmlFor="resolution" className="mb-1 block text-sm font-medium text-ink">Your answer to the customer</label>
              <textarea id="resolution" rows={4} className="field resize-none" value={text} onChange={(e) => setText(e.target.value)} placeholder="Write the final resolution. It is saved with the ticket." />
              <div className="mt-3 space-y-2 text-sm text-ink-soft">
                <label className="flex items-center gap-2"><input type="checkbox" checked={justified} onChange={(e) => setJustified(e.target.checked)} />This ticket really needed a human <span className="text-ink-faint">(feeds escalation precision)</span></label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={addKb} onChange={(e) => setAddKb(e.target.checked)} />Add this answer to the knowledge base</label>
              </div>
              <button className="btn-primary mt-4" onClick={resolve} disabled={busy || text.trim().length < 3}>{busy ? 'Saving…' : 'Close ticket'}</button>
            </Block>
          )}
          {t.human_resolution && <Block title="Team resolution"><p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-soft">{t.human_resolution}</p></Block>}

          <Block title={`Evidence used (${t.evidence?.length || 0})`}>
            {t.evidence?.length ? (
              <ul className="space-y-3">
                {t.evidence.map((e) => (
                  <li key={e.id} className="rounded-md border border-line p-3 text-sm">
                    <div className="flex items-baseline justify-between gap-3"><span className="font-semibold text-ink">{e.title}</span><span className="font-mono text-xs text-ink-soft">cos {e.score.toFixed(2)}</span></div>
                    <p className="mt-1 text-ink-soft">{e.content}</p>
                    <p className="mt-1.5 text-xs text-ink-faint">{label(e.category)} · {e.source === 'resolution' ? 'past resolution' : e.source === 'doc' ? 'documentation' : 'FAQ'}</p>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-ink-soft">No supporting passages were found, so the ticket went straight to a human.</p>}
            {evidenceCats.length > 1 && new Set(evidenceCats).size > 1 && <p className="mt-3 text-sm text-ink-soft">The passages come from different topics, which raises the complexity score.</p>}
          </Block>

          <Block title="Agent trail">
            <ol className="relative ml-2 space-y-4 border-l border-line pl-5">
              {t.logs.map((l) => (
                <li key={l.id} className="relative">
                  <span className="absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-ink" />
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-semibold text-ink">{AGENT_NAME[l.agent] || l.agent}</span>
                    <span className="font-mono text-xs text-ink-faint">{l.duration_ms} ms</span>
                  </div>
                  <p className="text-sm text-ink-soft">{l.summary}</p>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-xs text-ink-faint">Every step is saved to the audit log, and the ticket state is checkpointed after each agent.</p>
          </Block>
        </>)}
      </aside>
    </div>
  )
}
