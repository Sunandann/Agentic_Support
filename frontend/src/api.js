const BASE = import.meta.env.VITE_API_URL || ''

async function req(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const res = await fetch(BASE + path, { ...options, headers })
  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { /* non-JSON error body */ }
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status})`)
  }
  const contentType = res.headers.get('content-type') || ''
  return contentType.includes('application/json') ? res.json() : res.text()
}

export const api = {
  health: () => req('/api/health'),
  stats: () => req('/api/stats'),
  tickets: (status) => req('/api/tickets' + (status ? `?status=${status}` : '')),
  ticket: (id) => req(`/api/tickets/${id}`),
  createTicket: (body) => req('/api/tickets', { method: 'POST', body: JSON.stringify(body) }),
  resolve: (id, body) => req(`/api/tickets/${id}/resolve`, { method: 'POST', body: JSON.stringify(body) }),
  kb: () => req('/api/kb'),
  addKb: (body) => req('/api/kb', { method: 'POST', body: JSON.stringify(body) }),
  seedDemo: () => req('/api/demo/seed', { method: 'POST' }),
  runFeedback: () => req('/api/feedback/run', { method: 'POST' }),
}
