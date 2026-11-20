import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api.js'
import KnowledgeBase from './components/KnowledgeBase.jsx'
import Overview from './components/Overview.jsx'
import TicketDetail from './components/TicketDetail.jsx'
import TicketList from './components/TicketList.jsx'
import { Skeleton } from './components/ui.jsx'

const TABS = [['overview', 'Overview'], ['tickets', 'Tickets'], ['kb', 'Knowledge base']]

export default function App() {
  const [tab, setTab] = useState('overview')
  const [health, setHealth] = useState(null)
  const [stats, setStats] = useState(null)
  const [tickets, setTickets] = useState([])
  const [filter, setFilter] = useState('')
  const [docs, setDocs] = useState([])
  const [openId, setOpenId] = useState(null)
  const [offline, setOffline] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      const [h, s, t, k] = await Promise.all([api.health(), api.stats(), api.tickets(filter), api.kb()])
      setHealth(h); setStats(s); setTickets(t); setDocs(k); setOffline(false)
    } catch {
      setOffline(true)
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { const i = setInterval(refresh, 8000); return () => clearInterval(i) }, [refresh])

  async function seed() {
    setSeeding(true)
    try { await api.seedDemo(); await refresh() } finally { setSeeding(false) }
  }
  function created(t) { refresh(); setOpenId(t.id) }

  const counts = useMemo(
    () => stats ? { escalated: stats.by_status.escalated, auto_resolved: stats.by_status.auto_resolved, resolved: stats.by_status.resolved } : {},
    [stats],
  )

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-line bg-white/90 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-5 py-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-ink">Support Desk</h1>
            <p className="text-sm text-ink-soft">Four agents resolve what is safe and hand over what is not.</p>
          </div>
          <nav aria-label="Sections" className="flex flex-wrap gap-1 rounded-full bg-paper p-1">
            {TABS.map(([key, text]) => (
              <button key={key} onClick={() => setTab(key)} aria-current={tab === key ? 'page' : undefined}
                className={`rounded-full px-3.5 py-2 text-sm font-semibold transition-colors ${tab === key ? 'bg-ink text-white shadow-sm' : 'text-ink-soft hover:bg-white hover:text-ink'}`}>
                {text}{key === 'tickets' && counts.escalated ? <span className="ml-2 rounded-full bg-flag px-1.5 py-0.5 text-[10px] text-white tabular-nums">{counts.escalated}</span> : null}
              </button>
            ))}
          </nav>
        </div>
        {health && (
          <div className="border-t border-line bg-paper/60">
            <p className="mx-auto max-w-6xl px-5 py-1.5 text-xs text-ink-soft">
              Replies written by {health.llm ? 'a language model from retrieved evidence' : 'templates from retrieved evidence (offline mode)'} · orchestrated with {health.langgraph ? 'LangGraph' : 'the built-in runner'} · {health.kb_size} knowledge passages
            </p>
          </div>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-5 py-6">
        {offline && (
          <p role="alert" className="mb-5 rounded-md border border-flag/40 bg-flag-tint px-4 py-3 text-sm text-flag">
            Can’t reach the backend. Start it with <code className="font-mono">uvicorn app.main:app --port 8000</code> in the backend folder, then this page reconnects by itself.
          </p>
        )}

        {loading && !stats ? (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              {Array.from({ length: 5 }).map((_, idx) => (
                <Skeleton key={idx} className="h-24 rounded-lg border border-line bg-white" />
              ))}
            </div>
            <div className="grid gap-6 lg:grid-cols-5">
              <Skeleton className="h-[300px] rounded-lg border border-line bg-white lg:col-span-3" />
              <div className="space-y-6 lg:col-span-2">
                <Skeleton className="h-[140px] rounded-lg border border-line bg-white" />
                <Skeleton className="h-[160px] rounded-lg border border-line bg-white" />
              </div>
            </div>
          </div>
        ) : (
          <>
            {tab === 'overview' && <Overview stats={stats} onCreated={created} onSeed={seed} seeding={seeding} />}
            {tab === 'tickets' && <TicketList tickets={tickets} filter={filter} setFilter={setFilter} counts={counts} tau={health?.config.tau ?? 0.5} onOpen={setOpenId} onSeed={seed} seeding={seeding} />}
            {tab === 'kb' && <KnowledgeBase docs={docs} reload={refresh} />}
          </>
        )}
      </main>

      {openId && <TicketDetail id={openId} tau={health?.config.tau ?? 0.5} onClose={() => setOpenId(null)} onChanged={refresh} />}
    </div>
  )
}
