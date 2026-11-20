import { ago, label } from '../format.js'
import { Empty, Gauge, Meter, StatusBadge } from './ui.jsx'

const FILTERS = [
  ['', 'All'], ['escalated', 'Needs a human'], ['auto_resolved', 'Answered by AI'], ['resolved', 'Closed by team'],
]

export default function TicketList({ tickets, filter, setFilter, counts, tau, onOpen, onSeed, seeding }) {
  const rows = filter === 'escalated' ? [...tickets].sort((a, b) => (b.priority || 0) - (a.priority || 0)) : tickets
  return (
    <section aria-label="Tickets" className="overflow-hidden rounded-lg border border-line bg-surface shadow-sm">
      <div className="flex flex-wrap gap-2 border-b border-line px-4 py-3" role="group" aria-label="Filter tickets">
        {FILTERS.map(([key, text]) => (
          <button key={key} onClick={() => setFilter(key)} aria-pressed={filter === key}
            className={`rounded-sm border px-3 py-1.5 text-sm font-medium transition-colors ${filter === key ? 'border-signal bg-signal text-white' : 'border-line text-ink hover:bg-paper'}`}>
            {text}{key && counts[key] != null ? <span className="ml-1.5 tabular-nums opacity-70">{counts[key]}</span> : null}
          </button>
        ))}
        {filter === 'escalated' && <span className="ml-auto self-center text-sm text-ink-soft">Highest priority first</span>}
      </div>

      {rows.length === 0 ? (
        <Empty title="Nothing here yet">
          {filter ? 'No tickets match this filter.' : 'Send a test ticket from the overview, or load sample data.'}
          {!filter && <><br /><button className="btn-quiet mt-3" onClick={onSeed} disabled={seeding}>Load sample tickets</button></>}
        </Empty>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-line text-ink-soft">
              <tr><th className="px-4 py-2 font-medium">Ticket</th><th className="px-2 py-2 font-medium">Topic</th><th className="px-2 py-2 font-medium">Priority</th><th className="px-2 py-2 font-medium">Escalation score</th><th className="px-2 py-2 font-medium">Status</th><th className="px-4 py-2 text-right font-medium">Received</th></tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} className="border-b border-line last:border-0 hover:bg-paper">
                  <td className="max-w-xs px-4 py-3">
                    <button className="block w-full text-left" onClick={() => onOpen(t.id)}>
                      <span className="font-semibold text-ink underline-offset-2 hover:underline">{t.subject || 'No subject'}</span>
                      <span className="mt-0.5 block truncate text-ink-soft"><span className="font-mono text-xs">#{t.id}</span> {t.body}</span>
                    </button>
                  </td>
                  <td className="px-2 py-3 text-ink-soft">{label(t.category)}</td>
                  <td className="px-2 py-3"><div className="flex items-center gap-2"><Meter value={t.priority} tone={t.priority > 0.6 ? 'flag' : 'ink'} /><span className="font-mono text-xs text-ink-soft">{t.priority?.toFixed(2) ?? '–'}</span></div></td>
                  <td className="px-2 py-3"><Gauge compact score={t.escalation_score} tau={tau} /></td>
                  <td className="px-2 py-3"><StatusBadge status={t.status} /></td>
                  <td className="px-4 py-3 text-right text-ink-soft">{ago(t.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
