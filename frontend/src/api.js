// API client for the DiagnoFlow FastAPI backend.
//
// Base URL resolution, in order:
//   1. window.__ENV__.API_URL  (Docker/Render runtime config, /config.js)
//   2. VITE_API_URL            (build-time env var)
//   3. ''                      (same origin / Vite dev-server proxy on /api)
//
// Local dev:  backend on http://localhost:8002, frontend on :5173, proxy on.
// Docker:     API_URL=http://localhost:8002 (browser calls the host port).
// Render:     API_URL=https://<your-backend-service>.onrender.com
function baseUrl() {
  const runtime = typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.API_URL
  const built = import.meta.env.VITE_API_URL
  const raw = (runtime || built || '').trim()
  return raw.replace(/\/$/, '')
}

export const API_BASE = baseUrl()

const TOKEN_KEY = 'diagnoflow_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

function detailMessage(detail) {
  if (!detail) return 'Request failed'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        const loc = Array.isArray(e.loc) ? e.loc.slice(1).join('.') : ''
        return loc ? `${loc}: ${e.msg}` : e.msg
      })
      .join('; ')
  }
  return JSON.stringify(detail)
}

export async function api(path, { method = 'GET', body, signal } = {}) {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    method,
    signal,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (res.status === 204) return null
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const err = new Error(detailMessage(data && data.detail) || `Request failed (${res.status})`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

// Multipart (file upload) requests: FormData body, auth header only —
// the browser sets the multipart boundary itself.
export async function apiForm(path, form, { method = 'POST' } = {}) {
  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    method,
    headers: {
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    body: form,
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const err = new Error(detailMessage(data && data.detail) || `Request failed (${res.status})`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

// Login uses the OAuth2 password form: the username field is the mobile number.
export async function login(mobile, password) {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: mobile, password }),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new Error(detailMessage(data && data.detail) || 'Login failed')
  }
  setToken(data.access_token)
  return data
}

export function logout() {
  setToken(null)
}

export function qs(params) {
  const entries = Object.entries(params || {}).filter(
    ([, v]) => v !== undefined && v !== null && v !== '',
  )
  if (!entries.length) return ''
  return '?' + new URLSearchParams(entries).toString()
}

export const ROLES = {
  SYSTEM_ADMIN: 'SYSTEM_ADMIN',
  RECEPTIONIST: 'RECEPTIONIST',
  LAB_TECHNICIAN: 'LAB_TECHNICIAN',
  PHARMACIST: 'PHARMACIST',
  PHARMACY_MANAGER: 'PHARMACY_MANAGER',
  PATIENT: 'PATIENT',
}

// The backend's Role enum serialises as its lowercase VALUE
// ("patient", "system_admin", "receptionist", ...), not the uppercase
// member name. Every role check in the app must go through this
// normaliser, or no role check matches at all and every user falls
// through to the wrong branch. Never compare user.role directly.
export function normalizeRole(role) {
  if (role === null || role === undefined) return ''
  const raw = typeof role === 'object' ? (role.value ?? role.name ?? '') : role
  return String(raw).trim().toUpperCase()
}

export function userRole(user) {
  return normalizeRole(user && user.role)
}

// Backend wire value for a role name, e.g. 'RECEPTIONIST' -> 'receptionist'.
// Use this when sending a role to the API (staff creation, role filters).
export function roleWireValue(roleName) {
  return String(roleName || '').trim().toLowerCase()
}

export function todayISO() {
  const d = new Date()
  return d.toISOString().slice(0, 10)
}

export function money(value) {
  if (value === null || value === undefined || value === '') return '—'
  return `BDT ${Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function fullName(p) {
  if (!p) return '—'
  return [p.patient_first_name, p.patient_last_name].filter(Boolean).join(' ') || '—'
}

export function userName(u) {
  if (!u) return '—'
  return [u.first_name, u.last_name].filter(Boolean).join(' ') || u.mobile_number || '—'
}
