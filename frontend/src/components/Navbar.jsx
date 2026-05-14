/**
 * Navbar.jsx
 *
 * Changes from v1:
 * - Added "My Profile" button on the left side
 * - Accepts profileUsername, onOpenProfile, profilePulsing props
 * - Pulsing glow animation on the profile button when profilePulsing=true
 *   (i.e. user has just cast a chart but hasn't saved it yet)
 */

export default function Navbar({
  page,
  onNavigate,
  darkMode,
  onToggleDark,
  // Profile props
  profileUsername,   // string | null — shown when logged in
  onOpenProfile,     // () => void
  profilePulsing,    // bool — animate the button to draw attention
}) {

  const linkStyle = (active) => ({
    fontFamily: 'var(--font-body)',
    fontSize: '13px',
    fontWeight: active ? 600 : 400,
    color: active ? 'var(--gold)' : 'var(--text-dim)',
    textDecoration: 'underline',
    textUnderlineOffset: '3px',
    textDecorationColor: active ? 'var(--gold-dim)' : 'rgba(120,100,70,0.4)',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    padding: 0,
    transition: 'color 0.2s',
    letterSpacing: '0.01em',
  })

  return (
    <nav style={{
      position: 'fixed',
      top: 0, left: 0, right: 0,
      zIndex: 100,
      height: '52px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 28px',
      background: 'var(--nav-bg)',
      borderBottom: '1px solid var(--border)',
      backdropFilter: 'blur(16px)',
    }}>

      {/* ── Pulsing keyframes ────────────────────────────────────────── */}
      <style>{`
        @keyframes profilePulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(201,168,76,0.0); border-color: rgba(201,168,76,0.35); }
          50%       { box-shadow: 0 0 0 5px rgba(201,168,76,0.18); border-color: rgba(201,168,76,0.7); }
        }
        @keyframes profileDot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.4; transform: scale(0.75); }
        }
      `}</style>

      {/* ── Left: brand + nav links ──────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>

        {/* Brand */}
        <button
          onClick={() => onNavigate('home')}
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: '17px',
            fontWeight: 500,
            color: 'var(--gold)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            letterSpacing: '0.02em',
            padding: 0,
          }}
        >
          My Destiny ☽
        </button>

        <span style={{ color: 'var(--border)', fontSize: '14px', opacity: 0.6 }}>|</span>

        {/* My Profile button */}
        <button
          onClick={onOpenProfile}
          title={profileUsername ? `Profile: @${profileUsername}` : 'My Profile — save your chart'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontFamily: 'var(--font-body)',
            fontSize: '13px',
            color: profileUsername ? 'var(--gold-light)' : 'var(--text-dim)',
            background: profileUsername
              ? 'rgba(201,168,76,0.08)'
              : 'none',
            border: profileUsername
              ? '1px solid rgba(201,168,76,0.3)'
              : '1px solid transparent',
            borderRadius: '20px',
            padding: profileUsername ? '3px 10px 3px 7px' : '3px 4px',
            cursor: 'pointer',
            transition: 'all 0.2s',
            letterSpacing: '0.01em',
            animation: profilePulsing ? 'profilePulse 1.8s ease-in-out infinite' : 'none',
            position: 'relative',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = 'var(--gold)'
            if (!profilePulsing) e.currentTarget.style.borderColor = 'rgba(201,168,76,0.35)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = profileUsername ? 'var(--gold-light)' : 'var(--text-dim)'
            if (!profilePulsing && !profileUsername) e.currentTarget.style.borderColor = 'transparent'
          }}
        >
          {/* Pulsing dot indicator when there's something to save */}
          {profilePulsing && !profileUsername && (
            <span style={{
              width: '6px', height: '6px',
              borderRadius: '50%',
              background: 'var(--gold)',
              flexShrink: 0,
              animation: 'profileDot 1.8s ease-in-out infinite',
            }} />
          )}

          {/* Avatar/icon */}
          <span style={{ fontSize: '14px', lineHeight: 1 }}>
            {profileUsername ? '☽' : '○'}
          </span>

          {/* Label */}
          <span>
            {profileUsername ? `@${profileUsername}` : 'My Profile'}
          </span>
        </button>

        <span style={{ color: 'var(--border)', fontSize: '14px', opacity: 0.6 }}>|</span>

        {/* Know the Creator */}
        <button
          style={linkStyle(page === 'creator')}
          onClick={() => onNavigate('creator')}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--gold)'}
          onMouseLeave={e => e.currentTarget.style.color = page === 'creator' ? 'var(--gold)' : 'var(--text-dim)'}
        >
          Know the Creator
        </button>

        {/* Feedback */}
        <a
          href="mailto:feedback@astrogyaani.app"
          style={{ ...linkStyle(false), textDecoration: 'underline', textUnderlineOffset: '3px' }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--gold)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}
        >
          Feedback
        </a>
      </div>

      {/* ── Right: dark/light toggle ─────────────────────────────────── */}
      <button
        onClick={onToggleDark}
        title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'none',
          border: '1px solid var(--border)',
          borderRadius: '20px',
          padding: '5px 12px',
          cursor: 'pointer',
          color: 'var(--text-dim)',
          fontFamily: 'var(--font-body)',
          fontSize: '12px',
          letterSpacing: '0.04em',
          transition: 'all 0.2s',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = 'var(--gold-dim)'
          e.currentTarget.style.color = 'var(--gold)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = 'var(--border)'
          e.currentTarget.style.color = 'var(--text-dim)'
        }}
      >
        <span style={{ fontSize: '14px' }}>{darkMode ? '☀️' : '🌙'}</span>
        {darkMode ? 'Light' : 'Dark'}
      </button>

    </nav>
  )
}
