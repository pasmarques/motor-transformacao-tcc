/**
 * Cliente HTTP com refresh automático de token JWT.
 * O access token fica em memória (nunca em localStorage).
 * O refresh token fica em httpOnly cookie gerenciado pelo browser.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

let _accessToken = null

export function setAccessToken(token) {
  _accessToken = token
}

export function getAccessToken() {
  return _accessToken
}

export function clearAccessToken() {
  _accessToken = null
}

async function _refreshToken() {
  const resp = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    credentials: 'include', // envia o httpOnly cookie
  })
  if (!resp.ok) {
    clearAccessToken()
    throw new Error('Sessão expirada. Faça login novamente.')
  }
  const data = await resp.json()
  setAccessToken(data.access_token)
  return data.access_token
}

export async function apiFetch(path, options = {}) {
  const doRequest = async (token) => {
    return fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    })
  }

  let resp = await doRequest(_accessToken)

  // Token expirado — tenta refresh automático
  if (resp.status === 401 && _accessToken) {
    try {
      const newToken = await _refreshToken()
      resp = await doRequest(newToken)
    } catch {
      clearAccessToken()
      window.location.href = '/login'
      throw new Error('Sessão expirada.')
    }
  }

  return resp
}

export async function apiJSON(path, options = {}) {
  const resp = await apiFetch(path, options)
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.erro || 'Erro desconhecido')
  return data
}
