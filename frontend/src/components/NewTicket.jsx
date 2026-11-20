import { useState } from 'react'
import { api } from '../api.js'

const EXAMPLES = [
  ['Locked out', 'I forgot my password and I am locked out of my account. Please help me get back in.'],
  ['Charged twice', 'I was charged twice for my subscription this month. Please refund the duplicate for order ORD-48213.'],
  ['Legal threat', 'My parcel arrived three weeks late and ruined an event. I will contact my lawyer if I am not compensated.'],
]

export default function NewTicket({ onCreated }) {
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit() {
    if (!body.trim() || body.trim().length < 3) {
      setError('Please write a short ticket message before submitting.')
      return
    }

    setBusy(true); setError('')
    try {
      const t = await api.createTicket({ subject: subject.trim(), body, channel: 'web', customer_id: 'dashboard-user' })
      setSubject(''); setBody('')
      onCreated(t)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <section aria-labelledby="new-ticket" className="rounded-lg border border-line bg-surface p-5 shadow-sm">
      <h2 id="new-ticket" className="text-base font-semibold text-ink">Send a test ticket</h2>
      <p className="mt-1 text-sm text-ink-soft">The four agents handle it in a few milliseconds, then you can read exactly what each one decided.</p>
      <div className="mt-4 space-y-3">
        <div>
          <label htmlFor="subject" className="mb-1 block text-sm font-medium text-ink">Subject</label>
          <input id="subject" className="field" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Short summary" />
        </div>
        <div>
          <label htmlFor="body" className="mb-1 block text-sm font-medium text-ink">Message</label>
          <textarea id="body" rows={4} className="field resize-none" value={body} onChange={(e) => setBody(e.target.value)} placeholder="What does the customer say?" />
        </div>
        {error && <p role="alert" className="text-sm text-flag">{error}</p>}
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn-primary" onClick={submit} disabled={busy || body.trim().length < 3}>{busy ? 'Resolving…' : 'Resolve ticket'}</button>
          <span className="text-sm text-ink-faint">or try:</span>
          {EXAMPLES.map(([s, b]) => (
            <button key={s} type="button" className="rounded-sm border border-line px-2 py-1 text-xs text-ink hover:bg-paper" onClick={() => { setSubject(s); setBody(b) }}>{s}</button>
          ))}
        </div>
      </div>
    </section>
  )
}
