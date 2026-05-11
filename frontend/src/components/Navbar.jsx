export default function Navbar({ page, onNavigate, darkMode, onToggleDark }) {
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
      top: 0,
      left: 0,
      right: 0,
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
      {/* Left — brand + nav links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
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
          Astro-gyaani ☽
        </button>

        <span style={{ color: 'var(--border)', fontSize: '14px', opacity: 0.6 }}>|</span>

        <button
          style={linkStyle(page === 'creator')}
          onClick={() => onNavigate('creator')}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--gold)'}
          onMouseLeave={e => e.currentTarget.style.color = page === 'creator' ? 'var(--gold)' : 'var(--text-dim)'}
        >
          Know the Creator
        </button>

        <a
          href="mailto:feedback@astrogyaani.app"
          style={{
            ...linkStyle(false),
            textDecoration: 'underline',
            textUnderlineOffset: '3px',
          }}
          onMouseEnter={e => e.currentTarget.style.color = 'var(--gold)'}
          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}
        >
          Feedback
        </a>
      </div>

      {/* Right — dark/light toggle */}
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
