const API_BASE = import.meta.env.VITE_API_URL || ''

export async function apiPost(path, body) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.erro || 'Erro desconhecido')
  return data
}

export async function apiGet(path) {
  const resp = await fetch(`${API_BASE}${path}`)
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.erro || 'Erro desconhecido')
  return data
}
