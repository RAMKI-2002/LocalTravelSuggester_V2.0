/**
 * All API calls in one file.
 *
 * Why one file: when the backend URL changes, one file changes.
 * Token injection is handled here so components never touch headers directly.
 */

const BASE = ''  // Vite proxy forwards to http://localhost:8000

function getToken() {
  return localStorage.getItem('access_token')
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function handleResponse(resp) {
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const err = await resp.json()
      detail = err.detail || JSON.stringify(err)
    } catch (_) {}
    throw new Error(detail)
  }
  return resp.json()
}

export async function register(username, email, password) {
  const resp = await fetch(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })
  return handleResponse(resp)
}

export async function login(email, password) {
  const resp = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  return handleResponse(resp)
}

export async function getMe() {
  const resp = await fetch(`${BASE}/auth/me`, {
    headers: authHeaders(),
  })
  return handleResponse(resp)
}

export async function suggestTrip({ city, preference, locality, max_results }) {
  const resp = await fetch(`${BASE}/suggest-trip`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ city, preference, locality, max_results }),
  })
  return handleResponse(resp)
}

export async function getHistory(limit = 20) {
  const resp = await fetch(`${BASE}/history?limit=${limit}`, {
    headers: authHeaders(),
  })
  return handleResponse(resp)
}

export async function getHealthDetailed() {
  const resp = await fetch(`${BASE}/health/detailed`)
  return handleResponse(resp)
}
