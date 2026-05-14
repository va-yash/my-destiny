/**
 * ProfilePanel.jsx
 *
 * Slide-in panel for "My Profile" — optional, localStorage-based.
 *
 * Storage schema (localStorage key: "mydestiny_profiles"):
 *   Array of {
 *     id, username, email, passwordKey, createdAt,
 *     savedCharts: [{ id, label, savedAt, sessionData }]
 *   }
 *
 * Active session (sessionStorage key: "mydestiny_active"):
 *   { profileId, username }  — cleared when browser tab closes
 *
 * Note: passwords are encoded with btoa() as a lightweight local access
 * control for shared devices. This is NOT real authentication.
 */

import { useState, useEffect, useRef } from 'react'

// ─── Storage helpers ─────────────────────────────────────────────────────────

function getProfiles() {
  try { return JSON.parse(localStorage.getItem('mydestiny_profiles') || '[]') } catch { return [] }
}

function saveProfiles(arr) {
  localStorage.setItem('mydestiny_profiles', JSON.stringify(arr))
}

function encodePassword(pw) {
  // Lightweight obfuscation for local device use — not cryptographic security
  return btoa(encodeURIComponent(pw + 'md_salt_2025'))
}

function getActiveSession() {
  try { return JSON.parse(sessionStorage.getItem('mydestiny_active') || 'null') } catch { return null }
}

function setActiveSession(data) {
  if (data) sessionStorage.setItem('mydestiny_active', JSON.stringify(data))
  else sessionStorage.removeItem('mydestiny_active')
}

// Suggest username: 2 chars of last name + 4 chars of first name, lowercase
function suggestUsername(fullName) {
  if (!fullName || !fullName.trim()) return ''
  const parts = fullName.trim().split(/\s+/)
  const first = parts[0] || ''
  const last  = parts[parts.length - 1] || ''
  if (parts.length === 1) return first.slice(0, 6).toLowerCase()
  return (last.slice(0, 2) + first.slice(0, 4)).toLowerCase()
}

// ─── Panel styles ─────────────────────────────────────────────────────────────

const INPUT = {
  width: '100%',
  background: 'var(--bg-raised)',
  border: '1px solid rgba(180,155,100,0.22)',
  borderRadius: '8px',
  color: 'var(--cream)',
  fontFamily: 'var(--font-body)',
  fontSize: '14px',
  padding: '9px 13px',
  outline: 'none',
  transition: 'border-color 0.2s, box-shadow 0.2s',
}

const LABEL = {
  display: 'block',
  fontFamily: 'var(--font-mono)',
  fontSize: '10px',
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: 'var(--gold)',
  marginBottom: '5px',
  opacity: 0.8,
}

const BTN_PRIMARY = {
  width: '100%',
  padding: '10px',
  background: 'linear-gradient(135deg, rgba(201,168,76,0.28), rgba(201,168,76,0.14))',
  border: '1px solid var(--border-glow)',
  borderRadius: '8px',
  color: 'var(--gold-light)',
  fontFamily: 'var(--font-display)',
  fontSize: '14px',
  letterSpacing: '0.06em',
  cursor: 'pointer',
  transition: 'all 0.2s',
}

