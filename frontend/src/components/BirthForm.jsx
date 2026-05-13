import { useState } from 'react'

const API = import.meta.env.VITE_API_URL || ''

const FIELD_STYLES = {
  width: '100%',
  background: 'var(--bg-raised)',
  border: '1px solid rgba(180,155,100,0.22)',
  borderRadius: '8px',
  color: 'var(--cream)',
  fontFamily: 'var(--font-body)',
  fontSize: '16px',
  padding: '12px 16px',
  outline: 'none',
  transition: 'border-color 0.2s, box-shadow 0.2s',
}

const LABEL_STYLES = {
  display: 'block',
  fontFamily: 'var(--font-display)',
  fontSize: '12px',
  fontWeight: 500,
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--gold)',
  marginBottom: '7px',
}

const LANGUAGES = [
  'English', 'Hindi', 'Spanish', 'French', 'German', 'Italian', 'Portuguese',
  'Arabic', 'Chinese (Simplified)', 'Chinese (Traditional)', 'Japanese', 'Korean',
  'Russian', 'Dutch', 'Turkish', 'Bengali', 'Urdu', 'Tamil', 'Telugu', 'Marathi',
  'Gujarati', 'Punjabi', 'Malayalam', 'Kannada', 'Indonesian', 'Thai', 'Vietnamese',
  'Polish', 'Ukrainian', 'Persian', 'Swahili', 'Greek', 'Hebrew', 'Swedish',
  'Norwegian', 'Danish', 'Finnish', 'Czech', 'Romanian', 'Hungarian',
]

function Field({ label, required, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <label style={LABEL_STYLES}>
        {label}{required && <span style={{ color: 'var(--accent-rose)', marginLeft: 3 }}>*</span>}
      </label>
      {children}
    </div>
  )
}

