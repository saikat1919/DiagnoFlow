import { useCallback, useEffect, useState } from 'react'
import { api, money, qs, userRole } from '../api.js'
import { Badge, ConfirmButton, Empty, ErrorBanner, Field, Pager, inputProps } from '../ui.jsx'

const PAGE_SIZE = 20
const DOSAGE_FORMS = ['tablet', 'capsule', 'syrup', 'injection', 'cream', 'drops', 'ointment', 'other']
const BATCH_STATUSES = ['active', 'blocked', 'damaged', 'returned']
const MOVEMENT_TYPES = ['damaged', 'returned', 'adjusted']

/* ---------------- Pharmacy (patient browse-only) ---------------- */

// Patients may search the pharmacy for medicines and see selling prices.
// No supplier information, no stock/cost data, no forms: buying happens
// at the pharmacy counter, through staff.
export function PharmacyView() {
  const [rows, setRows] = useState([])
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api(`/medicines${qs({ q, page, page_size: PAGE_SIZE })}`)
      setRows(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [q, page])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <h2>Pharmacy</h2>
      <p className="lead">Browse the medicines available at the pharmacy, with selling prices. Buying happens at the pharmacy counter.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />
      <div className="card">
        <div className="toolbar">
          <Field label="Search medicines"><input placeholder="Brand or generic name" {...inputProps(q, (v) => { setQ(v); setPage(1) })} /></Field>
          <button type="button" onClick={load}>Search</button>
        </div>
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Brand</th><th>Generic</th><th>Strength</th><th>Form</th><th>Price</th></tr></thead>
              <tbody>
                {rows.map((m) => (
                  <tr key={m.id}>
                    <td>{m.brand_name}</td>
                    <td>{m.generic_name}</td>
                    <td>{m.strength}</td>
                    <td><Badge value={m.dosage_form} /></td>
                    <td>{money(m.selling_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={rows.length === PAGE_SIZE} />
      </div>
    </div>
  )
}

/* ---------------- Medicines + suppliers ---------------- */

export function MedicinesView({ user }) {
  const canPharmacy = ['PHARMACIST', 'PHARMACY_MANAGER'].includes(userRole(user))
  const [rows, setRows] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ brand_name: '', generic_name: '', strength: '', dosage_form: 'tablet', description: '', selling_price: '', reorder_level: '0' })
  const [supplierForm, setSupplierForm] = useState({ supplier_name: '', phone: '', email: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [meds, sups] = await Promise.all([
        api(`/medicines${qs({ q, page, page_size: PAGE_SIZE })}`),
        api('/suppliers?page_size=100').catch(() => []),
      ])
      setRows(Array.isArray(meds) ? meds : meds.items || [])
      setSuppliers(Array.isArray(sups) ? sups : sups.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [q, page])

  useEffect(() => { load() }, [load])

  async function createMedicine(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/medicines/add', {
        method: 'POST',
        body: {
          brand_name: form.brand_name,
          generic_name: form.generic_name,
          strength: form.strength,
          dosage_form: form.dosage_form,
          description: form.description || null,
          selling_price: String(form.selling_price),
          reorder_level: Number(form.reorder_level || 0),
        },
      })
      setForm({ brand_name: '', generic_name: '', strength: '', dosage_form: 'tablet', description: '', selling_price: '', reorder_level: '0' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function createSupplier(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/suppliers/add', { method: 'POST', body: { ...supplierForm, email: supplierForm.email || null } })
      setSupplierForm({ supplier_name: '', phone: '', email: '' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function toggleMedicine(m) {
    setError('')
    try {
      const updated = await api(`/medicines/${m.id}`, { method: 'PATCH', body: { is_active: !m.is_active } })
      setRows((rs) => rs.map((x) => (x.id === m.id ? updated : x)))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>Medicines &amp; suppliers</h2>
      <p className="lead">Only pharmacy staff can add or change medicines and suppliers. The system admin cannot do pharmacy work.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      {canPharmacy ? (
        <div className="grid cols-2">
          <div className="card">
            <h3>Add a medicine</h3>
            <form onSubmit={createMedicine}>
              <div className="form-grid">
                <Field label="Brand name"><input required {...inputProps(form.brand_name, (v) => setForm({ ...form, brand_name: v }))} /></Field>
                <Field label="Generic name"><input required {...inputProps(form.generic_name, (v) => setForm({ ...form, generic_name: v }))} /></Field>
                <Field label="Strength"><input required placeholder="e.g. 500mg" {...inputProps(form.strength, (v) => setForm({ ...form, strength: v }))} /></Field>
                <Field label="Dosage form">
                  <select value={form.dosage_form} onChange={(e) => setForm({ ...form, dosage_form: e.target.value })}>
                    {DOSAGE_FORMS.map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </Field>
                <Field label="Selling price (BDT)"><input required type="number" min="0" step="0.01" {...inputProps(form.selling_price, (v) => setForm({ ...form, selling_price: v }))} /></Field>
                <Field label="Reorder level"><input type="number" min="0" {...inputProps(form.reorder_level, (v) => setForm({ ...form, reorder_level: v }))} /></Field>
                <Field label="Description"><input {...inputProps(form.description, (v) => setForm({ ...form, description: v }))} /></Field>
              </div>
              <button type="submit" className="primary">Add medicine</button>
            </form>
          </div>

          <div className="card">
            <h3>Add a supplier</h3>
            <form onSubmit={createSupplier}>
              <div className="form-grid">
                <Field label="Supplier name"><input required {...inputProps(supplierForm.supplier_name, (v) => setSupplierForm({ ...supplierForm, supplier_name: v }))} /></Field>
                <Field label="Phone"><input required {...inputProps(supplierForm.phone, (v) => setSupplierForm({ ...supplierForm, phone: v }))} /></Field>
                <Field label="Email (optional)"><input type="email" {...inputProps(supplierForm.email, (v) => setSupplierForm({ ...supplierForm, email: v }))} /></Field>
              </div>
              <button type="submit" className="primary">Add supplier</button>
            </form>
            <h3 style={{ marginTop: 20 }}>Suppliers</h3>
            {suppliers.length === 0 ? <Empty text="No suppliers." /> : (
              <ul>
                {suppliers.map((s) => <li key={s.id}>{s.supplier_name} — {s.phone}{s.email ? ` · ${s.email}` : ''}{!s.is_active ? ' (inactive)' : ''}</li>)}
              </ul>
            )}
          </div>
        </div>
      ) : null}

      <div className="card">
        <div className="toolbar">
          <Field label="Search medicines"><input placeholder="Brand or generic name" {...inputProps(q, (v) => { setQ(v); setPage(1) })} /></Field>
          <button type="button" onClick={load}>Search</button>
        </div>
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Brand</th><th>Generic</th><th>Strength</th><th>Form</th><th>Price</th><th>Reorder</th><th>Active</th>{canPharmacy ? <th></th> : null}</tr></thead>
              <tbody>
                {rows.map((m) => (
                  <tr key={m.id}>
                    <td>{m.brand_name}</td>
                    <td>{m.generic_name}</td>
                    <td>{m.strength}</td>
                    <td><Badge value={m.dosage_form} /></td>
                    <td>{money(m.selling_price)}</td>
                    <td>{m.reorder_level}</td>
                    <td>{m.is_active ? 'Yes' : 'No'}</td>
                    {canPharmacy ? (
                      <td><button type="button" className="small" onClick={() => toggleMedicine(m)}>{m.is_active ? 'Deactivate' : 'Activate'}</button></td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={rows.length === PAGE_SIZE} />
      </div>
    </div>
  )
}

/* ---------------- Inventory ---------------- */

export function InventoryView({ user }) {
  const canPharmacy = ['PHARMACIST', 'PHARMACY_MANAGER'].includes(userRole(user))
  const [batches, setBatches] = useState([])
  const [lowStock, setLowStock] = useState([])
  const [expiring, setExpiring] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [medicines, setMedicines] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [form, setForm] = useState({ medicine_id: '', supplier_id: '', batch_no: '', expiry_date: '', quantity_received: '', purchase_price: '' })
  const [moveForm, setMoveForm] = useState({ batch_id: '', movement_type: 'damaged', quantity: '' })
  const [movements, setMovements] = useState([])
  const [stockQuery, setStockQuery] = useState({ medicine_id: '', result: null })

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [bs, low, exp] = await Promise.all([
        api(`/inventory/batches${qs({ page, page_size: PAGE_SIZE })}`),
        api('/inventory/batches/low-stock').catch(() => []),
        api('/inventory/batches/expiring?days=30').catch(() => []),
      ])
      setBatches(Array.isArray(bs) ? bs : bs.items || [])
      setLowStock(Array.isArray(low) ? low : low.items || [])
      setExpiring(Array.isArray(exp) ? exp : exp.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    api('/medicines?page_size=100').then(setMedicines).catch(() => {})
    api('/suppliers?page_size=100').then(setSuppliers).catch(() => {})
  }, [])

  async function createBatch(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/inventory/batches/add', {
        method: 'POST',
        body: { ...form, quantity_received: Number(form.quantity_received), purchase_price: String(form.purchase_price) },
      })
      setForm({ medicine_id: '', supplier_id: '', batch_no: '', expiry_date: '', quantity_received: '', purchase_price: '' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function createMovement(e) {
    e.preventDefault()
    setError('')
    try {
      await api('/inventory/movements/add', {
        method: 'POST',
        body: { ...moveForm, quantity: Number(moveForm.quantity) },
      })
      setMoveForm({ batch_id: '', movement_type: 'damaged', quantity: '' })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function showMovements(batchId) {
    setError('')
    try {
      const data = await api(`/inventory/movements/batch/${batchId}?page_size=20`)
      setMovements(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    }
  }

  async function checkStock() {
    if (!stockQuery.medicine_id) return
    setError('')
    try {
      const data = await api(`/inventory/stock/${stockQuery.medicine_id}`)
      setStockQuery((s) => ({ ...s, result: data }))
    } catch (e) {
      setError(e.message)
    }
  }

  async function setBatchStatus(batch, status) {
    setError('')
    try {
      const updated = await api(`/inventory/batches/${batch.id}`, { method: 'PATCH', body: { status } })
      setBatches((bs) => bs.map((b) => (b.id === batch.id ? updated : b)))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>Inventory</h2>
      <p className="lead">Batches, usable stock (active, unexpired, in stock), movements and low-stock alerts.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      <div className="grid cols-2">
        <div className="card">
          <h3>Low stock</h3>
          {lowStock.length === 0 ? <p className="muted">Nothing below reorder level.</p> : (
            <ul>
              {lowStock.map((r, i) => <li key={i}>{r.medicine.brand_name} {r.medicine.strength} — usable stock {r.usable_stock}, reorder at {r.reorder_level}</li>)}
            </ul>
          )}
          <h3 style={{ marginTop: 18 }}>Check usable stock</h3>
          <div className="form-grid">
            <Field label="Medicine">
              <select value={stockQuery.medicine_id} onChange={(e) => setStockQuery({ ...stockQuery, medicine_id: e.target.value })}>
                <option value="">Select…</option>
                {medicines.map((m) => <option key={m.id} value={m.id}>{m.brand_name} {m.strength}</option>)}
              </select>
            </Field>
          </div>
          <button type="button" onClick={checkStock}>Check stock</button>
          {stockQuery.result ? <p style={{ marginTop: 10 }}>Usable stock: <strong>{stockQuery.result.usable_stock}</strong></p> : null}
        </div>

        {canPharmacy ? (
          <div className="card">
            <h3>Add a batch</h3>
            <form onSubmit={createBatch}>
              <div className="form-grid">
                <Field label="Medicine">
                  <select required value={form.medicine_id} onChange={(e) => setForm({ ...form, medicine_id: e.target.value })}>
                    <option value="">Select…</option>
                    {medicines.map((m) => <option key={m.id} value={m.id}>{m.brand_name} {m.strength}</option>)}
                  </select>
                </Field>
                <Field label="Supplier">
                  <select required value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}>
                    <option value="">Select…</option>
                    {suppliers.map((s) => <option key={s.id} value={s.id}>{s.supplier_name}</option>)}
                  </select>
                </Field>
                <Field label="Batch no."><input required {...inputProps(form.batch_no, (v) => setForm({ ...form, batch_no: v }))} /></Field>
                <Field label="Expiry date" hint="Must be in the future"><input required type="date" {...inputProps(form.expiry_date, (v) => setForm({ ...form, expiry_date: v }))} /></Field>
                <Field label="Quantity received"><input required type="number" min="1" {...inputProps(form.quantity_received, (v) => setForm({ ...form, quantity_received: v }))} /></Field>
                <Field label="Purchase price (BDT)"><input required type="number" min="0" step="0.01" {...inputProps(form.purchase_price, (v) => setForm({ ...form, purchase_price: v }))} /></Field>
              </div>
              <button type="submit" className="primary">Add batch</button>
            </form>
          </div>
        ) : null}
      </div>

      {canPharmacy ? (
        <div className="card">
          <h3>Record a stock movement</h3>
          <p className="muted">Damaged and returned quantities are negative (stock leaves); adjusted can be positive or negative. Sales and purchase receipts create their own movements — do not record those here.</p>
          <form onSubmit={createMovement}>
            <div className="form-grid">
              <Field label="Batch">
                <select required value={moveForm.batch_id} onChange={(e) => setMoveForm({ ...moveForm, batch_id: e.target.value })}>
                  <option value="">Select…</option>
                  {batches.map((b) => <option key={b.id} value={b.id}>{b.batch_no} — {b.medicine.brand_name} {b.medicine.strength} (in stock {b.quantity_in_stock})</option>)}
                </select>
              </Field>
              <Field label="Type">
                <select value={moveForm.movement_type} onChange={(e) => setMoveForm({ ...moveForm, movement_type: e.target.value })}>
                  {MOVEMENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </Field>
              <Field label="Quantity"><input required type="number" {...inputProps(moveForm.quantity, (v) => setMoveForm({ ...moveForm, quantity: v }))} /></Field>
            </div>
            <button type="submit" className="primary">Record movement</button>
          </form>
          {movements.length ? (
            <div style={{ marginTop: 14 }}>
              <h3>Recent movements for the selected batch</h3>
              <ul>
                {movements.map((m) => <li key={m.id}>{m.movement_type} {m.quantity} — {String(m.created_at).slice(0, 16).replace('T', ' ')}</li>)}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="card">
        <h3>Batches</h3>
        {loading ? <p className="muted">Loading…</p> : batches.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Batch</th><th>Medicine</th><th>Supplier</th><th>Expiry</th><th>Received</th><th>In stock</th><th>Price</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {batches.map((b) => (
                  <tr key={b.id}>
                    <td>{b.batch_no}</td>
                    <td>{b.medicine.brand_name} {b.medicine.strength}</td>
                    <td>{b.supplier.supplier_name}</td>
                    <td>{b.expiry_date}</td>
                    <td>{b.quantity_received}</td>
                    <td>{b.quantity_in_stock}</td>
                    <td>{money(b.purchase_price)}</td>
                    <td><Badge value={b.status} /></td>
                    <td>
                      <div className="row-actions">
                        <button type="button" className="small" onClick={() => showMovements(b.id)}>Movements</button>
                        {canPharmacy ? (
                          <select aria-label="Batch status" value={b.status} onChange={(e) => setBatchStatus(b, e.target.value)} style={{ width: 'auto' }}>
                            {BATCH_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                          </select>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} setPage={setPage} hasMore={batches.length === PAGE_SIZE} />
        <p className="muted">Expiring within 30 days: {expiring.length} batch(es).</p>
      </div>
    </div>
  )
}

/* ---------------- Purchases ---------------- */

const PURCHASE_STATUSES = ['ordered', 'partially_received', 'received', 'cancelled']
const PURCHASE_PAYMENTS = ['unpaid', 'paid', 'partially_paid']

export function PurchasesView({ user }) {
  const canPharmacy = ['PHARMACIST', 'PHARMACY_MANAGER'].includes(userRole(user))
  const [rows, setRows] = useState([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [medicines, setMedicines] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [form, setForm] = useState({ supplier_id: '', expected_delivery: '', items: [] })
  const [itemDraft, setItemDraft] = useState({ medicine_id: '', quantity_ordered: '', unit_cost: '' })
  const [selected, setSelected] = useState(null)
  const [receiveDraft, setReceiveDraft] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api(`/purchases${qs({ page, page_size: PAGE_SIZE })}`)
      setRows(Array.isArray(data) ? data : data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    api('/medicines?page_size=100').then(setMedicines).catch(() => {})
    api('/suppliers?page_size=100').then(setSuppliers).catch(() => {})
  }, [])

  async function createOrder(e) {
    e.preventDefault()
    setError('')
    if (!form.items.length) {
      setError('Add at least one medicine to the order.')
      return
    }
    try {
      await api('/purchases/add', {
        method: 'POST',
        body: {
          supplier_id: form.supplier_id,
          expected_delivery: form.expected_delivery || null,
          items: form.items.map((it) => ({ medicine_id: it.medicine_id, quantity_ordered: Number(it.quantity_ordered), unit_cost: String(it.unit_cost) })),
        },
      })
      setForm({ supplier_id: '', expected_delivery: '', items: [] })
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  async function receive(order) {
    setError('')
    const items = order.items
      .filter((it) => receiveDraft[it.id])
      .map((it) => ({
        purchase_order_item_id: it.id,
        quantity_received: Number(receiveDraft[it.id].quantity_received),
        batch_no: receiveDraft[it.id].batch_no,
        expiry_date: receiveDraft[it.id].expiry_date,
      }))
    if (!items.length) {
      setError('Fill in at least one received item (quantity, batch no. and expiry date).')
      return
    }
    try {
      const updated = await api(`/purchases/${order.id}/receive`, { method: 'POST', body: { items } })
      setSelected(updated)
      setReceiveDraft({})
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  async function patchOrder(order, endpoint, body) {
    setError('')
    try {
      const updated = await api(`/purchases/${order.id}/${endpoint}`, { method: 'PATCH', body })
      setSelected(updated)
      load()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h2>Purchases</h2>
      <p className="lead">Buy medicine from suppliers. Receiving creates batches and stock movements. Only pharmacy staff can buy.</p>
      <ErrorBanner error={error} onClose={() => setError('')} />

      {canPharmacy ? (
        <div className="card">
          <h3>Create a purchase order</h3>
          <form onSubmit={createOrder}>
            <div className="form-grid">
              <Field label="Supplier">
                <select required value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}>
                  <option value="">Select…</option>
                  {suppliers.map((s) => <option key={s.id} value={s.id}>{s.supplier_name}</option>)}
                </select>
              </Field>
              <Field label="Expected delivery" hint="Optional, cannot be in the past"><input type="date" {...inputProps(form.expected_delivery, (v) => setForm({ ...form, expected_delivery: v }))} /></Field>
            </div>
            <div className="form-grid">
              <Field label="Medicine">
                <select value={itemDraft.medicine_id} onChange={(e) => setItemDraft({ ...itemDraft, medicine_id: e.target.value })}>
                  <option value="">Select…</option>
                  {medicines.map((m) => <option key={m.id} value={m.id}>{m.brand_name} {m.strength}</option>)}
                </select>
              </Field>
              <Field label="Quantity"><input type="number" min="1" {...inputProps(itemDraft.quantity_ordered, (v) => setItemDraft({ ...itemDraft, quantity_ordered: v }))} /></Field>
              <Field label="Unit cost (BDT)"><input type="number" min="0" step="0.01" {...inputProps(itemDraft.unit_cost, (v) => setItemDraft({ ...itemDraft, unit_cost: v }))} /></Field>
            </div>
            <button
              type="button"
              onClick={() => {
                if (!itemDraft.medicine_id || !itemDraft.quantity_ordered || !itemDraft.unit_cost) return
                setForm((f) => ({ ...f, items: [...f.items, itemDraft] }))
                setItemDraft({ medicine_id: '', quantity_ordered: '', unit_cost: '' })
              }}
            >
              Add item
            </button>
            {form.items.length ? (
              <ul>
                {form.items.map((it, i) => {
                  const m = medicines.find((x) => x.id === it.medicine_id)
                  return <li key={i}>{m ? `${m.brand_name} ${m.strength}` : it.medicine_id} — {it.quantity_ordered} × {money(it.unit_cost)}</li>
                })}
              </ul>
            ) : null}
            <div style={{ marginTop: 10 }}>
              <button type="submit" className="primary">Create purchase order</button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="card">
        {loading ? <p className="muted">Loading…</p> : rows.length === 0 ? <Empty /> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Purchase no.</th><th>Supplier</th><th>Date</th><th>Status</th><th>Payment</th><th>Total</th><th></th></tr></thead>
              <tbody>
                {rows.map((o) => (
                  <tr key={o.id}>
                    <td>{o.purchase_no}</td>
                    <td>{o.supplier.supplier_name}</td>
                    <td>{String(o.order_date).slice(0, 10)}</td>
                    <td><Badge value={o.status} /></td>
                    <td><Badge value={o.payment_status} /></td>
                    <td>{money(o.total_amount)}</td>
                    <td>
                      <button type="button" className="small" onClick={async () => {
                        try { setSelected(await api(`/purchases/${o.id}`)) } catch (e) { setError(e.message) }
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
          <h3>{selected.purchase_no} — <Badge value={selected.status} /> <Badge value={selected.payment_status} /></h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Medicine</th><th>Ordered</th><th>Received</th><th>Unit cost</th>{canPharmacy && selected.status !== 'cancelled' && selected.status !== 'received' ? <th>Receive now</th> : null}</tr></thead>
              <tbody>
                {selected.items.map((it) => (
                  <tr key={it.id}>
                    <td>{it.medicine.brand_name} {it.medicine.strength}</td>
                    <td>{it.quantity_ordered}</td>
                    <td>{it.quantity_received}</td>
                    <td>{money(it.unit_cost)}</td>
                    {canPharmacy && selected.status !== 'cancelled' && selected.status !== 'received' ? (
                      <td>
                        <div className="form-grid" style={{ minWidth: 300 }}>
                          <Field label="Qty"><input type="number" min="1" value={receiveDraft[it.id]?.quantity_received || ''} onChange={(e) => setReceiveDraft({ ...receiveDraft, [it.id]: { ...receiveDraft[it.id], quantity_received: e.target.value } })} /></Field>
                          <Field label="Batch no."><input value={receiveDraft[it.id]?.batch_no || ''} onChange={(e) => setReceiveDraft({ ...receiveDraft, [it.id]: { ...receiveDraft[it.id], batch_no: e.target.value } })} /></Field>
                          <Field label="Expiry"><input type="date" value={receiveDraft[it.id]?.expiry_date || ''} onChange={(e) => setReceiveDraft({ ...receiveDraft, [it.id]: { ...receiveDraft[it.id], expiry_date: e.target.value } })} /></Field>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {canPharmacy ? (
            <div className="row-actions" style={{ marginTop: 12 }}>
              {selected.status !== 'cancelled' && selected.status !== 'received' ? (
                <button type="button" className="primary" onClick={() => receive(selected)}>Receive filled items</button>
              ) : null}
              <select aria-label="Payment status" value={selected.payment_status} onChange={(e) => patchOrder(selected, 'payment', { payment_status: e.target.value })} style={{ width: 'auto' }}>
                {PURCHASE_PAYMENTS.map((s) => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}
              </select>
              {selected.status !== 'cancelled' && selected.status !== 'received' ? (
                <ConfirmButton label="Cancel order" className="danger" onConfirm={() => patchOrder(selected, 'cancel')} />
              ) : null}
              <button type="button" onClick={() => setSelected(null)}>Close</button>
            </div>
          ) : null}
          <p className="muted">Cancelling a partly received order keeps the stock already received.</p>
        </div>
      ) : null}
    </div>
  )
}
