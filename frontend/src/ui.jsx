import { useState } from 'react'

export function Badge({ value }) {
  if (value === null || value === undefined || value === '') return <span>—</span>
  return <span className="badge">{String(value).replaceAll('_', ' ')}</span>
}

export function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint ? <span className="hint">{hint}</span> : null}
    </label>
  )
}

export function inputProps(value, onChange, extra = {}) {
  return { value: value ?? '', onChange: (e) => onChange(e.target.value), ...extra }
}

export function ErrorBanner({ error, onClose }) {
  if (!error) return null
  return (
    <div className="error-banner" role="alert">
      <span>{error}</span>
      {onClose ? (
        <button type="button" className="link-btn" onClick={onClose}>
          Dismiss
        </button>
      ) : null}
    </div>
  )
}

export function Empty({ text }) {
  return <p className="empty">{text || 'No records found.'}</p>
}

export function Pager({ page, setPage, hasMore }) {
  return (
    <div className="pager">
      <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
        Previous
      </button>
      <span>Page {page}</span>
      <button type="button" disabled={!hasMore} onClick={() => setPage(page + 1)}>
        Next
      </button>
    </div>
  )
}

export function ConfirmButton({ label, confirmLabel = 'Click again to confirm', onConfirm, className = '' }) {
  const [armed, setArmed] = useState(false)
  return (
    <button
      type="button"
      className={className}
      onClick={() => {
        if (armed) {
          setArmed(false)
          onConfirm()
        } else {
          setArmed(true)
          setTimeout(() => setArmed(false), 4000)
        }
      }}
    >
      {armed ? confirmLabel : label}
    </button>
  )
}
