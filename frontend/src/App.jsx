import { useCallback, useEffect, useState } from 'react'
import { api, getToken, login, logout, setToken, userName, userRole } from './api.js'
import { ErrorBanner, Field, inputProps } from './ui.jsx'
import { CatalogueView, OrdersView, ReportsView } from './views/operations.jsx'
import { InventoryView, MedicinesView, PharmacyView, PurchasesView } from './views/pharmacy.jsx'
import { ChatView, PrescriptionsView, SalesView } from './views/care.jsx'
import { Dashboard, PatientsView, UsersView, PatientAccountView } from './views/people.jsx'

// Navigation, by role. The backend enforces the same rules; hiding a
// page here is only for clarity — a forbidden call still returns 403.
const NAV = {
  SYSTEM_ADMIN: [
    ['dashboard', 'Dashboard'],
    ['users', 'Users'],
    ['patients', 'Patients'],
    ['orders', 'Orders'],
    ['reports', 'Reports'],
    ['catalogue', 'Test catalogue'],
    ['medicines', 'Medicines & suppliers'],
    ['inventory', 'Inventory'],
    ['purchases', 'Purchases'],
    ['prescriptions', 'Prescriptions'],
    ['sales', 'Sales'],
    ['chat', 'Assistant'],
  ],
  RECEPTIONIST: [
    ['dashboard', 'Dashboard'],
    ['patients', 'Patients'],
    ['patient-accounts', 'Patient accounts'],
    ['orders', 'Orders'],
    ['reports', 'Reports'],
    ['catalogue', 'Test catalogue'],
    ['medicines', 'Medicines & suppliers'],
    ['prescriptions', 'Prescriptions'],
    ['sales', 'Sales'],
    ['chat', 'Assistant'],
  ],
  LAB_TECHNICIAN: [
    ['dashboard', 'Dashboard'],
    ['orders', 'Orders'],
    ['reports', 'Reports'],
    ['catalogue', 'Test catalogue'],
    ['chat', 'Assistant'],
  ],
  PHARMACIST: [
    ['dashboard', 'Dashboard'],
    ['medicines', 'Medicines & suppliers'],
    ['inventory', 'Inventory'],
    ['purchases', 'Purchases'],
    ['prescriptions', 'Prescriptions'],
    ['sales', 'Sales'],
    ['chat', 'Assistant'],
  ],
  PHARMACY_MANAGER: [
    ['dashboard', 'Dashboard'],
    ['medicines', 'Medicines & suppliers'],
    ['inventory', 'Inventory'],
    ['purchases', 'Purchases'],
    ['prescriptions', 'Prescriptions'],
    ['sales', 'Sales'],
    ['chat', 'Assistant'],
  ],
  PATIENT: [
    ['dashboard', 'Dashboard'],
    ['orders', 'My orders'],
    ['reports', 'My reports'],
    ['catalogue', 'Test catalogue'],
    ['medicines', 'Pharmacy'],
    ['prescriptions', 'My prescriptions'],
    ['sales', 'My purchases'],
    ['chat', 'Assistant'],
  ],
}

