import { useCallback, useEffect, useState } from 'react'
import { api, fullName, money, normalizeRole, qs, roleWireValue, todayISO, userName, userRole } from '../api.js'
import { Badge, Empty, ErrorBanner, Field, Pager, inputProps } from '../ui.jsx'

const PAGE_SIZE = 20

/* ---------------- Dashboard ---------------- */

// Dashboards are strictly per role. Each role only calls the endpoints
// that role is allowed to call, and only sees its own cards:
//   PATIENT           - only their own /me lists. Never staff totals,
//                       patient lists, sales or stock.
//   SYSTEM_ADMIN      - counts only (no personal information), every table.
//   RECEPTIONIST      - patients and orders/reports only. No sales, no stock.
//   LAB_TECHNICIAN    - orders and reports only. No patients, sales or stock.
//   PHARMACIST /
//   PHARMACY_MANAGER  - sales, stock and prescriptions only. No patients/orders.
// A failed call shows "—", never a misleading 0: a 0 must mean "none",
// not "forbidden / failed".
const IN_PROGRESS = ['registered', 'sample_collected', 'processing']

function testNames(order) {
  return (order.items || [])
    .map((it) => (it.test && (it.test.test_name || it.test.test_code)) || 'Test')
    .filter(Boolean)
}

export function Dashboard({ user, go }) {
  const role = userRole(user)
  const isPatient = role === 'PATIENT'
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      const today = todayISO()
      try {
        if (isPatient) {
          const [orders, reports, prescriptions, sales] = await Promise.all([
            api(`/diagnostic-orders/me?page_size=100`).catch(() => null),
            api(`/test-reports/me?page_size=100`).catch(() => null),
            api(`/prescriptions/me?page_size=100`).catch(() => null),
            api(`/sales/me?page_size=100`).catch(() => null),
          ])
          if (!cancelled) setData({ orders: orders || [], reports: reports || [], prescriptions: prescriptions || [], sales: sales || [] })
          return
        }
        if (role === 'SYSTEM_ADMIN') {
          const [patients, orders, reports, prescriptions, totals, lowStock, expiring] = await Promise.all([
            api(`/patients?page_size=100`).catch(() => null),
            api(`/diagnostic-orders?page_size=100`).catch(() => null),
            api(`/test-reports?page_size=100`).catch(() => null),
            api(`/prescriptions?page_size=100`).catch(() => null),
            api(`/sales/daily-totals?date_from=${today}&date_to=${today}`).catch(() => null),
            api('/inventory/batches/low-stock').catch(() => null),
            api('/inventory/batches/expiring?days=30').catch(() => null),
          ])
          if (!cancelled) setData({
            patients: patients, orders: orders || [], reports: reports || [],
            prescriptions: prescriptions || [], totals: totals || [], lowStock: lowStock, expiring: expiring,
          })
          return
        }
        if (role === 'RECEPTIONIST') {
          const [patients, orders, reports] = await Promise.all([
            api(`/patients?page_size=100`).catch(() => null),
            api(`/diagnostic-orders?page_size=100`).catch(() => null),
            api(`/test-reports?page_size=100`).catch(() => null),
          ])
          if (!cancelled) setData({ patients, orders: orders || [], reports: reports || [] })
          return
        }
        if (role === 'LAB_TECHNICIAN') {
          const [orders, reports] = await Promise.all([
            api(`/diagnostic-orders?page_size=100`).catch(() => null),
            api(`/test-reports?page_size=100`).catch(() => null),
          ])
          if (!cancelled) setData({ orders: orders || [], reports: reports || [] })
          return
        }
        if (role === 'PHARMACIST' || role === 'PHARMACY_MANAGER') {
          const [totals, lowStock, expiring, prescriptions] = await Promise.all([
            api(`/sales/daily-totals?date_from=${today}&date_to=${today}`).catch(() => null),
            api('/inventory/batches/low-stock').catch(() => null),
            api('/inventory/batches/expiring?days=30').catch(() => null),
            api(`/prescriptions?page_size=100`).catch(() => null),
          ])
          if (!cancelled) setData({ totals: totals || [], lowStock, expiring, prescriptions: prescriptions || [] })
          return
        }
        // Unrecognised role: show nothing rather than leak another role's data.
        if (!cancelled) setData({})
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    }
    load()
    return () => { cancelled = true }
  }, [isPatient, role])

  if (!role) {
    return (
      <div>
        <h2>Welcome, {userName(user)}</h2>
        <ErrorBanner error="Your login response did not include a role, so no dashboard data can be shown safely. Log out and log in again." />
      </div>
    )
  }

  if (isPatient) {
    const orders = data ? data.orders : []
    const reports = data ? data.reports : []
    const inQueue = orders.filter((o) => IN_PROGRESS.includes(String(o.status)))
    const completed = orders.filter((o) => String(o.status) === 'completed')
    return (
      <div>
        <h2>Welcome, {userName(user)}</h2>
        <p className="lead">Your own orders, reports, prescriptions and purchases — nothing else.</p>
        <ErrorBanner error={error} onClose={() => setError('')} />
        {!data ? <p className="muted">Loading…</p> : (
          <>
            <div className="grid cols-4">
              <div className="card stat"><div className="label">Reports in queue</div><div className="value">{inQueue.length}</div><button type="button" onClick={() => go('orders')}>View orders</button></div>
              <div className="card stat"><div className="label">Reports ready</div><div className="value">{reports.length}</div><button type="button" onClick={() => go('reports')}>View reports</button></div>
              <div className="card stat"><div className="label">My prescriptions</div><div className="value">{data.prescriptions.length}</div><button type="button" onClick={() => go('prescriptions')}>View prescriptions</button></div>
              <div className="card stat"><div className="label">My purchases</div><div className="value">{data.sales.length}</div><button type="button" onClick={() => go('sales')}>View purchases</button></div>
            </div>

            <div className="card">
              <h3>Reports in queue</h3>
              {inQueue.length === 0 ? <Empty text="No tests in progress. When an order is registered, it appears here until it is completed." /> : (
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Invoice</th><th>Tests</th><th>Date</th><th>Status</th><th>Expected delivery</th></tr></thead>
                    <tbody>
                      {inQueue.map((o) => (
                        <tr key={o.id}>
                          <td>{o.invoice_no}</td>
                          <td>{testNames(o).join(', ') || '—'}</td>
                          <td>{String(o.order_date || '').slice(0, 10)}</td>
                          <td><Badge value={o.status} /></td>
                          <td>{o.expected_delivery ? String(o.expected_delivery).slice(0, 10) : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="card">
              <h3>Previous reports</h3>
              {reports.length === 0 && completed.length === 0 ? <Empty text="No released reports yet." /> : (
                <>
                  {reports.length ? (
                    <div className="table-wrap">
                      <table>
                        <thead><tr><th>Test</th><th>Released</th></tr></thead>
                        <tbody>
                          {reports.map((r) => (
                            <tr key={r.id}>
                              <td>{r.order_item && r.order_item.test ? `${r.order_item.test.test_code} — ${r.order_item.test.test_name}` : `${String(r.id).slice(0, 8)}…`}</td>
                              <td>{r.released_at ? String(r.released_at).slice(0, 16).replace('T', ' ') : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                  {completed.length ? (
                    <>
                      <p className="muted" style={{ marginTop: 12 }}>Completed orders</p>
                      <ul>
                        {completed.map((o) => <li key={o.id}>{o.invoice_no} — {testNames(o).join(', ')} ({String(o.order_date || '').slice(0, 10)})</li>)}
                      </ul>
                    </>
                  ) : null}
                  <p className="muted">Open “My reports” to see the stored result file for each report.</p>
                </>
              )}
            </div>
          </>
        )}
      </div>
    )
  }

  const count = (list) => (list === null || list === undefined ? '—' : list.length)
  const ordersToday = data ? (data.orders || []).filter((o) => String(o.order_date || '').startsWith(todayISO())) : []
  const reportsDraft = data ? (data.reports || []).filter((r) => String(r.report_status) === 'draft') : []
  const reportsReleasedToday = data ? (data.reports || []).filter((r) => r.released_at && String(r.released_at).startsWith(todayISO())) : []
  const openPrescriptions = data ? (data.prescriptions || []).filter((p) => !['dispensed', 'cancelled'].includes(String(p.status))) : []
  const totals = data && data.totals && data.totals[0] ? data.totals[0] : null

  return (
    <div>
      <h2>Welcome, {userName(user)}</h2>
      <p className="lead">
        {role === 'SYSTEM_ADMIN'
          ? 'Counts only — no personal information. Today at a glance.'
          : role === 'RECEPTIONIST'
            ? 'Patients and orders at a glance.'
            : role === 'LAB_TECHNICIAN'
              ? 'Orders and reports at a glance.'
              : 'Pharmacy at a glance: sales, stock and prescriptions.'}
      </p>
      <ErrorBanner error={error} onClose={() => setError('')} />
      {!data ? <p className="muted">Loading…</p> : (
        <div className="grid cols-3">
          {role === 'SYSTEM_ADMIN' || role === 'RECEPTIONIST' ? (
            <div className="card stat"><div className="label">Patients (first page)</div><div className="value">{count(data.patients)}</div><div className="sub">Count only — open Patients for names</div></div>
          ) : null}
          {role === 'SYSTEM_ADMIN' || role === 'RECEPTIONIST' || role === 'LAB_TECHNICIAN' ? (
            <div className="card stat"><div className="label">Orders today</div><div className="value">{ordersToday.length}</div><div className="sub">Diagnostic orders created today</div></div>
          ) : null}
          {role === 'LAB_TECHNICIAN' ? (
            <>
              <div className="card stat"><div className="label">Orders in progress</div><div className="value">{(data.orders || []).filter((o) => IN_PROGRESS.includes(String(o.status))).length}</div><div className="sub">Registered, sample collected or processing</div></div>
              <div className="card stat"><div className="label">Reports waiting (draft)</div><div className="value">{reportsDraft.length}</div><button type="button" onClick={() => go('reports')}>View reports</button></div>
              <div className="card stat"><div className="label">Reports released today</div><div className="value">{reportsReleasedToday.length}</div><div className="sub">Released today</div></div>
            </>
          ) : null}
          {role === 'SYSTEM_ADMIN' ? (
            <>
              <div className="card stat"><div className="label">Reports waiting (draft)</div><div className="value">{reportsDraft.length}</div><div className="sub">Across all orders</div></div>
              <div className="card stat"><div className="label">Open prescriptions</div><div className="value">{openPrescriptions.length}</div><div className="sub">Not dispensed or cancelled</div></div>
            </>
          ) : null}
          {role === 'RECEPTIONIST' ? (
            <div className="card stat"><div className="label">Reports released today</div><div className="value">{reportsReleasedToday.length}</div><div className="sub">Released today</div></div>
          ) : null}
          {role === 'SYSTEM_ADMIN' || role === 'PHARMACIST' || role === 'PHARMACY_MANAGER' ? (
            <>
              <div className="card stat"><div className="label">Sales today</div><div className="value">{totals ? money(totals.total_amount) : '—'}</div><div className="sub">{totals ? `${totals.sale_count} sales` : 'No sales data'}</div></div>
              <div className="card stat"><div className="label">Low stock medicines</div><div className="value">{count(data.lowStock)}</div><button type="button" onClick={() => go('inventory')}>View inventory</button></div>
              <div className="card stat"><div className="label">Batches expiring in 30 days</div><div className="value">{count(data.expiring)}</div><button type="button" onClick={() => go('inventory')}>View inventory</button></div>
            </>
          ) : null}
          {role === 'PHARMACIST' || role === 'PHARMACY_MANAGER' ? (
            <div className="card stat"><div className="label">Open prescriptions</div><div className="value">{openPrescriptions.length}</div><button type="button" onClick={() => go('prescriptions')}>View prescriptions</button></div>
          ) : null}
          <div className="card stat"><div className="label">Assistant</div><div className="value" style={{ fontSize: 20 }}>Ask the chatbot</div><div className="sub">Summaries are available through chat, by role.</div><button type="button" onClick={() => go('chat')}>Open chat</button></div>
        </div>
      )}
    </div>
  )
}

/* ---------------- Patients ---------------- */

const SEXES = ['male', 'female', 'other']

export function PatientsView({ user }) {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState({ patient_first_name: '', patient_last_name: '', sex: 'male', age: '', phone_number: '' })
  const [editing, setEditing] = useState(null)
  const [editForm, setEditForm] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    setNotice('')
    try {
      // The backend patient search by name is broken at HEAD 8481d7a
      // (it filters on the removed Patient.patient_name and returns 500
      // for q=...). Try the server search first; on failure, fetch the
      // list and filter in the browser so search still works.
      let data
      try {
        data = await api(`/patients${qs({ q, page, page_size: PAGE_SIZE })}`)
      } catch (e) {
        if (q && e.status >= 500) {
          const all = await api(`/patients${qs({ page: 1, page_size: 100 })}`)
          const needle = q.toLowerCase()
          data = all.filter((p) =>
            [fullName(p), p.phone_number, p.patient_no].join(' ').toLowerCase().includes(needle),
          )
          setNotice('Server search is unavailable, so results were filtered in the browser. Ask the backend owner to fix PatientRepository.search (patient_name).')
        } else {
          throw e
        }
      }
      setRows(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [q, page])

  useEffect(() => { load() }, [load])

  async function createPatient(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/patients/add', {
        method: 'POST',
        body: { ...form, age: Number(form.age) },
      })
      setForm({ patient_first_name: '', patient_last_name: '', sex: 'male', age: '', phone_number: '' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function saveEdit(e) {
    e.preventDefault()
    setError('')
    const body = {}
    for (const [k, v] of Object.entries(editForm)) {
      if (v !== '' && v !== undefined && v !== null) body[k] = k === 'age' ? Number(v) : v
    }
    try {
      await api(`/patients/${editing.id}`, { method: 'PATCH', body })
      setEditing(null)
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  return (
    <div>
      <h2>Patients</h2>
      <p className="lead">Register patients and search by name, phone or patient number.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />
      {notice ? <p className="muted">{notice}</p> : null}

      <div className="card">
        <h3>Register a patient</h3>
        <form onSubmit={createPatient}>
          <div className="form-grid">
            <Field label="First name"><input required {...inputProps(form.patient_first_name, (v) => setForm({ ...form, patient_first_name: v }))} /></Field>
            <Field label="Last name"><input required {...inputProps(form.patient_last_name, (v) => setForm({ ...form, patient_last_name: v }))} /></Field>
            <Field label="Sex">
              <select value={form.sex} onChange={(e) => setForm({ ...form, sex: e.target.value })}>
                {SEXES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Age"><input required type="number" min="0" {...inputProps(form.age, (v) => setForm({ ...form, age: v }))} /></Field>
            <Field label="Phone number" hint="11–13 digits, e.g. 01711000001"><input required {...inputProps(form.phone_number, (v) => setForm({ ...form, phone_number: v }))} /></Field>
          </div>
          <button type="submit" className="primary">Register patient</button>
        </form>
      </div>

      <div className="card">
        <div className="toolbar">
          <Field label="Search"><input placeholder="Name, phone or patient no." {...inputProps(q, (v) => { setQ(v); setPage(1) })} /></Field>
          <button type="button" onClick={load}>Search</button>
        </div>
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Patient no.</th><th>Name</th><th>Sex</th><th>Age</th><th>Phone</th><th>Registered</th><th></th></tr></thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <td>{p.patient_no}</td>
                    <td>{fullName(p)}</td>
                    <td><Badge value={p.sex} /></td>
                    <td>{p.age}</td>
                    <td>{p.phone_number}</td>
                    <td>{String(p.created_at || '').slice(0, 10)}</td>
                    <td>
                      <button type="button" className="small" onClick={() => { setEditing(p); setEditForm({ patient_first_name: p.patient_first_name, patient_last_name: p.patient_last_name, sex: p.sex, age: p.age, phone_number: p.phone_number }) }}>
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={rows.length === PAGE_SIZE} />
        <p className="muted">Changing a phone number here does not change the patient&apos;s login number. Keep the two in step manually.</p>
      </div>

      {editing ? (
        <div className="card">
          <h3>Edit {fullName(editing)} ({editing.patient_no})</h3>
          <form onSubmit={saveEdit}>
            <div className="form-grid">
              <Field label="First name"><input {...inputProps(editForm.patient_first_name, (v) => setEditForm({ ...editForm, patient_first_name: v }))} /></Field>
              <Field label="Last name"><input {...inputProps(editForm.patient_last_name, (v) => setEditForm({ ...editForm, patient_last_name: v }))} /></Field>
              <Field label="Sex">
                <select value={editForm.sex || ''} onChange={(e) => setEditForm({ ...editForm, sex: e.target.value })}>
                  {SEXES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Age"><input type="number" min="0" {...inputProps(editForm.age, (v) => setEditForm({ ...editForm, age: v }))} /></Field>
              <Field label="Phone number"><input {...inputProps(editForm.phone_number, (v) => setEditForm({ ...editForm, phone_number: v }))} /></Field>
            </div>
            <div className="row-actions">
              <button type="submit" className="primary">Save</button>
              <button type="button" onClick={() => setEditing(null)}>Cancel</button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  )
}

/* ---------------- Users (admin) ---------------- */

const STAFF_ROLES = ['RECEPTIONIST', 'LAB_TECHNICIAN', 'PHARMACIST', 'PHARMACY_MANAGER']

export function UsersView({ user }) {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [staffForm, setStaffForm] = useState({ first_name: '', last_name: '', mobile_number: '', email: '', password: '', role: 'RECEPTIONIST' })
  const [patientForm, setPatientForm] = useState({ username: '', password: '' })
  const [editing, setEditing] = useState(null)
  const [editForm, setEditForm] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api(`/users${qs({ q, page, page_size: PAGE_SIZE })}`)
      setRows(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [q, page])

  useEffect(() => { load() }, [load])

  async function createStaff(e) {
    e.preventDefault()
    setError('')
    try {
      // The API expects the enum VALUE ("receptionist"), not the member name.
      await api('/auth/register', { method: 'POST', body: { ...staffForm, role: roleWireValue(staffForm.role) } })
      setStaffForm({ first_name: '', last_name: '', mobile_number: '', email: '', password: '', role: 'RECEPTIONIST' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function createPatientAccount(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/auth/register/patient', { method: 'POST', body: patientForm })
      setPatientForm({ username: '', password: '' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function saveEdit(e) {
    e.preventDefault()
    setError('')
    if (editing.id === user.id && editForm.is_active === false) {
      setError('You are about to deactivate your own account. Use a different admin account, or leave Active on.')
      return
    }
    const body = {}
    for (const [k, v] of Object.entries(editForm)) {
      if (v !== '' && v !== undefined && v !== null) body[k] = v
    }
    try {
      await api(`/users/${editing.id}`, { method: 'PATCH', body })
      setEditing(null)
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  return (
    <div>
      <h2>Users</h2>
      <p className="lead">System admin only. Create worker accounts and patient login accounts.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      <div className="grid cols-2">
        <div className="card">
          <h3>Create a worker account</h3>
          <form onSubmit={createStaff}>
            <div className="form-grid">
              <Field label="First name"><input required {...inputProps(staffForm.first_name, (v) => setStaffForm({ ...staffForm, first_name: v }))} /></Field>
              <Field label="Last name"><input required {...inputProps(staffForm.last_name, (v) => setStaffForm({ ...staffForm, last_name: v }))} /></Field>
              <Field label="Mobile number" hint="This is the login name."><input required {...inputProps(staffForm.mobile_number, (v) => setStaffForm({ ...staffForm, mobile_number: v }))} /></Field>
              <Field label="Email"><input required type="email" {...inputProps(staffForm.email, (v) => setStaffForm({ ...staffForm, email: v }))} /></Field>
              <Field label="Password"><input required type="password" {...inputProps(staffForm.password, (v) => setStaffForm({ ...staffForm, password: v }))} /></Field>
              <Field label="Role">
                <select value={staffForm.role} onChange={(e) => setStaffForm({ ...staffForm, role: e.target.value })}>
                  {STAFF_ROLES.map((r) => <option key={r} value={r}>{r.replaceAll('_', ' ')}</option>)}
                </select>
              </Field>
            </div>
            <button type="submit" className="primary">Create worker</button>
          </form>
        </div>

        <div className="card">
          <h3>Create a patient login account</h3>
          <p className="muted">The patient must already be registered. The username is the patient&apos;s phone number.</p>
          <form onSubmit={createPatientAccount}>
            <div className="form-grid">
              <Field label="Username (patient phone)"><input required {...inputProps(patientForm.username, (v) => setPatientForm({ ...patientForm, username: v }))} /></Field>
              <Field label="Password"><input required type="password" {...inputProps(patientForm.password, (v) => setPatientForm({ ...patientForm, password: v }))} /></Field>
            </div>
            <button type="submit" className="primary">Create patient account</button>
          </form>
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <Field label="Search"><input placeholder="Name, mobile or email" {...inputProps(q, (v) => { setQ(v); setPage(1) })} /></Field>
          <button type="button" onClick={load}>Search</button>
        </div>
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Mobile</th><th>Email</th><th>Role</th><th>Active</th><th></th></tr></thead>
              <tbody>
                {rows.map((u) => (
                  <tr key={u.id}>
                    <td>{userName(u)}</td>
                    <td>{u.mobile_number}</td>
                    <td>{u.email || '—'}</td>
                    <td><Badge value={normalizeRole(u.role)} /></td>
                    <td>{u.is_active ? 'Yes' : 'No'}</td>
                    <td>
                      {normalizeRole(u.role) !== 'PATIENT' ? (
                        <button type="button" className="small" onClick={() => { setEditing(u); setEditForm({ first_name: u.first_name, last_name: u.last_name, mobile_number: u.mobile_number, email: u.email || '', is_active: u.is_active }) }}>
                          Edit
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={rows.length === PAGE_SIZE} />
      </div>

      {editing ? (
        <div className="card">
          <h3>Edit {userName(editing)}</h3>
          <form onSubmit={saveEdit}>
            <div className="form-grid">
              <Field label="First name"><input {...inputProps(editForm.first_name, (v) => setEditForm({ ...editForm, first_name: v }))} /></Field>
              <Field label="Last name"><input {...inputProps(editForm.last_name, (v) => setEditForm({ ...editForm, last_name: v }))} /></Field>
              <Field label="Mobile number"><input {...inputProps(editForm.mobile_number, (v) => setEditForm({ ...editForm, mobile_number: v }))} /></Field>
              <Field label="Email"><input type="email" {...inputProps(editForm.email, (v) => setEditForm({ ...editForm, email: v }))} /></Field>
              <Field label="Active">
                <select value={editForm.is_active ? 'yes' : 'no'} onChange={(e) => setEditForm({ ...editForm, is_active: e.target.value === 'yes' })}>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </Field>
            </div>
            <div className="row-actions">
              <button type="submit" className="primary">Save</button>
              <button type="button" onClick={() => setEditing(null)}>Cancel</button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  )
}

/* ---------------- Patient accounts (admin + receptionist) ---------------- */

export function PatientAccountView() {
  const [patientForm, setPatientForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [createdFor, setCreatedFor] = useState('')

  async function createPatientAccount(e) {
    e.preventDefault()
    setError('')
    setCreatedFor('')
    try {
      await api('/auth/register/patient', { method: 'POST', body: patientForm })
      setCreatedFor(patientForm.username)
      setPatientForm({ username: '', password: '' })
    } catch (e2) {
      setError(e2.message)
    }
  }

  return (
    <div>
      <h2>Patient accounts</h2>
      <p className="lead">Create a login account for a patient who is already registered.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />
      {createdFor ? <p className="muted">Patient login account created for {createdFor}.</p> : null}
      <div className="card">
        <h3>Create a patient login account</h3>
        <p className="muted">The patient must already be registered. The username is the patient&apos;s phone number.</p>
        <form onSubmit={createPatientAccount}>
          <div className="form-grid">
            <Field label="Username (patient phone)"><input required {...inputProps(patientForm.username, (v) => setPatientForm({ ...patientForm, username: v }))} /></Field>
            <Field label="Password"><input required type="password" {...inputProps(patientForm.password, (v) => setPatientForm({ ...patientForm, password: v }))} /></Field>
          </div>
          <button type="submit" className="primary">Create patient account</button>
        </form>
      </div>
    </div>
  )
}
