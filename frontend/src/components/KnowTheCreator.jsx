export default function KnowTheCreator() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '100px 24px 48px',
      position: 'relative',
      zIndex: 1,
    }}>
      <div style={{
        width: '100%',
        maxWidth: '560px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '52px 48px',
        boxShadow: 'var(--shadow), var(--glow)',
        backdropFilter: 'blur(20px)',
        textAlign: 'center',
      }}>
        {/* Divider top */}
        <div style={{
          height: '1px',
          background: 'linear-gradient(90deg, transparent, var(--border-glow), transparent)',
          marginBottom: '36px',
        }} />

        {/* Unknown creator note */}
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: '14px',
          color: 'var(--text-dim)',
          fontStyle: 'italic',
          marginBottom: '32px',
          lineHeight: 1.6,
        }}>
          Unfortunately the creator is unknown — but here is the person who built this webpage:
        </p>

        {/* Avatar placeholder */}
        <div style={{
          width: '72px',
          height: '72px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(201,168,76,0.25), rgba(201,168,76,0.06))',
          border: '1px solid var(--border-glow)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '28px',
          margin: '0 auto 24px',
        }}>
          ✦
        </div>

        {/* Name */}
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '32px',
          fontWeight: 400,
          color: 'var(--cream)',
          letterSpacing: '0.02em',
          marginBottom: '8px',
        }}>
          Yashraj Vasishtha
        </h1>

        {/* Tagline */}
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: '13px',
          color: 'var(--gold)',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          marginBottom: '28px',
          opacity: 0.85,
        }}>
          Aviation · Energy · AI
        </p>

        {/* Divider */}
        <div style={{
          height: '1px',
          background: 'linear-gradient(90deg, transparent, var(--border-glow), transparent)',
          marginBottom: '28px',
        }} />

        {/* Bio */}
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: '15px',
          color: 'var(--text)',
          lineHeight: 1.75,
          marginBottom: '36px',
        }}>
          Has a knack for modern physics, vedic texts, anthropology, philosophy, and psychology.
          Building practical solutions at the edge — where ancient wisdom meets emerging technology.
        </p>

        {/* Links */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '20px' }}>
          <a
            href="https://www.linkedin.com/in/yashraj-vasishtha/"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              fontFamily: 'var(--font-body)',
              fontSize: '14px',
              color: 'var(--gold)',
              textDecoration: 'none',
              border: '1px solid var(--border-glow)',
              borderRadius: '8px',
              padding: '9px 18px',
              transition: 'all 0.2s',
              background: 'rgba(201,168,76,0.05)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(201,168,76,0.12)'
              e.currentTarget.style.borderColor = 'var(--gold)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(201,168,76,0.05)'
              e.currentTarget.style.borderColor = 'var(--border-glow)'
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6zM2 9h4v12H2z"/>
              <circle cx="4" cy="4" r="2"/>
            </svg>
            LinkedIn
          </a>

          <a
            href="https://www.instagram.com/yashraj__v/"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '7px',
              fontFamily: 'var(--font-body)',
              fontSize: '14px',
              color: 'var(--gold)',
              textDecoration: 'none',
              border: '1px solid var(--border-glow)',
              borderRadius: '8px',
              padding: '9px 18px',
              transition: 'all 0.2s',
              background: 'rgba(201,168,76,0.05)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(201,168,76,0.12)'
              e.currentTarget.style.borderColor = 'var(--gold)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(201,168,76,0.05)'
              e.currentTarget.style.borderColor = 'var(--border-glow)'
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
              <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
              <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
            </svg>
            Instagram
          </a>
        </div>

        {/* Divider bottom */}
        <div style={{
          height: '1px',
          background: 'linear-gradient(90deg, transparent, var(--border-glow), transparent)',
          marginTop: '36px',
        }} />
      </div>
    </div>
  )
}