function LoginPage({ onLoggedIn }) {
  const [mobile, setMobile] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(mobile.trim(), password)
      onLoggedIn()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>DiagnoFlow</h1>
        <p>Diagnostic centre &amp; pharmacy. Sign in with your mobile number.</p>
        <ErrorBanner error={error} onClose={() => setError('')} />
        <form onSubmit={submit}>
          <div className="form-grid" style={{ gridTemplateColumns: '1fr' }}>
            <Field label="Mobile number" hint="Your login name, e.g. 01711000001"><input required autoComplete="username" {...inputProps(mobile, setMobile)} /></Field>
            <Field label="Password"><input required type="password" autoComplete="current-password" {...inputProps(password, setPassword)} /></Field>
          </div>
          <button type="submit" className="primary" disabled={busy} style={{ width: '100%' }}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="muted" style={{ marginTop: 16 }}>
          Demo seed accounts use the password set by the seed scripts. If login fails with 401, check the mobile number and password, or that the account is active.
        </p>
      </div>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [view, setView] = useState('dashboard')
  const [checking, setChecking] = useState(true)
  const [loadError, setLoadError] = useState('')

  const loadMe = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setChecking(false)
      return
    }
    try {
      const me = await api('/auth/me')
      setUser(me)
      setLoadError('')
    } catch (e) {
      // Expired or invalid token: drop back to login instead of looping.
      setToken(null)
      setUser(null)
      if (e.status !== 401) setLoadError(e.message)
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => { loadMe() }, [loadMe])

  async function handleLogout() {
    try {
      await api('/chat/session', { method: 'DELETE' })
    } catch {
      // Clearing chat history must never block logout.
    }
    logout()
    setUser(null)
    setView('dashboard')
  }

  if (checking) {
    return <div className="login-wrap"><p className="muted">Loading…</p></div>
  }

  if (!user) {
    return (
      <>
        {loadError ? (
          <div style={{ padding: '12px 20px 0' }}>
            <ErrorBanner error={`Could not reach the backend: ${loadError}`} />
          </div>
        ) : null}
        <LoginPage onLoggedIn={loadMe} />
      </>
    )
  }

  const nav = NAV[userRole(user)] || NAV.PATIENT
  // A view a role may open. The sidebar above is a shorter curated list,
  // but a dashboard button must never silently do nothing: the old code
  // fell back to the dashboard whenever the target was not in the sidebar
  // list, so "View inventory" looked dead for every role whose sidebar
  // did not list Inventory, even though the backend allows staff reads.
  // The backend still enforces every guard; this only stops dead links.
  const STAFF_VIEWS = ['dashboard', 'patients', 'orders', 'reports', 'catalogue', 'medicines', 'inventory', 'purchases', 'prescriptions', 'sales', 'chat']
  const PATIENT_VIEWS = ['dashboard', 'orders', 'reports', 'catalogue', 'medicines', 'prescriptions', 'sales', 'chat']
  const allowedViews = userRole(user) === 'PATIENT'
  ? PATIENT_VIEWS
  : userRole(user) === 'SYSTEM_ADMIN'
    ? [...STAFF_VIEWS, 'users', 'patient-accounts']
    : userRole(user) === 'RECEPTIONIST'
      ? [...STAFF_VIEWS, 'patient-accounts']
      : STAFF_VIEWS
  const activeView = allowedViews.includes(view) ? view : 'dashboard'

  return (
    <div className="shell">
      <aside className="sidebar">
        <h1>DiagnoFlow</h1>
        <p className="tagline">Diagnostic centre &amp; pharmacy</p>
        <nav>
          {nav.map(([key, label]) => (
            <button
              key={key}
              type="button"
              className={activeView === key ? 'active' : ''}
              onClick={() => setView(key)}
            >
              {label}
            </button>
          ))}
        </nav>
        <div className="who">
          <div><strong>{userName(user)}</strong></div>
          <div>{userRole(user).replaceAll('_', ' ')}</div>
          <div>{user.mobile_number}</div>
          <button type="button" onClick={handleLogout}>Log out</button>
        </div>
      </aside>

      <main className="main">
        {activeView === 'dashboard' && <Dashboard user={user} go={setView} />}
        {activeView === 'users' && <UsersView user={user} />}
        {activeView === 'patient-accounts' && <PatientAccountView />}
        {activeView === 'patients' && <PatientsView user={user} />}
        {activeView === 'orders' && <OrdersView user={user} />}
        {activeView === 'reports' && <ReportsView user={user} />}
        {activeView === 'catalogue' && <CatalogueView user={user} />}
        {activeView === 'medicines' && (userRole(user) === 'PATIENT' ? <PharmacyView /> : <MedicinesView user={user} />)}
        {activeView === 'inventory' && <InventoryView user={user} />}
        {activeView === 'purchases' && <PurchasesView user={user} />}
        {activeView === 'prescriptions' && <PrescriptionsView user={user} />}
        {activeView === 'sales' && <SalesView user={user} />}
        {activeView === 'chat' && <ChatView user={user} />}
      </main>
    </div>
  )
}
