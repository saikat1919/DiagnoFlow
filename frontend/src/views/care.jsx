import { useCallback, useEffect, useRef, useState } from 'react'
import { api, apiForm, fullName, money, qs, todayISO, userRole } from '../api.js'
import { Badge, ConfirmButton, Empty, ErrorBanner, Field, Pager, inputProps } from '../ui.jsx'

const PAGE_SIZE = 20
const PAYMENT_METHODS = ['cash', 'bkash', 'card', 'other']

/* ---------------- Prescriptions ---------------- */

export function PrescriptionsView({ user }) {
  const isPatient = userRole(user) === 'PATIENT'
  const canPharmacy = ['PHARMACIST', 'PHARMACY_MANAGER'].includes(userRole(user))
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [patients, setPatients] = useState([])
  const [medicines, setMedicines] = useState([])
  const [form, setForm] = useState({ patient_id: '', prescriber_name: '', prescription_date: todayISO(), notes: '', items: [] })
  const [itemDraft, setItemDraft] = useState({ medicine_name: '', strength: '', instructions: '', quantity_prescribed: '' })
  const [selected, setSelected] = useState(null)
  const [matchDraft, setMatchDraft] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const path = isPatient
        ? `/prescriptions/me${qs({ page, page_size: PAGE_SIZE })}`
        : `/prescriptions${qs({ page, page_size: PAGE_SIZE })}`
      const data = await api(path)
      setRows(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [isPatient, page])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (isPatient) return
    api('/patients?page_size=100').then(setPatients).catch(() => {})
    api('/medicines?page_size=100').then(setMedicines).catch(() => {})
  }, [isPatient])

  async function createPrescription(e) {
    e.preventDefault()
    setError('')
    if (!form.items.length) {
      setError('Add at least one prescribed item.')
      return
    }
    try {
      await api('/prescriptions/add', {
        method: 'POST',
        body: { ...form, notes: form.notes || null, items: form.items.map((it) => ({ ...it, quantity_prescribed: Number(it.quantity_prescribed), strength: it.strength || null, instructions: it.instructions || null })) },
      })
      setForm({ patient_id: '', prescriber_name: '', prescription_date: todayISO(), notes: '', items: [] })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function refreshSelected(id) {
    try {
      const fresh = isPatient ? await api(`/prescriptions/me/${id}`) : await api(`/prescriptions/${id}`)
      setSelected(fresh)
      setRows((rs) => rs.map((r) => (r.id === id ? fresh : r)))
    } catch (e) {
      setError(e.message)
    }
  }

  async function matchItem(item) {
    const medicineId = matchDraft[item.id]
    if (!medicineId) return
    setError('')
    try {
      await api(`/prescriptions/items/${item.id}/match`, { method: 'PATCH', body: { medicine_id: medicineId } })
      await refreshSelected(selected.id)
    } catch (e) {
      setError(e.message)
    }
  }

  async function markNotAvailable(item) {
    setError('')
    try {
      await api(`/prescriptions/items/${item.id}/not-available`, { method: 'PATCH' })
      await refreshSelected(selected.id)
    } catch (e) {
      setError(e.message)
    }
  }

  async function cancelPrescription(p) {
    setError('')
    try {
      await api(`/prescriptions/${p.id}/cancel`, { method: 'PATCH' })
      setSelected(null)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>{isPatient ? 'My prescriptions' : 'Prescriptions'}</h2>
      <p className="lead">Items start unmatched. Pharmacy matches each item to a medicine; delivery happens only through a sale.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      {!isPatient ? (
        <div className="card">
          <h3>Record a prescription</h3>
          <form onSubmit={createPrescription}>
            <div className="form-grid">
              <Field label="Patient">
                <select required value={form.patient_id} onChange={(e) => setForm({ ...form, patient_id: e.target.value })}>
                  <option value="">Select…</option>
                  {patients.map((p) => <option key={p.id} value={p.id}>{fullName(p)} — {p.patient_no}</option>)}
                </select>
              </Field>
              <Field label="Prescriber name"><input required {...inputProps(form.prescriber_name, (v) => setForm({ ...form, prescriber_name: v }))} /></Field>
              <Field label="Prescription date"><input required type="date" {...inputProps(form.prescription_date, (v) => setForm({ ...form, prescription_date: v }))} /></Field>
              <Field label="Notes"><input {...inputProps(form.notes, (v) => setForm({ ...form, notes: v }))} /></Field>
            </div>
            <div className="form-grid">
              <Field label="Medicine name (as written)"><input value={itemDraft.medicine_name} onChange={(e) => setItemDraft({ ...itemDraft, medicine_name: e.target.value })} /></Field>
              <Field label="Strength"><input {...inputProps(itemDraft.strength, (v) => setItemDraft({ ...itemDraft, strength: v }))} /></Field>
              <Field label="Instructions"><input {...inputProps(itemDraft.instructions, (v) => setItemDraft({ ...itemDraft, instructions: v }))} /></Field>
              <Field label="Quantity"><input type="number" min="1" {...inputProps(itemDraft.quantity_prescribed, (v) => setItemDraft({ ...itemDraft, quantity_prescribed: v }))} /></Field>
            </div>
            <button
              type="button"
              onClick={() => {
                if (!itemDraft.medicine_name || !itemDraft.quantity_prescribed) return
                setForm((f) => ({ ...f, items: [...f.items, itemDraft] }))
                setItemDraft({ medicine_name: '', strength: '', instructions: '', quantity_prescribed: '' })
              }}
            >
              Add item
            </button>
            {form.items.length ? (
              <ul>
                {form.items.map((it, i) => <li key={i}>{it.medicine_name} {it.strength || ''} — {it.quantity_prescribed}</li>)}
              </ul>
            ) : null}
            <div style={{ marginTop: 10 }}>
              <button type="submit" className="primary">Record prescription</button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="card">
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Patient</th><th>Prescriber</th><th>Date</th><th>Status</th><th>Items</th><th></th></tr></thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <td>{p.patient ? fullName(p.patient) : 'You'}</td>
                    <td>{p.prescriber_name}</td>
                    <td>{p.prescription_date}</td>
                    <td><Badge value={p.status} /></td>
                    <td>{p.items.length}</td>
                    <td>
                      <button type="button" className="small" onClick={async () => {
                        try { setSelected(isPatient ? await api(`/prescriptions/me/${p.id}`) : await api(`/prescriptions/${p.id}`)) } catch (e) { setError(e.message) }
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
          <h3>Prescription — <Badge value={selected.status} /></h3>
          <p className="muted">{selected.prescriber_name} · {selected.prescription_date}{selected.notes ? ` · ${selected.notes}` : ''}</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Medicine</th><th>Strength</th><th>Prescribed</th><th>Delivered</th><th>Status</th>{canPharmacy ? <th>Match / mark</th> : null}</tr></thead>
              <tbody>
                {selected.items.map((it) => (
                  <tr key={it.id}>
                    <td>{it.medicine ? `${it.medicine.brand_name} ${it.medicine.strength}` : it.medicine_name}</td>
                    <td>{it.strength || '—'}</td>
                    <td>{it.quantity_prescribed}</td>
                    <td>{it.quantity_delivered}</td>
                    <td><Badge value={it.dispense_status} /></td>
                    {canPharmacy ? (
                      <td>
                        <div className="row-actions">
                          <select aria-label="Match medicine" value={matchDraft[it.id] || ''} onChange={(e) => setMatchDraft({ ...matchDraft, [it.id]: e.target.value })} style={{ width: 'auto' }}>
                            <option value="">Match to…</option>
                            {medicines.map((m) => <option key={m.id} value={m.id}>{m.brand_name} {m.strength}</option>)}
                          </select>
                          <button type="button" className="small" disabled={!matchDraft[it.id] || it.quantity_delivered > 0} onClick={() => matchItem(it)}>Match</button>
                          <button type="button" className="small" disabled={it.quantity_delivered > 0} onClick={() => markNotAvailable(it)}>Not available</button>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row-actions" style={{ marginTop: 12 }}>
            {canPharmacy && selected.status !== 'dispensed' && selected.status !== 'cancelled' ? (
              <ConfirmButton label="Cancel prescription" className="danger" onConfirm={() => cancelPrescription(selected)} />
            ) : null}
            <button type="button" onClick={() => setSelected(null)}>Close</button>
          </div>
          <p className="muted">If an item was marked not available and then matched, tell pharmacy: the backend may keep it marked not available until the match fix is applied.</p>
        </div>
      ) : null}
    </div>
  )
}

/* ---------------- Sales ---------------- */

export function SalesView({ user }) {
  const isPatient = userRole(user) === 'PATIENT'
  const canPharmacy = ['PHARMACIST', 'PHARMACY_MANAGER'].includes(userRole(user))
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [medicines, setMedicines] = useState([])
  const [patients, setPatients] = useState([])
  const [prescriptions, setPrescriptions] = useState([])
  const [totals, setTotals] = useState(null)
  const [form, setForm] = useState({ patient_id: '', prescription_id: '', discount: '0', payment_method: '', payment_status: 'pending', lines: [] })
  const [lineDraft, setLineDraft] = useState({ medicine_id: '', quantity: '', batch_id: '' })
  const [batches, setBatches] = useState([])
  const [selected, setSelected] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const path = isPatient
        ? `/sales/me${qs({ page, page_size: PAGE_SIZE })}`
        : `/sales${qs({ page, page_size: PAGE_SIZE })}`
      const data = await api(path)
      setRows(Array.isArray(data) ? data : data.items || [])
      if (!isPatient) {
        const today = todayISO()
        const t = await api(`/sales/daily-totals?date_from=${today}&date_to=${today}`).catch(() => [])
        setTotals(t[0] || null)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [isPatient, page])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (isPatient) return
    api('/medicines?page_size=100').then(setMedicines).catch(() => {})
    api('/patients?page_size=100').then(setPatients).catch(() => {})
    api('/prescriptions?page_size=100').then(setPrescriptions).catch(() => {})
  }, [isPatient])

  useEffect(() => {
    if (!lineDraft.medicine_id) { setBatches([]); return }
    api(`/inventory/batches${qs({ medicine_id: lineDraft.medicine_id, in_stock_only: true, page_size: 50 })}`)
      .then(setBatches)
      .catch(() => setBatches([]))
  }, [lineDraft.medicine_id])

  const lineTotal = form.lines.reduce((sum, ln) => {
    const m = medicines.find((x) => x.id === ln.medicine_id)
    return sum + (m ? Number(m.selling_price) * Number(ln.quantity) : 0)
  }, 0)

  async function createSale(e) {
    e.preventDefault()
    setError('')
    if (!form.lines.length) {
      setError('Add at least one medicine line.')
      return
    }
    try {
      await api('/sales/add', {
        method: 'POST',
        body: {
          patient_id: form.patient_id || null,
          prescription_id: form.prescription_id || null,
          discount: String(form.discount || '0'),
          payment_method: form.payment_status === 'paid' ? form.payment_method : (form.payment_method || null),
          payment_status: form.payment_status,
          items: form.lines.map((ln) => ({ medicine_id: ln.medicine_id, quantity: Number(ln.quantity), batch_id: ln.batch_id || null })),
        },
      })
      setForm({ patient_id: '', prescription_id: '', discount: '0', payment_method: '', payment_status: 'pending', lines: [] })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function updatePayment(sale, payment_status, payment_method) {
    setError('')
    try {
      const updated = await api(`/sales/${sale.id}/payment`, { method: 'PATCH', body: { payment_status, payment_method: payment_method || null } })
      setRows((rs) => rs.map((r) => (r.id === sale.id ? updated : r)))
      if (selected && selected.id === sale.id) setSelected(updated)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>{isPatient ? 'My purchases' : 'Sales'}</h2>
      <p className="lead">{isPatient ? 'Your pharmacy purchases.' : 'Sales use first-expiry-first-out stock unless you pick a batch. There is no cancel or return for a sale.'}</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      {!isPatient && totals ? (
        <div className="card stat">
          <div className="label">Today&apos;s sales</div>
          <div className="value">{money(totals.total_amount)}</div>
          <div className="sub">{totals.sale_count} sales · paid {money(totals.paid_amount)}</div>
        </div>
      ) : null}

      {canPharmacy ? (
        <div className="card">
          <h3>New sale</h3>
          <form onSubmit={createSale}>
            <div className="form-grid">
              <Field label="Patient (optional, required for prescription sales)">
                <select value={form.patient_id} onChange={(e) => setForm({ ...form, patient_id: e.target.value })}>
                  <option value="">Walk-in (no patient)</option>
                  {patients.map((p) => <option key={p.id} value={p.id}>{fullName(p)} — {p.patient_no}</option>)}
                </select>
              </Field>
              <Field label="Prescription (optional)">
                <select value={form.prescription_id} onChange={(e) => setForm({ ...form, prescription_id: e.target.value })}>
                  <option value="">None</option>
                  {prescriptions.filter((p) => p.status !== 'cancelled').map((p) => <option key={p.id} value={p.id}>{p.patient ? fullName(p.patient) : ''} — {p.prescriber_name} ({p.status})</option>)}
                </select>
              </Field>
              <Field label="Discount (BDT)"><input type="number" min="0" step="0.01" {...inputProps(form.discount, (v) => setForm({ ...form, discount: v }))} /></Field>
              <Field label="Payment status">
                <select value={form.payment_status} onChange={(e) => setForm({ ...form, payment_status: e.target.value })}>
                  <option value="pending">Pending</option>
                  <option value="paid">Paid</option>
                </select>
              </Field>
              {form.payment_status === 'paid' ? (
                <Field label="Payment method">
                  <select required value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
                    <option value="">Select…</option>
                    {PAYMENT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </Field>
              ) : null}
            </div>
            <div className="form-grid">
              <Field label="Medicine">
                <select value={lineDraft.medicine_id} onChange={(e) => setLineDraft({ ...lineDraft, medicine_id: e.target.value, batch_id: '' })}>
                  <option value="">Select…</option>
                  {medicines.map((m) => <option key={m.id} value={m.id}>{m.brand_name} {m.strength} — {money(m.selling_price)}</option>)}
                </select>
              </Field>
              <Field label="Quantity"><input type="number" min="1" {...inputProps(lineDraft.quantity, (v) => setLineDraft({ ...lineDraft, quantity: v }))} /></Field>
              <Field label="Batch (optional — leave empty for first-expiry-first-out)">
                <select value={lineDraft.batch_id} onChange={(e) => setLineDraft({ ...lineDraft, batch_id: e.target.value })}>
                  <option value="">Automatic (FEFO)</option>
                  {batches.map((b) => <option key={b.id} value={b.id}>{b.batch_no} — in stock {b.quantity_in_stock}, exp {b.expiry_date}</option>)}
                </select>
              </Field>
            </div>
            <button
              type="button"
              onClick={() => {
                if (!lineDraft.medicine_id || !lineDraft.quantity) return
                setForm((f) => ({ ...f, lines: [...f.lines, lineDraft] }))
                setLineDraft({ medicine_id: '', quantity: '', batch_id: '' })
              }}
            >
              Add line
            </button>
            {form.lines.length ? (
              <div style={{ marginTop: 10 }}>
                <ul>
                  {form.lines.map((ln, i) => {
                    const m = medicines.find((x) => x.id === ln.medicine_id)
                    return <li key={i}>{m ? `${m.brand_name} ${m.strength}` : ''} × {ln.quantity}{ln.batch_id ? ' (named batch)' : ' (FEFO)'}</li>
                  })}
                </ul>
                <p>Subtotal: <strong>{money(lineTotal)}</strong> · Total after discount: <strong>{money(Math.max(0, lineTotal - Number(form.discount || 0)))}</strong></p>
                <p className="muted">Do not mix a named batch and automatic stock for the same medicine in one sale — the backend can double-count that batch.</p>
              </div>
            ) : null}
            <div style={{ marginTop: 10 }}>
              <button type="submit" className="primary">Create sale</button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="card">
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Sale no.</th><th>Patient</th><th>Date</th><th>Subtotal</th><th>Discount</th><th>Total</th><th>Payment</th><th></th></tr></thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.id}>
                    <td>{s.sale_no}</td>
                    <td>{s.patient ? fullName(s.patient) : 'Walk-in'}</td>
                    <td>{String(s.sale_date).slice(0, 10)}</td>
                    <td>{money(s.subtotal)}</td>
                    <td>{money(s.discount)}</td>
                    <td>{money(s.total_amount)}</td>
                    <td><Badge value={s.payment_status} />{s.payment_method ? ` ${s.payment_method}` : ''}</td>
                    <td>
                      <div className="row-actions">
                        <button type="button" className="small" onClick={async () => {
                          try { setSelected(isPatient ? await api(`/sales/me/${s.id}`) : await api(`/sales/${s.id}`)) } catch (e) { setError(e.message) }
                        }}>
                          Details
                        </button>
                        {canPharmacy && s.payment_status === 'pending' ? (
                          <button type="button" className="small" onClick={() => updatePayment(s, 'paid', 'cash')}>Mark paid (cash)</button>
                        ) : null}
                      </div>
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
          <h3>Sale {selected.sale_no}</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Medicine</th><th>Batch</th><th>Qty</th><th>Unit price</th><th>Line total</th></tr></thead>
              <tbody>
                {selected.items.map((it) => (
                  <tr key={it.id}>
                    <td>{it.batch ? `${it.batch.medicine.brand_name} ${it.batch.medicine.strength}` : (it.medicine_name || '—')}</td>
                    <td>{it.batch ? it.batch.batch_no : '—'}</td>
                    <td>{it.quantity}</td>
                    <td>{money(it.unit_price)}</td>
                    <td>{money(it.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" onClick={() => setSelected(null)} style={{ marginTop: 10 }}>Close</button>
        </div>
      ) : null}
    </div>
  )
}

/* ---------------- Knowledge ---------------- */

export function KnowledgeView({ user }) {
  const isAdmin = userRole(user) === 'SYSTEM_ADMIN'
  const [q, setQ] = useState('')
  const [source, setSource] = useState('')
  const [hits, setHits] = useState([])
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')
  const [ingestResult, setIngestResult] = useState(null)
  const [chunks, setChunks] = useState([])
  const [chunkPage, setChunkPage] = useState({ page: 1, total: 0, page_size: 10 })
  const [chunkForm, setChunkForm] = useState({ source: 'policy', title: '', content: '' })

  async function search(e) {
    if (e) e.preventDefault()
    setError('')
    try {
      const data = await api(`/knowledge/search${qs({ q, source: source || undefined, limit: 5 })}`)
      setHits(Array.isArray(data) ? data : [])
      setSearched(true)
    } catch (err) {
      setError(err.message)
    }
  }

  const loadChunks = useCallback(async (page = 1) => {
    if (!isAdmin) return
    try {
      const data = await api(`/knowledge${qs({ page, page_size: 10 })}`)
      setChunks(data.items || [])
      setChunkPage({ page: data.page || page, total: data.total || 0, page_size: data.page_size || 10 })
    } catch (err) {
      setError(err.message)
    }
  }, [isAdmin])

  useEffect(() => { loadChunks(1) }, [loadChunks])

  async function ingest() {
    setError('')
    setIngestResult(null)
    try {
      const data = await api('/knowledge/ingest', { method: 'POST' })
      setIngestResult(data)
      loadChunks(1)
    } catch (e) {
      setError(e.message)
    }
  }

  async function createChunk(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/knowledge', { method: 'POST', body: chunkForm })
      setChunkForm({ source: 'policy', title: '', content: '' })
      loadChunks(1)
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteChunk(id) {
    setError('')
    try {
      await api(`/knowledge/${id}`, { method: 'DELETE' })
      loadChunks(chunkPage.page)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h2>Knowledge search</h2>
      <p className="lead">Search company policies, medicines and tests. This uses the embedded knowledge base — run ingest after changing policies, prices or the catalogue.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      <div className="card">
        <form onSubmit={search}>
          <div className="toolbar">
            <Field label="Search (at least 2 characters)"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. refund, napa, CBC" /></Field>
            <Field label="Source">
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="">All</option>
                <option value="policy">Policy</option>
                <option value="medicine">Medicine</option>
                <option value="test">Test</option>
              </select>
            </Field>
            <button type="submit" className="primary">Search</button>
          </div>
        </form>
        {searched && hits.length === 0 ? <Empty text="No matching sections. Check that ingest has run and the embedder is up." /> : null}
        {hits.map((h, i) => (
          <div className="detail" key={i}>
            <strong>{h.title}</strong> <span className="muted">({h.source})</span>
            <p style={{ whiteSpace: 'pre-wrap', margin: '6px 0 0' }}>{h.content}</p>
          </div>
        ))}
      </div>

      {isAdmin ? (
        <>
          <div className="card">
            <h3>Rebuild the knowledge base</h3>
            <p className="muted">Reads scripts/data/policies.md and the active medicines and tests from the database. Replaces only policy, medicine and test chunks — hand-written chunks survive.</p>
            <ConfirmButton label="Run ingest" className="primary" onConfirm={ingest} />
            {ingestResult ? <p style={{ marginTop: 10 }}>Policies: {ingestResult.policies} · Medicines: {ingestResult.medicines} · Tests: {ingestResult.tests} · Total: {ingestResult.total}</p> : null}
          </div>

          <div className="card">
            <h3>Add a hand-written chunk</h3>
            <form onSubmit={createChunk}>
              <div className="form-grid">
                <Field label="Source">
                  <select value={chunkForm.source} onChange={(e) => setChunkForm({ ...chunkForm, source: e.target.value })}>
                    <option value="policy">Policy</option>
                    <option value="medicine">Medicine</option>
                    <option value="test">Test</option>
                  </select>
                </Field>
                <Field label="Title"><input required {...inputProps(chunkForm.title, (v) => setChunkForm({ ...chunkForm, title: v }))} /></Field>
              </div>
              <Field label="Content"><textarea rows={4} required {...inputProps(chunkForm.content, (v) => setChunkForm({ ...chunkForm, content: v }))} /></Field>
              <div style={{ marginTop: 10 }}>
                <button type="submit" className="primary">Add chunk</button>
              </div>
            </form>
          </div>

          <div className="card">
            <h3>Chunks ({chunkPage.total})</h3>
            {chunks.length === 0 ? <Empty /> : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Source</th><th>Title</th><th>Content</th><th></th></tr></thead>
                  <tbody>
                    {chunks.map((c) => (
                      <tr key={c.id}>
                        <td><Badge value={c.source} /></td>
                        <td>{c.title}</td>
                        <td>{String(c.content).slice(0, 120)}{String(c.content).length > 120 ? '…' : ''}</td>
                        <td><ConfirmButton label="Delete" className="small danger" onConfirm={() => deleteChunk(c.id)} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <Pager page={chunkPage.page} setPage={(p) => loadChunks(p)} hasMore={chunks.length === chunkPage.page_size} />
          </div>
        </>
      ) : null}
    </div>
  )
}

/* ---------------- Chat ---------------- */

export function ChatView({ user }) {
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [imageFile, setImageFile] = useState(null)
  const [imagePreview, setImagePreview] = useState('')
  const imageInputRef = useRef(null)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  async function send(e) {
    e.preventDefault()
    const content = draft.trim()
    const file = imageFile
    if ((!content && !file) || busy) return
    setDraft('')
    setError('')
    const preview = imagePreview
    setMessages((ms) => [...ms, { role: 'user', content: content || 'Please read this image.', imageUrl: preview || undefined }])
    setImageFile(null)
    setImagePreview('')
    if (imageInputRef.current) imageInputRef.current.value = ''
    setBusy(true)
    try {
      const data = file
        ? await apiForm('/chat/image', (() => {
            const fd = new FormData()
            fd.append('file', file)
            fd.append('content', content)
            return fd
          })())
        : await api('/chat', { method: 'POST', body: { content } })
      const reply = (data.reply || '').trim()
      setMessages((ms) => [...ms, {
        role: 'assistant',
        content: reply || 'I got the information but could not write an answer. Please ask again in a simpler way.',
        toolCalls: data.tool_calls || [],
      }])
    } catch (err) {
      setError(err.message)
      setMessages((ms) => [...ms, { role: 'assistant', content: `I could not answer that: ${err.message}` }])
    } finally {
      setBusy(false)
    }
  }

  async function clearSession() {
    setError('')
    try {
      await api('/chat/session', { method: 'DELETE' })
    } catch (e) {
      // History is server-side and session-only; a failed clear is not fatal.
      setError(e.message)
    }
    setMessages([])
  }

  return (
    <div>
      <h2>Assistant</h2>
      <p className="lead">
        Signed in as {userRole(user).replaceAll('_', ' ')}. Staff see summaries only — no personal information. Patients see only their own report updates, plus medicine, policy and test searches.
      </p>
      <ErrorBanner error={error} onClose={() => setError('')} />
      <div className="card">
        <div className="chat-box">
          <div className="chat-log">
            {messages.length === 0 ? <p className="empty">Try: “How many patients are here today?” or “What is the price of a CBC test?”</p> : null}
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.imageUrl ? <img src={m.imageUrl} alt="Attached" style={{ maxWidth: '100%', borderRadius: 8, marginBottom: 6 }} /> : null}
                {m.content}
                {m.toolCalls && m.toolCalls.length ? (
                  <div className="tools">Used: {m.toolCalls.join(', ')}</div>
                ) : null}
              </div>
            ))}
            {busy ? <div className="msg assistant">Thinking…</div> : null}
            <div ref={endRef} />
          </div>
          <form className="chat-form" onSubmit={send}>
            <input ref={imageInputRef} type="file" accept="image/*" aria-label="Attach a picture" onChange={(e) => {
              const f = e.target.files[0] || null
              setImageFile(f)
              setImagePreview(f ? URL.createObjectURL(f) : '')
            }} />
            <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Ask about tests, medicines, policies or summaries…" maxLength={2000} />
            <button type="submit" className="primary" disabled={busy || (!draft.trim() && !imageFile)}>Send</button>
            <button type="button" onClick={clearSession}>Clear session</button>
          </form>
          {imagePreview ? <p className="muted">Attached: {imageFile ? imageFile.name : ''} — the assistant reads the photo directly. It is not stored.</p> : <p className="muted">You can attach a photo of a prescription — the assistant reads it and checks the medicines against the pharmacy.</p>}
        </div>
        <p className="muted">Chat history lives only while your login session lasts. Logging out or clearing the session removes it.</p>
      </div>
    </div>
  )
}
