import { duration, label, pct } from '../format.js'
import NewTicket from './NewTicket.jsx'

function Figure({ name, value, note }) {
  return (
    <div className="px-5 py-4">
      <p className="text-sm text-ink-soft">{name}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums text-ink">{value}</p>
      {note && <p className="mt-1 text-xs text-ink-faint">{note}</p>}
    </div>
  )
}

export default function Overview({ stats, onCreated, onSeed, seeding }) {
  if (!stats) return <p className="p-6 text-ink-soft">Loading…</p>
  const s = stats.by_status
  const trend = Array.isArray(stats.trend) ? stats.trend : []
  const maxDay = Math.max(1, ...trend.map((d) => d.total))
  const cats = Object.entries(stats.categories || {}).sort((a, b) => b[1] - a[1])
  const maxCat = Math.max(1, ...cats.map(([, n]) => n))
  const queue = s.escalated

  return (
    <div className="space-y-6">
      <section aria-label="Key figures" className="grid divide-line overflow-hidden rounded-lg border border-line bg-surface sm:grid-cols-2 sm:divide-x lg:grid-cols-5 [&>*]:border-b [&>*]:border-line lg:[&>*]:border-b-0">
        <Figure name="Answered without a human" value={pct(stats.first_contact_resolution_rate)} note="first-contact resolution" />
        <Figure name="Waiting for a human" value={queue} note={queue === 1 ? '1 ticket in the queue' : `${queue} tickets in the queue`} />
        <Figure name="Escalation precision" value={pct(stats.escalation_precision)} note={stats.escalations_reviewed ? `${stats.escalations_reviewed} reviewed by the team` : 'appears once the team reviews handoffs'} />
        <Figure name="Avg. handling time" value={duration(stats.avg_handling_seconds)} note={stats.avg_handling_human_seconds != null ? `team-handled: ${duration(stats.avg_handling_human_seconds)}` : 'ticket received to resolved'} />
        <Figure name="Tickets processed" value={stats.total} note={`${stats.actions_executed} routine actions run`} />
      </section>

      {stats.total === 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-dashed border-ink-faint bg-surface px-5 py-4">
          <p className="text-sm text-ink-soft">No tickets yet. Load ten realistic sample tickets to see the agents at work.</p>
          <button className="btn-primary" onClick={onSeed} disabled={seeding}>{seeding ? 'Loading…' : 'Load sample tickets'}</button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3"><NewTicket onCreated={onCreated} /></div>

        <div className="space-y-6 lg:col-span-2">
          <section aria-labelledby="trend" className="rounded-lg border border-line bg-surface p-5">
            <h2 id="trend" className="text-base font-semibold text-ink">Last 7 days</h2>
            {trend.length === 0 ? <p className="mt-3 text-sm text-ink-soft">No trend data yet.</p> : (
              <>
                <div className="mt-4 flex h-28 items-end gap-2">
                  {trend.map((d) => (
                    <div key={d.date} className="flex flex-1 flex-col items-center gap-1" title={`${d.date}: ${d.auto} answered by AI, ${d.escalated} handed to a human`}>
                      <div className="flex w-full flex-1 flex-col justify-end">
                        <div className="w-full bg-flag transition-all duration-200" style={{ height: `${(d.escalated / maxDay) * 100}%` }} />
                        <div className="w-full bg-signal transition-all duration-200" style={{ height: `${(d.auto / maxDay) * 100}%` }} />
                      </div>
                      <span className="text-[11px] text-ink-faint">{d.date.slice(8)}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 flex gap-4 text-xs text-ink-soft">
                  <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 bg-signal" />Answered by AI</span>
                  <span className="flex items-center gap-1.5"><i className="inline-block h-2.5 w-2.5 bg-flag" />Handed to a human</span>
                </p>
              </>
            )}
          </section>

          <section aria-labelledby="topics" className="rounded-lg border border-line bg-surface p-5">
            <h2 id="topics" className="text-base font-semibold text-ink">What customers ask about</h2>
            {cats.length === 0 ? <p className="mt-3 text-sm text-ink-soft">Topics appear after the first ticket.</p> : (
              <ul className="mt-3 space-y-2">
                {cats.map(([c, n]) => (
                  <li key={c} className="grid grid-cols-[8.5rem_1fr_2rem] items-center gap-2 text-sm">
                    <span className="truncate text-ink-soft">{label(c)}</span>
                    <span className="h-2 rounded-full bg-paper"><span className="block h-full rounded-full bg-ink" style={{ width: `${(n / maxCat) * 100}%` }} /></span>
                    <span className="text-right tabular-nums text-ink-soft">{n}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-labelledby="agents" className="rounded-lg border border-line bg-surface p-5">
            <h2 id="agents" className="text-base font-semibold text-ink">Agent activity</h2>
            {stats.agents.length === 0 ? <p className="mt-3 text-sm text-ink-soft">No runs recorded yet.</p> : (
              <table className="mt-3 w-full text-sm">
                <thead><tr className="text-left text-ink-soft"><th className="pb-1 font-medium">Agent</th><th className="pb-1 text-right font-medium">Runs</th><th className="pb-1 text-right font-medium">Avg. time</th></tr></thead>
                <tbody>
                  {stats.agents.map((a) => (
                    <tr key={a.agent} className="border-t border-line"><td className="py-1.5 capitalize text-ink">{a.agent}</td><td className="py-1.5 text-right tabular-nums text-ink-soft">{a.runs}</td><td className="py-1.5 text-right font-mono text-xs text-ink-soft">{a.avg_ms} ms</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
