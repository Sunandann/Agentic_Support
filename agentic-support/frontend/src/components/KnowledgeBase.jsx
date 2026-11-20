import { useMemo, useState } from 'react'
import { api } from '../api.js'
import { CATEGORY_LABEL, label } from '../format.js'
import { Empty } from './ui.jsx'

const SOURCE = { faq: 'FAQ', doc: 'Documentation', resolution: 'Past resolution' }

export default function KnowledgeBase({ docs, reload }) {
  const [q, setQ] = useState('')
  const [form, setForm] = useState({ title: '', content: '', category: 'general', source: 'faq' })
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const shown = useMemo(() => {
    const n = q.trim().toLowerCase()
    return n ? docs.filter((d) => (d.title + d.content).toLowerCase().includes(n)) : docs
  }, [docs, q])

  async function add() {
    if (form.title.trim().length < 3 || form.content.trim().length < 3) {
      setMsg('Add both a title and answer before saving a passage.')
      return
    }

    setBusy(true); setMsg('')
    try { await api.addKb(form); setForm({ ...form, title: '', content: '' }); await reload(); setMsg('Passage added. New tickets can use it right away.') }
    catch (e) { setMsg(e.message) } finally { setBusy(false) }
  }

  async function fold() {
    setBusy(true); setMsg('')
    try { const r = await api.runFeedback(); await reload(); setMsg(r.added ? `Added ${r.added} resolved ticket${r.added > 1 ? 's' : ''} to the knowledge base.` : 'Everything resolved is already in the knowledge base.') }
    catch (e) { setMsg(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <section className="overflow-hidden rounded-lg border border-line bg-white shadow-sm lg:col-span-3" aria-label="Knowledge base passages">
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <label htmlFor="kbsearch" className="sr-only">Search passages</label>
          <input id="kbsearch" className="field" placeholder={`Search ${docs.length} passages`} value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        {shown.length === 0 ? <Empty title="No passages match">Try a different word, or add a passage on the right.</Empty> : (
          <ul className="max-h-[70vh] divide-y divide-line overflow-y-auto">
            {shown.map((d) => (
              <li key={d.id} className="px-4 py-3 text-sm">
                <p className="font-semibold text-ink">{d.title}</p>
                <p className="mt-0.5 text-ink-soft">{d.content}</p>
                <p className="mt-1 text-xs text-ink-faint">{label(d.category)} · {SOURCE[d.source] || d.source}{d.ticket_id ? ` · ticket #${d.ticket_id}` : ''}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="space-y-6 lg:col-span-2">
        <section className="rounded-lg border border-line bg-white p-5 shadow-sm" aria-labelledby="addkb">
          <h2 id="addkb" className="text-base font-semibold text-ink">Add a passage</h2>
          <div className="mt-3 space-y-3">
            <div><label htmlFor="kt" className="mb-1 block text-sm font-medium text-ink">Question or title</label><input id="kt" className="field" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div><label htmlFor="kc" className="mb-1 block text-sm font-medium text-ink">Answer</label><textarea id="kc" rows={4} className="field resize-none" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label htmlFor="kcat" className="mb-1 block text-sm font-medium text-ink">Topic</label><select id="kcat" className="field" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>{Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
              <div><label htmlFor="ksrc" className="mb-1 block text-sm font-medium text-ink">Type</label><select id="ksrc" className="field" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}><option value="faq">FAQ</option><option value="doc">Documentation</option><option value="resolution">Past resolution</option></select></div>
            </div>
            <button className="btn-primary" onClick={add} disabled={busy || form.title.trim().length < 3 || form.content.trim().length < 3}>Add passage</button>
          </div>
        </section>
        <section className="rounded-lg border border-line bg-white p-5 shadow-sm" aria-labelledby="fold">
          <h2 id="fold" className="text-base font-semibold text-ink">Learn from resolved tickets</h2>
          <p className="mt-1 text-sm text-ink-soft">Team answers are added automatically when a ticket is closed. This also folds in AI-answered tickets, so similar questions find them next time.</p>
          <button className="btn-quiet mt-3" onClick={fold} disabled={busy}>Fold resolved tickets in</button>
        </section>
        {msg && <p role="status" className="text-sm text-ink-soft">{msg}</p>}
      </div>
    </div>
  )
}
