import { useCallback, useEffect, useRef, useState } from 'react'
import { API_BASE, api, apiForm, fullName, getToken, money, qs, userRole } from '../api.js'
import { Badge, ConfirmButton, Empty, ErrorBanner, Field, Pager, inputProps } from '../ui.jsx'

const PAGE_SIZE = 20
const WORK_STATUSES = ['registered', 'sample_collected', 'processing', 'completed', 'cancelled']
const PAYMENT_STATUSES = ['pending', 'paid']

/* ---------------- Diagnostic orders ---------------- */

export function OrdersView({ user }) {
  const isPatient = userRole(user) === 'PATIENT'
  const canCreate = ['SYSTEM_ADMIN', 'RECEPTIONIST'].includes(userRole(user))
  const canStatus = ['SYSTEM_ADMIN', 'LAB_TECHNICIAN'].includes(userRole(user))
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [patients, setPatients] = useState([])
  const [tests, setTests] = useState([])
  const [form, setForm] = useState({ patient_id: '', expected_delivery: '', items: [] })
  const [selected, setSelected] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const path = isPatient
        ? `/diagnostic-orders/me${qs({ page, page_size: PAGE_SIZE })}`
        : `/diagnostic-orders${qs({ q, page, page_size: PAGE_SIZE })}`
      const data = await api(path)
      setRows(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [isPatient, q, page])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!canCreate) return
    api(`/patients?page_size=100`).then(setPatients).catch(() => {})
    api(`/tests?page_size=100`).then(setTests).catch(() => {})
  }, [canCreate])

  function toggleTest(code) {
    setForm((f) => ({
      ...f,
      items: f.items.includes(code) ? f.items.filter((c) => c !== code) : [...f.items, code],
    }))
  }

  async function createOrder(e) {
    e.preventDefault()
    setError('')
    if (!form.items.length) {
      setError('Choose at least one test.')
      return
    }
    try {
      await api('/diagnostic-orders/add', {
        method: 'POST',
        body: {
          patient_id: form.patient_id,
          expected_delivery: form.expected_delivery ? new Date(form.expected_delivery).toISOString() : null,
          items: form.items.map((test_code) => ({ test_code })),
        },
      })
      setForm({ patient_id: '', expected_delivery: '', items: [] })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function patchOrder(order, body, endpoint) {
    setError('')
    try {
      const updated = await api(`/diagnostic-orders/${order.id}/${endpoint}`, { method: 'PATCH', body })
      setRows((rs) => rs.map((r) => (r.id === order.id ? updated : r)))
      if (selected && selected.id === order.id) setSelected(updated)
    } catch (e) {
      setError(e.message)
    }
  }

  async function patchItem(item, item_status) {
    setError('')
    try {
      await api(`/diagnostic-orders/items/${item.id}/status`, { method: 'PATCH', body: { item_status } })
      if (selected) {
        const fresh = await api(`/diagnostic-orders/${selected.id}`)
        setSelected(fresh)
        setRows((rs) => rs.map((r) => (r.id === fresh.id ? fresh : r)))
      }
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>{isPatient ? 'My orders' : 'Diagnostic orders'}</h2>
      <p className="lead">Prices are fixed at order time. Order and item statuses are tracked separately by the backend.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      {canCreate ? (
        <div className="card">
          <h3>Create an order</h3>
          <form onSubmit={createOrder}>
            <div className="form-grid">
              <Field label="Patient">
                <select required value={form.patient_id} onChange={(e) => setForm({ ...form, patient_id: e.target.value })}>
                  <option value="">Select a patient…</option>
                  {patients.map((p) => <option key={p.id} value={p.id}>{fullName(p)} — {p.patient_no} ({p.phone_number})</option>)}
                </select>
              </Field>
              <Field label="Expected delivery" hint="Optional"><input type="datetime-local" {...inputProps(form.expected_delivery, (v) => setForm({ ...form, expected_delivery: v }))} /></Field>
            </div>
            <Field label="Tests">
              <div className="check-list">
                {tests.map((t) => (
                  <label key={t.test_code}>
                    <input type="checkbox" checked={form.items.includes(t.test_code)} onChange={() => toggleTest(t.test_code)} />
                    {t.test_code} — {t.test_name} ({money(t.price)})
                  </label>
                ))}
              </div>
            </Field>
            <div style={{ marginTop: 12 }}>
              <button type="submit" className="primary">Create order</button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="card">
        {!isPatient ? (
          <div className="toolbar">
            <Field label="Search"><input placeholder="Invoice number" {...inputProps(q, (v) => { setQ(v); setPage(1) })} /></Field>
            <button type="button" onClick={load}>Search</button>
          </div>
        ) : null}
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Invoice</th><th>Patient</th><th>Date</th><th>Status</th><th>Payment</th><th>Total</th><th></th></tr></thead>
              <tbody>
                {rows.map((o) => (
                  <tr key={o.id}>
                    <td>{o.invoice_no}</td>
                    <td>{o.patient ? fullName(o.patient) : '—'}</td>
                    <td>{String(o.order_date || '').slice(0, 10)}</td>
                    <td><Badge value={o.status} /></td>
                    <td><Badge value={o.payment_status} /></td>
                    <td>{money(o.total_amount)}</td>
                    <td>
                      <button type="button" className="small" onClick={async () => {
                        try {
                          const fresh = isPatient ? await api(`/diagnostic-orders/me/${o.id}`) : await api(`/diagnostic-orders/${o.id}`)
                          setSelected(fresh)
                        } catch (e) { setError(e.message) }
                      }}>
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={rows.length === PAGE_SIZE} />
      </div>

      {selected ? (
        <div className="card">
          <h3>Order {selected.invoice_no} — <Badge value={selected.status} /> <Badge value={selected.payment_status} /></h3>
          <p className="muted">Total {money(selected.total_amount)} · Expected delivery: {selected.expected_delivery ? String(selected.expected_delivery).slice(0, 16).replace('T', ' ') : '—'}</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Test</th><th>Price</th><th>Item status</th>{canStatus ? <th>Change item status</th> : null}</tr></thead>
              <tbody>
                {selected.items.map((it) => (
                  <tr key={it.id}>
                    <td>{it.test.test_code} — {it.test.test_name}</td>
                    <td>{it.price_at_order !== undefined ? money(it.price_at_order) : '—'}</td>
                    <td><Badge value={it.item_status} /></td>
                    {canStatus ? (
                      <td>
                        <select value={it.item_status} onChange={(e) => patchItem(it, e.target.value)}>
                          {WORK_STATUSES.map((s) => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}
                        </select>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {canStatus || canCreate ? (
            <div className="row-actions" style={{ marginTop: 12 }}>
              {canStatus ? (
                <select aria-label="Order status" value={selected.status} onChange={(e) => patchOrder(selected, { status: e.target.value }, 'status')} style={{ width: 'auto' }}>
                  {WORK_STATUSES.map((s) => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}
                </select>
              ) : null}
              {canCreate ? (
                <select aria-label="Payment status" value={selected.payment_status} onChange={(e) => patchOrder(selected, { payment_status: e.target.value }, 'payment')} style={{ width: 'auto' }}>
                  {PAYMENT_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              ) : null}
              <button type="button" onClick={() => setSelected(null)}>Close</button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

/* ---------------- Test reports ---------------- */

export function ReportsView({ user }) {
  const isPatient = userRole(user) === 'PATIENT'
  const canLab = userRole(user) === 'LAB_TECHNICIAN'
  const [rows, setRows] = useState([])
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [orders, setOrders] = useState([])
  const [form, setForm] = useState({ order_id: '', order_item_id: '' })
  const [selectedItems, setSelectedItems] = useState([])
  const [reportFile, setReportFile] = useState(null)
  const fileInputRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const path = isPatient
        ? `/test-reports/me${qs({ page, page_size: PAGE_SIZE })}`
        : `/test-reports${qs({ status: status || undefined, page, page_size: PAGE_SIZE })}`
      const data = await api(path)
      setRows(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [isPatient, status, page])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!canLab) return
    api(`/diagnostic-orders?page_size=100`).then(setOrders).catch(() => {})
  }, [canLab])

  useEffect(() => {
    if (!form.order_id) { setSelectedItems([]); return }
    api(`/diagnostic-orders/${form.order_id}`).then((o) => setSelectedItems(o.items || [])).catch(() => setSelectedItems([]))
  }, [form.order_id])

  async function createReport(e) {
    e.preventDefault()
    setError('')
    if (!reportFile) {
      setError('Choose a report file to upload.')
      return
    }
    try {
      const fd = new FormData()
      fd.append('order_item_id', form.order_item_id)
      fd.append('file', reportFile)
      await apiForm('/test-reports/upload', fd)
      setForm({ order_id: '', order_item_id: '' })
      setReportFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function downloadReport(r) {
    setError('')
    try {
      const path = isPatient ? `/test-reports/me/${r.id}/file` : `/test-reports/${r.id}/file`
      const res = await fetch(`${API_BASE}/api/v1${path}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (!res.ok) {
        const data = await res.json().catch(() => null)
        throw new Error((data && data.detail) || `Download failed (${res.status})`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const match = (res.headers.get('content-disposition') || '').match(/filename="?([^"]+)"?/)
      const a = document.createElement('a')
      a.href = url
      a.download = match ? match[1] : 'report'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function release(id) {
    setError('')
    try {
      const updated = await api(`/test-reports/${id}/release`, { method: 'PATCH' })
      setRows((rs) => rs.map((r) => (r.id === id ? updated : r)))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>{isPatient ? 'My reports' : 'Test reports'}</h2>
      <p className="lead">{isPatient ? 'Only your released reports are shown here. Use Download to open the report file.' : 'Only lab technicians can create and release reports. Upload the report file — it is stored on the server and the patient can download it once released.'}</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      {canLab ? (
        <div className="card">
          <h3>Create a report (draft)</h3>
          <form onSubmit={createReport}>
            <div className="form-grid">
              <Field label="Order">
                <select required value={form.order_id} onChange={(e) => setForm({ ...form, order_id: e.target.value, order_item_id: '' })}>
                  <option value="">Select an order…</option>
                  {orders.map((o) => <option key={o.id} value={o.id}>{o.invoice_no} — {o.patient ? fullName(o.patient) : ''}</option>)}
                </select>
              </Field>
              <Field label="Order item">
                <select required value={form.order_item_id} onChange={(e) => setForm({ ...form, order_item_id: e.target.value })} disabled={!selectedItems.length}>
                  <option value="">Select a test…</option>
                  {selectedItems.map((it) => <option key={it.id} value={it.id}>{it.test.test_code} — {it.test.test_name} ({it.item_status})</option>)}
                </select>
              </Field>
              <Field label="Report file" hint="PDF or image, up to 10 MB"><input ref={fileInputRef} required type="file" accept=".pdf,image/*" onChange={(e) => setReportFile(e.target.files[0] || null)} /></Field>
            </div>
            <button type="submit" className="primary">Create report</button>
          </form>
        </div>
      ) : null}

      <div className="card">
        {!isPatient ? (
          <div className="toolbar">
            <Field label="Status">
              <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
                <option value="">All</option>
                <option value="draft">Draft</option>
                <option value="released">Released</option>
              </select>
            </Field>
          </div>
        ) : null}
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Test</th><th>Result file</th><th>Status</th><th>Released</th><th>Created</th>{(canLab || isPatient) ? <th></th> : null}</tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.order_item && r.order_item.test ? `${r.order_item.test.test_code} — ${r.order_item.test.test_name}` : `${String(r.order_item_id || r.id).slice(0, 8)}…`}</td>
                    <td>{r.file_location || '—'}</td>
                    <td><Badge value={r.report_status} /></td>
                    <td>{r.released_at ? String(r.released_at).slice(0, 16).replace('T', ' ') : '—'}</td>
                    <td>{r.created_at ? String(r.created_at).slice(0, 10) : '—'}</td>
                    {(canLab || isPatient) ? (
                      <td>
                        <div className="row-actions">
                          <button type="button" className="small" onClick={() => downloadReport(r)}>Download</button>
                          {canLab && r.report_status === 'draft' ? (
                            <ConfirmButton label="Release" className="small" onConfirm={() => release(r.id)} />
                          ) : null}
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={rows.length === PAGE_SIZE} />
        {isPatient ? <p className="muted">The result is the file stored at the path shown. The system does not offer a file download yet.</p> : null}
      </div>
    </div>
  )
}

/* ---------------- Test catalogue ---------------- */

export function CatalogueView({ user }) {
  const canEdit = ['SYSTEM_ADMIN', 'LAB_TECHNICIAN'].includes(userRole(user))
  const [departments, setDepartments] = useState([])
  const [tests, setTests] = useState([])
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deptName, setDeptName] = useState('')
  const [testForm, setTestForm] = useState({ test_code: '', test_name: '', department_id: '', price: '', expected_delivery_time: '' })

  const isPatient = userRole(user) === 'PATIENT'
  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    // Load departments and tests independently: a departments failure
    // must not hide the test list (or vice versa).
    try {
      const deps = await api(`/departments?active_only=${isPatient}`)
      setDepartments(Array.isArray(deps) ? deps : deps.items || [])
    } catch {
      setDepartments([])
    }
    try {
      const ts = await api(`/tests${qs({ q, page, page_size: PAGE_SIZE })}`)
      setTests(Array.isArray(ts) ? ts : ts.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [q, page, isPatient])

  useEffect(() => { load() }, [load])

  async function createDepartment(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/departments/add', { method: 'POST', body: { name: deptName } })
      setDeptName('')
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function createTest(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/tests/add', {
        method: 'POST',
        body: { ...testForm, price: String(testForm.price) },
      })
      setTestForm({ test_code: '', test_name: '', department_id: '', price: '', expected_delivery_time: '' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function toggleTest(t) {
    setError('')
    try {
      const updated = await api(`/tests/${t.test_code}`, { method: 'PATCH', body: { is_active: !t.is_active } })
      setTests((ts) => ts.map((x) => (x.test_code === t.test_code ? updated : x)))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>Test catalogue</h2>
      <p className="lead">Departments and diagnostic tests with prices and expected delivery times.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      <div className="grid cols-2">
        <div className="card">
          <h3>Departments</h3>
          {departments.length === 0 ? <Empty text="No departments." /> : (
            <ul>
              {departments.map((d) => <li key={d.id}>{d.name} {!d.is_active ? <Badge value="inactive" /> : null}</li>)}
            </ul>
          )}
          {canEdit ? (
            <form onSubmit={createDepartment} style={{ marginTop: 12 }}>
              <div className="form-grid">
                <Field label="New department"><input required {...inputProps(deptName, setDeptName)} /></Field>
              </div>
              <button type="submit" className="primary">Add department</button>
            </form>
          ) : null}
        </div>

        {canEdit ? (
          <div className="card">
            <h3>Add a test</h3>
            <form onSubmit={createTest}>
              <div className="form-grid">
                <Field label="Test code" hint="Uppercase, e.g. CBC"><input required {...inputProps(testForm.test_code, (v) => setTestForm({ ...testForm, test_code: v }))} /></Field>
                <Field label="Test name"><input required {...inputProps(testForm.test_name, (v) => setTestForm({ ...testForm, test_name: v }))} /></Field>
                <Field label="Department">
                  <select required value={testForm.department_id} onChange={(e) => setTestForm({ ...testForm, department_id: e.target.value })}>
                    <option value="">Select…</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </Field>
                <Field label="Price (BDT)"><input required type="number" min="0" step="0.01" {...inputProps(testForm.price, (v) => setTestForm({ ...testForm, price: v }))} /></Field>
                <Field label="Expected delivery time"><input required placeholder="e.g. Same day" {...inputProps(testForm.expected_delivery_time, (v) => setTestForm({ ...testForm, expected_delivery_time: v }))} /></Field>
              </div>
              <button type="submit" className="primary">Add test</button>
            </form>
          </div>
        ) : null}
      </div>

      <div className="card">
        <div className="toolbar">
          <Field label="Search tests"><input placeholder="Code or name" {...inputProps(q, (v) => { setQ(v); setPage(1) })} /></Field>
          <button type="button" onClick={load}>Search</button>
        </div>
        {loading ? <p className="muted">Loading…</p> : tests.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Code</th><th>Name</th><th>Department</th><th>Price</th><th>Delivery</th><th>Active</th>{canEdit ? <th></th> : null}</tr></thead>
              <tbody>
                {tests.map((t) => (
                  <tr key={t.test_code}>
                    <td>{t.test_code}</td>
                    <td>{t.test_name}</td>
                    <td>{t.department ? t.department.name : '—'}</td>
                    <td>{money(t.price)}</td>
                    <td>{t.expected_delivery_time}</td>
                    <td>{t.is_active ? 'Yes' : 'No'}</td>
                    {canEdit ? (
                      <td><button type="button" className="small" onClick={() => toggleTest(t)}>{t.is_active ? 'Deactivate' : 'Activate'}</button></td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={tests.length === PAGE_SIZE} />
      </div>
    </div>
  )
}