export default function BirthForm({ onChartReady }) {
  const [form, setForm] = useState({
    name: '', dob: '', tob: '', pob: '', gender: '', language: 'English'
  })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [focused, setFocused] = useState(null)

  function onChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setError('')
  }

  async function onSubmit(e) {
    e.preventDefault()
    if (!form.dob || !form.tob || !form.pob) {
      setError('Please fill in Date of Birth, Time of Birth, and Place of Birth.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/api/chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to calculate chart')
      }
      onChartReady({ ...data, language: form.language })
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const focusStyle = (name) => focused === name
    ? { ...FIELD_STYLES, borderColor: 'var(--gold-dim)', boxShadow: '0 0 0 3px rgba(201,168,76,0.10)' }
    : FIELD_STYLES

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '80px 24px 24px',
      position: 'relative',
      zIndex: 1,
    }}>
      <div style={{
        width: '100%',
        maxWidth: '520px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '52px 48px',
        boxShadow: 'var(--shadow), var(--glow)',
        backdropFilter: 'blur(20px)',
      }}>

        {/* Language Selector */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          marginBottom: '28px',
          gap: '10px',
        }}>
          <span style={{
            fontFamily: 'var(--font-display)',
            fontSize: '11px',
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            color: 'var(--gold)',
            opacity: 0.75,
          }}>
            🌐 Language
          </span>
          <select
            name="language"
            value={form.language}
            onChange={onChange}
            onFocus={() => setFocused('language')}
            onBlur={() => setFocused(null)}
            style={{
              background: 'var(--bg-raised)',
              border: focused === 'language'
                ? '1px solid var(--gold-dim)'
                : '1px solid rgba(180,155,100,0.3)',
              borderRadius: '8px',
              color: 'var(--gold-light)',
              fontFamily: 'var(--font-body)',
              fontSize: '13px',
              padding: '7px 12px',
              outline: 'none',
              cursor: 'pointer',
              appearance: 'none',
              minWidth: '160px',
              boxShadow: focused === 'language' ? '0 0 0 3px rgba(201,168,76,0.10)' : 'none',
              transition: 'border-color 0.2s, box-shadow 0.2s',
            }}
          >
            {LANGUAGES.map(lang => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>
        </div>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '42px' }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: '13px',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            color: 'var(--gold)',
            marginBottom: '14px',
            opacity: 0.8,
          }}>
            ☽ Vedic Astrology ☽
          </div>
          <h1 style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(32px, 5vw, 44px)',
            fontWeight: 300,
            color: 'var(--cream)',
            lineHeight: 1.15,
            letterSpacing: '0.02em',
          }}>
            My Destiny
          </h1>
          <p style={{
            marginTop: '12px',
            color: 'var(--text-dim)',
            fontFamily: 'var(--font-body)',
            fontSize: '15px',
            lineHeight: 1.6,
          }}>
            Your stars. Your story. Your destiny.<br />
            <span style={{ fontSize: '13px', opacity: 0.75 }}>
              Enter your birth details for a personalised Vedic chart reading.
            </span>
          </p>
        </div>

        {/* Divider */}
        <div style={{
          height: '1px',
          background: 'linear-gradient(90deg, transparent, var(--border-glow), transparent)',
          marginBottom: '36px',
        }} />

        {/* Form */}
        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
          {/* Name */}
          <Field label="Your Name" required={false}>
            <input
              name="name" type="text" value={form.name}
              onChange={onChange} placeholder="Optional"
              onFocus={() => setFocused('name')} onBlur={() => setFocused(null)}
              style={focusStyle('name')}
            />
          </Field>

          {/* DOB + TOB row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <Field label="Date of Birth" required>
              <input
                name="dob" type="date" value={form.dob}
                onChange={onChange}
                onFocus={() => setFocused('dob')} onBlur={() => setFocused(null)}
                style={{ ...focusStyle('dob'), colorScheme: 'dark' }}
              />
            </Field>
            <Field label="Time of Birth" required>
              <input
                name="tob" type="time" value={form.tob}
                onChange={onChange}
                onFocus={() => setFocused('tob')} onBlur={() => setFocused(null)}
                style={{ ...focusStyle('tob'), colorScheme: 'dark' }}
              />
            </Field>
          </div>

          {/* POB */}
          <Field label="Place of Birth" required>
            <input
              name="pob" type="text" value={form.pob}
              onChange={onChange} placeholder="e.g. Nagpur, India"
              onFocus={() => setFocused('pob')} onBlur={() => setFocused(null)}
              style={focusStyle('pob')}
            />
          </Field>

          {/* Gender */}
          <Field label="Gender" required={false}>
            <select
              name="gender" value={form.gender} onChange={onChange}
              onFocus={() => setFocused('gender')} onBlur={() => setFocused(null)}
              style={{ ...focusStyle('gender'), appearance: 'none', cursor: 'pointer' }}
            >
              <option value="">Prefer not to say</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </Field>

          {/* Error */}
          {error && (
            <div style={{
              background: 'rgba(196,106,106,0.12)',
              border: '1px solid rgba(196,106,106,0.35)',
              borderRadius: 'var(--radius)',
              padding: '12px 16px',
              color: '#e08080',
              fontSize: '14px',
              fontFamily: 'var(--font-body)',
            }}>
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '6px',
              padding: '15px 24px',
              background: loading
                ? 'rgba(201,168,76,0.12)'
                : 'linear-gradient(135deg, rgba(201,168,76,0.22), rgba(201,168,76,0.12))',
              border: '1px solid var(--border-glow)',
              borderRadius: 'var(--radius)',
              color: loading ? 'var(--gold-dim)' : 'var(--gold-light)',
              fontFamily: 'var(--font-display)',
              fontSize: '16px',
              fontWeight: 500,
              letterSpacing: '0.1em',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.25s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
            }}
          >
            {loading ? (
              <>
                <Spinner />
                Reading your chart…
              </>
            ) : (
              'Cast My Chart  →'
            )}
          </button>
        </form>

        {/* Footer note */}
        <p style={{
          marginTop: '28px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '12px',
          fontFamily: 'var(--font-body)',
          letterSpacing: '0.03em',
        }}>
          Your birth data is never stored beyond this session.
        </p>
      </div>
    </div>
  )
}

function Spinner() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" style={{ animation: 'spin 1s linear infinite' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="2"
        strokeDasharray="28" strokeDashoffset="10" strokeLinecap="round" />
    </svg>
  )
}