const BTN_GHOST = {
  background: 'none',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  color: 'var(--text-dim)',
  fontFamily: 'var(--font-body)',
  fontSize: '12px',
  padding: '6px 12px',
  cursor: 'pointer',
  transition: 'all 0.2s',
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ProfilePanel({
  onClose,
  currentSession,      // current chat session to optionally save
  onChartSaved,        // () => void — called when a chart is saved
  onLoadChart,         // (sessionData) => void — restores a saved chart
  suggestedName,       // pre-fill from birth form
}) {
  const [view,    setView]    = useState('loading')  // 'loading' | 'login' | 'register' | 'dashboard'
  const [profile, setProfile] = useState(null)
  const [focused, setFocused] = useState(null)
  const [error,   setError]   = useState('')
  const [success, setSuccess] = useState('')

  // Register form
  const [regForm, setRegForm] = useState({
    username: suggestedName ? suggestUsername(suggestedName) : '',
    email:    '',
    password: '',
    confirm:  '',
  })

  // Login form
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })

  // On mount: check for active session
  useEffect(() => {
    const active = getActiveSession()
    if (active) {
      const profiles = getProfiles()
      const found    = profiles.find(p => p.id === active.profileId)
      if (found) {
        setProfile(found)
        setView('dashboard')
        return
      }
    }
    setView('login')
  }, [])

  // If a suggestedName arrives after mount (e.g. just cast a chart)
  useEffect(() => {
    if (suggestedName && view === 'register') {
      setRegForm(prev => ({
        ...prev,
        username: prev.username || suggestUsername(suggestedName),
      }))
    }
  }, [suggestedName])

  function inputStyle(name) {
    return focused === name
      ? { ...INPUT, borderColor: 'var(--gold-dim)', boxShadow: '0 0 0 3px rgba(201,168,76,0.1)' }
      : INPUT
  }

  // ── Register ─────────────────────────────────────────────────────────
  function handleRegister() {
    setError('')
    const { username, email, password, confirm } = regForm
    if (!username.trim()) return setError('Username is required.')
    if (username.length < 3) return setError('Username must be at least 3 characters.')
    if (!password)           return setError('Password is required.')
    if (password !== confirm) return setError('Passwords do not match.')

    const profiles = getProfiles()
    if (profiles.find(p => p.username.toLowerCase() === username.toLowerCase())) {
      return setError('That username is already taken.')
    }

    const newProfile = {
      id:          crypto.randomUUID(),
      username:    username.trim().toLowerCase(),
      email:       email.trim(),
      passwordKey: encodePassword(password),
      createdAt:   new Date().toISOString(),
      savedCharts: [],
    }

    saveProfiles([...profiles, newProfile])
    setActiveSession({ profileId: newProfile.id, username: newProfile.username })
    setProfile(newProfile)
    setView('dashboard')
    setSuccess('Profile created!')
  }

  // ── Login ─────────────────────────────────────────────────────────────
  function handleLogin() {
    setError('')
    const { username, password } = loginForm
    if (!username || !password) return setError('Enter username and password.')

    const profiles = getProfiles()
    const found    = profiles.find(p => p.username.toLowerCase() === username.toLowerCase())
    if (!found || found.passwordKey !== encodePassword(password)) {
      return setError('Incorrect username or password.')
    }

    setActiveSession({ profileId: found.id, username: found.username })
    setProfile(found)
    setView('dashboard')
  }

  // ── Logout ────────────────────────────────────────────────────────────
  function handleLogout() {
    setActiveSession(null)
    setProfile(null)
    setView('login')
    setLoginForm({ username: '', password: '' })
  }

  // ── Save current chart ────────────────────────────────────────────────
  function handleSaveChart() {
    if (!currentSession || !profile) return
    setError('')

    const label = [
      currentSession.name && currentSession.name !== 'Friend' ? currentSession.name : null,
      currentSession.dob  ? currentSession.dob : null,
    ].filter(Boolean).join(' · ') || 'My Chart'

    const newChart = {
      id:          crypto.randomUUID(),
      label,
      savedAt:     new Date().toISOString(),
      sessionData: currentSession,
    }

    const profiles    = getProfiles()
    const updatedProf = { ...profile, savedCharts: [...profile.savedCharts, newChart] }
    const updatedList = profiles.map(p => p.id === profile.id ? updatedProf : p)

    saveProfiles(updatedList)
    setProfile(updatedProf)
    setSuccess('Chart saved!')
    onChartSaved?.()
    setTimeout(() => setSuccess(''), 3000)
  }

  // ── Delete saved chart ────────────────────────────────────────────────
  function handleDeleteChart(chartId) {
    const profiles    = getProfiles()
    const updatedProf = {
      ...profile,
      savedCharts: profile.savedCharts.filter(c => c.id !== chartId),
    }
    const updatedList = profiles.map(p => p.id === profile.id ? updatedProf : p)
    saveProfiles(updatedList)
    setProfile(updatedProf)
  }

  // ── Load saved chart ──────────────────────────────────────────────────
  function handleLoadChart(savedChart) {
    onLoadChart?.(savedChart.sessionData)
    onClose()
  }

  // ── Keyboard: Enter to submit ─────────────────────────────────────────
  function onKeyLogin(e)    { if (e.key === 'Enter') handleLogin()    }
  function onKeyRegister(e) { if (e.key === 'Enter') handleRegister() }

  // ─── Render ──────────────────────────────────────────────────────────────

  if (view === 'loading') return null

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 199,
          background: 'rgba(0,0,0,0.4)',
          backdropFilter: 'blur(2px)',
          animation: 'fadeIn 0.2s ease',
        }}
      />

      {/* Panel */}
      <div style={{
        position:   'fixed',
        top:        '62px',
        left:       '16px',
        zIndex:     200,
        width:      '320px',
        maxHeight:  'calc(100vh - 80px)',
        overflowY:  'auto',
        background: 'var(--bg-card)',
        border:     '1px solid var(--border-glow)',
        borderRadius: '14px',
        padding:    '24px',
        boxShadow:  '0 8px 40px rgba(0,0,0,0.6), 0 0 24px rgba(201,168,76,0.08)',
        animation:  'slideDown 0.22s ease',
      }}>

        <style>{`
          @keyframes fadeIn   { from { opacity:0 } to { opacity:1 } }
          @keyframes slideDown { from { opacity:0; transform:translateY(-8px) } to { opacity:1; transform:translateY(0) } }
        `}</style>

        {/* Header */}
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'20px' }}>
          <div>
            <div style={{ fontFamily:'var(--font-display)', fontSize:'18px', color:'var(--gold-light)', letterSpacing:'0.02em' }}>
              My Profile
            </div>
            {profile && (
              <div style={{ fontFamily:'var(--font-mono)', fontSize:'10px', color:'var(--text-dim)', marginTop:'2px', letterSpacing:'0.06em' }}>
                @{profile.username}
              </div>
            )}
          </div>
          <button onClick={onClose} style={{ background:'none', border:'none', color:'var(--text-dim)', fontSize:'18px', cursor:'pointer', lineHeight:1 }}>✕</button>
        </div>

        {/* Feedback messages */}
        {error   && <div style={{ background:'rgba(196,106,106,0.12)', border:'1px solid rgba(196,106,106,0.3)', borderRadius:'8px', padding:'10px 13px', color:'#e08080', fontSize:'13px', marginBottom:'14px' }}>{error}</div>}
        {success && <div style={{ background:'rgba(80,180,120,0.12)', border:'1px solid rgba(80,180,120,0.3)', borderRadius:'8px', padding:'10px 13px', color:'#70d0a0', fontSize:'13px', marginBottom:'14px' }}>{success}</div>}

        {/* ── LOGIN VIEW ─────────────────────────────────────────────── */}
        {view === 'login' && (
          <div style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
            <p style={{ color:'var(--text-dim)', fontSize:'13px', lineHeight:1.5 }}>
              Log in to access your saved charts.
            </p>

            <div>
              <label style={LABEL}>Username</label>
              <input
                type="text"
                value={loginForm.username}
                onChange={e => setLoginForm(p => ({ ...p, username: e.target.value }))}
                onFocus={() => setFocused('lu')} onBlur={() => setFocused(null)}
                onKeyDown={onKeyLogin}
                style={inputStyle('lu')}
                placeholder="your username"
                autoComplete="username"
              />
            </div>

            <div>
              <label style={LABEL}>Password</label>
              <input
                type="password"
                value={loginForm.password}
                onChange={e => setLoginForm(p => ({ ...p, password: e.target.value }))}
                onFocus={() => setFocused('lp')} onBlur={() => setFocused(null)}
                onKeyDown={onKeyLogin}
                style={inputStyle('lp')}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>

            <button onClick={handleLogin} style={BTN_PRIMARY}>Log In</button>

            <div style={{ textAlign:'center', color:'var(--text-dim)', fontSize:'12px' }}>
              No profile yet?{' '}
              <button
                onClick={() => { setView('register'); setError('') }}
                style={{ background:'none', border:'none', color:'var(--gold)', cursor:'pointer', fontSize:'12px', textDecoration:'underline' }}
              >
                Create one — it's free
              </button>
            </div>
          </div>
        )}

        {/* ── REGISTER VIEW ──────────────────────────────────────────── */}
        {view === 'register' && (
          <div style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
            <p style={{ color:'var(--text-dim)', fontSize:'13px', lineHeight:1.5 }}>
              Create a profile to save your chart and access it anytime.
              <br />
              <span style={{ fontSize:'11px', opacity:0.7 }}>
                Everything stays on your device — no server account required.
              </span>
            </p>

            {/* Username with suggestion hint */}
            <div>
              <label style={LABEL}>Username</label>
              <input
                type="text"
                value={regForm.username}
                onChange={e => setRegForm(p => ({ ...p, username: e.target.value.toLowerCase().replace(/\s/g,'') }))}
                onFocus={() => setFocused('ru')} onBlur={() => setFocused(null)}
                onKeyDown={onKeyRegister}
                style={inputStyle('ru')}
                placeholder="choose a username"
                autoComplete="username"
              />
              {suggestedName && regForm.username === '' && (
                <div style={{ fontSize:'11px', color:'var(--text-dim)', marginTop:'4px' }}>
                  Suggested:{' '}
                  <button
                    onClick={() => setRegForm(p => ({ ...p, username: suggestUsername(suggestedName) }))}
                    style={{ background:'none', border:'none', color:'var(--gold)', cursor:'pointer', fontSize:'11px', padding:0 }}
                  >
                    {suggestUsername(suggestedName)}
                  </button>
                </div>
              )}
            </div>

            <div>
              <label style={LABEL}>Email <span style={{ fontWeight:300, opacity:0.6 }}>(optional)</span></label>
              <input
                type="email"
                value={regForm.email}
                onChange={e => setRegForm(p => ({ ...p, email: e.target.value }))}
                onFocus={() => setFocused('re')} onBlur={() => setFocused(null)}
                onKeyDown={onKeyRegister}
                style={inputStyle('re')}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label style={LABEL}>Password</label>
              <input
                type="password"
                value={regForm.password}
                onChange={e => setRegForm(p => ({ ...p, password: e.target.value }))}
                onFocus={() => setFocused('rp')} onBlur={() => setFocused(null)}
                onKeyDown={onKeyRegister}
                style={inputStyle('rp')}
                placeholder="••••••••"
                autoComplete="new-password"
              />
            </div>

            <div>
              <label style={LABEL}>Confirm Password</label>
              <input
                type="password"
                value={regForm.confirm}
                onChange={e => setRegForm(p => ({ ...p, confirm: e.target.value }))}
                onFocus={() => setFocused('rc')} onBlur={() => setFocused(null)}
                onKeyDown={onKeyRegister}
                style={inputStyle('rc')}
                placeholder="••••••••"
                autoComplete="new-password"
              />
            </div>

            <button onClick={handleRegister} style={BTN_PRIMARY}>Create Profile</button>

            <div style={{ textAlign:'center', color:'var(--text-dim)', fontSize:'12px' }}>
              Already have one?{' '}
              <button
                onClick={() => { setView('login'); setError('') }}
                style={{ background:'none', border:'none', color:'var(--gold)', cursor:'pointer', fontSize:'12px', textDecoration:'underline' }}
              >
                Log in
              </button>
            </div>
          </div>
        )}

        {/* ── DASHBOARD VIEW ─────────────────────────────────────────── */}
        {view === 'dashboard' && profile && (
          <div style={{ display:'flex', flexDirection:'column', gap:'16px' }}>

            {/* Save current chart CTA (only when a chart is active) */}
            {currentSession && (
              <div style={{
                background: 'linear-gradient(135deg, rgba(201,168,76,0.1), rgba(201,168,76,0.04))',
                border: '1px solid rgba(201,168,76,0.25)',
                borderRadius: '10px',
                padding: '14px',
              }}>
                <div style={{ fontSize:'13px', color:'var(--text)', marginBottom:'10px', lineHeight:1.4 }}>
                  <strong style={{ color:'var(--gold-light)' }}>Save current chart</strong>
                  <br />
                  <span style={{ fontSize:'12px', color:'var(--text-dim)' }}>
                    {currentSession.name && currentSession.name !== 'Friend'
                      ? currentSession.name : 'This chart'}{' '}
                    — {currentSession.dob || 'your reading'}
                  </span>
                </div>
                <button onClick={handleSaveChart} style={{ ...BTN_PRIMARY, fontSize:'13px', padding:'8px' }}>
                  ✦ Save to My Profile
                </button>
              </div>
            )}

            {/* Saved charts */}
            <div>
              <div style={{ fontFamily:'var(--font-mono)', fontSize:'10px', letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--text-dim)', marginBottom:'10px' }}>
                Saved Charts ({profile.savedCharts.length})
              </div>

              {profile.savedCharts.length === 0 ? (
                <div style={{ color:'var(--text-dim)', fontSize:'13px', textAlign:'center', padding:'16px 0', opacity:0.6 }}>
                  No charts saved yet.
                </div>
              ) : (
                <div style={{ display:'flex', flexDirection:'column', gap:'8px' }}>
                  {[...profile.savedCharts].reverse().map(chart => (
                    <div
                      key={chart.id}
                      style={{
                        background: 'rgba(18,21,42,0.5)',
                        border: '1px solid var(--border)',
                        borderRadius: '10px',
                        padding: '12px 14px',
                      }}
                    >
                      <div style={{ fontSize:'13px', color:'var(--cream)', marginBottom:'4px', fontWeight:500 }}>
                        {chart.label}
                      </div>
                      <div style={{ fontSize:'11px', color:'var(--text-dim)', marginBottom:'10px' }}>
                        {chart.sessionData?.ascendant && `↑ ${chart.sessionData.ascendant}`}
                        {chart.sessionData?.sun_sign  && ` · ☉ ${chart.sessionData.sun_sign}`}
                        {chart.sessionData?.moon_sign && ` · ☽ ${chart.sessionData.moon_sign}`}
                      </div>
                      <div style={{ display:'flex', gap:'8px' }}>
                        <button
                          onClick={() => handleLoadChart(chart)}
                          style={{ ...BTN_GHOST, fontSize:'11px', padding:'5px 10px', color:'var(--gold)', borderColor:'rgba(201,168,76,0.3)' }}
                          onMouseEnter={e => { e.currentTarget.style.borderColor='var(--border-glow)'; e.currentTarget.style.color='var(--gold-light)' }}
                          onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(201,168,76,0.3)'; e.currentTarget.style.color='var(--gold)' }}
                        >
                          Load Chart
                        </button>
                        <button
                          onClick={() => handleDeleteChart(chart.id)}
                          style={{ ...BTN_GHOST, fontSize:'11px', padding:'5px 10px', color:'var(--accent-rose)', borderColor:'rgba(196,106,106,0.25)' }}
                          onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(196,106,106,0.5)' }}
                          onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(196,106,106,0.25)' }}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer: logout */}
            <div style={{ borderTop:'1px solid var(--border)', paddingTop:'14px' }}>
              <button
                onClick={handleLogout}
                style={{ ...BTN_GHOST, width:'100%', textAlign:'center', fontSize:'12px' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor='var(--gold-dim)'; e.currentTarget.style.color='var(--gold)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor='var(--border)'; e.currentTarget.style.color='var(--text-dim)' }}
              >
                Log out
              </button>
            </div>

          </div>
        )}

      </div>
    </>
  )
}

// Export helper so App.jsx can read the active session without importing the panel
export { getActiveSession }
