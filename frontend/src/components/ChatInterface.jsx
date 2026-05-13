import { useState, useRef, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_URL || ''

// ─── Simple markdown → styled text renderer ──────────────────────────────────

function renderMarkdown(text) {
  const lines = text.split('\n')
  const elements = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    if (/^[━─—\-]{3,}$/.test(line.trim())) {
      elements.push(
        <hr key={i} style={{
          border: 'none',
          borderTop: '1px solid rgba(180,155,100,0.2)',
          margin: '14px 0',
        }} />
      )
      i++; continue
    }

    const h3Match = line.match(/^###\s+(.+)/)
    const h2Match = line.match(/^##\s+(.+)/)
    const h1Match = line.match(/^#\s+(.+)/)
    if (h1Match || h2Match || h3Match) {
      const content = (h1Match || h2Match || h3Match)[1]
      const size = h1Match ? '20px' : h2Match ? '18px' : '16px'
      elements.push(
        <div key={i} style={{
          fontFamily: 'var(--font-display)',
          fontSize: size,
          fontWeight: 500,
          color: 'var(--gold-light)',
          margin: '18px 0 8px',
          letterSpacing: '0.02em',
        }}>
          {inlineFormat(content)}
        </div>
      )
      i++; continue
    }

    if (!line.trim()) {
      elements.push(<div key={i} style={{ height: '10px' }} />)
      i++; continue
    }

    if (line.match(/^[\-\*•]\s+/)) {
      const content = line.replace(/^[\-\*•]\s+/, '')
      elements.push(
        <div key={i} style={{
          display: 'flex', gap: '10px', margin: '4px 0',
          paddingLeft: '4px',
        }}>
          <span style={{ color: 'var(--gold)', flexShrink: 0, marginTop: '2px' }}>✦</span>
          <span>{inlineFormat(content)}</span>
        </div>
      )
      i++; continue
    }

    elements.push(
      <span key={i}>
        {inlineFormat(line)}
        {'\n'}
      </span>
    )
    i++
  }

  return elements
}

function inlineFormat(text) {
  const parts = []
  const re = /(\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`)/g
  let last = 0, m

  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    if (m[2]) parts.push(<strong key={m.index} style={{ color: 'var(--cream)', fontWeight: 600 }}>{m[2]}</strong>)
    else if (m[3]) parts.push(<em key={m.index} style={{ color: 'var(--gold-light)', fontStyle: 'italic' }}>{m[3]}</em>)
    else if (m[4]) parts.push(
      <code key={m.index} style={{
        fontFamily: 'var(--font-mono)', fontSize: '13px',
        background: 'rgba(201,168,76,0.1)', color: 'var(--gold-light)',
        padding: '1px 6px', borderRadius: '4px',
      }}>{m[4]}</code>
    )
    last = m.index + m[0].length
  }

  if (last < text.length) parts.push(text.slice(last))
  return parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : parts
}

// ─── Typing cursor ────────────────────────────────────────────────────────────
function Cursor() {
  return (
    <span style={{
      display: 'inline-block',
      width: '2px', height: '16px',
      background: 'var(--gold)',
      marginLeft: '2px',
      verticalAlign: 'middle',
      animation: 'blink 1s step-end infinite',
    }}>
      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
    </span>
  )
}

// ─── Single message bubble ────────────────────────────────────────────────────
function MessageBubble({ msg, isStreaming }) {
  const isUser = msg.role === 'user'
  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      padding: '4px 0',
      animation: 'fadeUp 0.3s ease',
    }}>
      <style>{`@keyframes fadeUp { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:translateY(0) } }`}</style>

      {!isUser && (
        <div style={{
          width: '32px', height: '32px', flexShrink: 0,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(201,168,76,0.25), rgba(201,168,76,0.08))',
          border: '1px solid var(--border-glow)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '14px', marginRight: '12px', marginTop: '4px',
        }}>
          ☽
        </div>
      )}

      <div style={{
        maxWidth: isUser ? '55%' : '80%',
        background: isUser ? 'var(--msg-user-bg)' : 'var(--msg-ai-bg)',
        border: `1px solid ${isUser ? 'rgba(201,168,76,0.3)' : 'rgba(180,155,100,0.12)'}`,
        borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
        padding: '14px 18px',
        backdropFilter: 'blur(12px)',
      }}>
        {isUser ? (
          <p style={{
            color: 'var(--gold-light)',
            fontFamily: 'var(--font-body)',
            fontSize: '15px',
            lineHeight: 1.6,
          }}>
            {msg.content}
          </p>
        ) : (
          <div style={{
            color: 'var(--text)',
            fontFamily: 'var(--font-body)',
            fontSize: '16px',
            lineHeight: 1.7,
          }}>
            {renderMarkdown(msg.content)}
            {isStreaming && <Cursor />}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Planetary reference toggle ───────────────────────────────────────────────
function ReferenceToggle({ value, onChange }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '7px',
      background: 'rgba(18,21,42,0.6)',
      border: '1px solid rgba(180,155,100,0.18)',
      borderRadius: '20px',
      padding: '4px 5px 4px 10px',
      backdropFilter: 'blur(8px)',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        letterSpacing: '0.06em',
        color: 'var(--text-dim)',
        whiteSpace: 'nowrap',
      }}>
        Refs
      </span>

      {/* Toggle pill */}
      <button
        onClick={() => onChange(!value)}
        title={value ? 'Showing planetary references — click to hide' : 'Hiding planetary references — click to show'}
        style={{
          position: 'relative',
          width: '40px',
          height: '22px',
          borderRadius: '11px',
          border: 'none',
          cursor: 'pointer',
          background: value
            ? 'linear-gradient(135deg, rgba(201,168,76,0.45), rgba(201,168,76,0.25))'
            : 'rgba(255,255,255,0.06)',
          transition: 'background 0.25s',
          flexShrink: 0,
          boxShadow: value ? '0 0 8px rgba(201,168,76,0.25)' : 'none',
        }}
      >
        <span style={{
          position: 'absolute',
          top: '3px',
          left: value ? '21px' : '3px',
          width: '16px',
          height: '16px',
          borderRadius: '50%',
          background: value ? 'var(--gold)' : 'rgba(255,255,255,0.3)',
          transition: 'left 0.25s, background 0.25s',
          boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
        }} />
      </button>

      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        letterSpacing: '0.06em',
        color: value ? 'var(--gold)' : 'var(--text-muted)',
        minWidth: '24px',
        transition: 'color 0.2s',
      }}>
        {value ? 'ON' : 'OFF'}
      </span>
    </div>
  )
}

// ─── Suggested questions ──────────────────────────────────────────────────────
const SUGGESTIONS = [
  "What are my core strengths and shadow traits?",
  "What does my career path look like?",
  "Tell me about my relationship patterns.",
  "What is my current dasha period activating?",
  "What are my biggest life lessons?",
  "What spiritual path is right for me?",
]

// ─── Main Chat Interface ──────────────────────────────────────────────────────
export default function ChatInterface({ session, onReset }) {
  const [messages, setMessages]           = useState([])
  const [input, setInput]                 = useState('')
  const [streaming, setStreaming]         = useState(false)
  const [error, setError]                 = useState('')
  const [includeRefs, setIncludeRefs]     = useState(true)

  const scrollRef    = useRef(null)
  const inputRef     = useRef(null)
  const abortRef     = useRef(null)
  // Track whether user has manually scrolled up during streaming
  const userScrolled = useRef(false)

  // ── Scroll helpers ─────────────────────────────────────────────────────────
  const isNearBottom = () => {
    if (!scrollRef.current) return true
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    return scrollHeight - scrollTop - clientHeight < 120
  }

  const scrollToBottom = (force = false) => {
    if (!scrollRef.current) return
    if (force || !userScrolled.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }

  // Detect when user manually scrolls up (only matters during streaming)
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const handleScroll = () => {
      if (streaming && !isNearBottom()) {
        userScrolled.current = true
      } else if (isNearBottom()) {
        userScrolled.current = false
      }
    }
    el.addEventListener('scroll', handleScroll, { passive: true })
    return () => el.removeEventListener('scroll', handleScroll)
  }, [streaming])

  // Auto-scroll during streaming only if user hasn't scrolled away
  useEffect(() => {
    if (streaming) {
      scrollToBottom(false)   // respects userScrolled
    }
  }, [messages])

  // Opening message
  useEffect(() => {
    const openingText =
      `Namaste. I have your complete birth chart before me.\n\n` +
      `Your Ascendant is **${session.ascendant}** — ` +
      `your soul walks in through the nakshatra of **${session.asc_nakshatra}**. ` +
      `Your Moon rests in **${session.moon_sign}** in **${session.moon_nakshatra}**, ` +
      `and your Sun shines through **${session.sun_sign}**.\n\n` +
      `I have read your full D1, D9, and D10 charts, your current dasha timeline, and all active yogas. ` +
      `What would you like to explore?`

    setMessages([{ role: 'assistant', content: openingText }])
  }, [session])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || streaming) return
    setError('')

    const userMsg = { role: 'user', content: text.trim() }
    const history = messages.slice(-8).map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [...prev, userMsg])
    setInput('')
    setStreaming(true)
    // User just sent — always snap to bottom and reset scroll flag
    userScrolled.current = false
    setTimeout(() => scrollToBottom(true), 50)

    // Placeholder assistant message
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await fetch(`${API}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          session_id:         session.session_id,
          system_prompt:      session.system_prompt || '',
          question:           text.trim(),
          history,
          language:           session.language || 'English',
          include_references: includeRefs,
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Request failed')
      }

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const event = JSON.parse(raw)
            if (event.error) throw new Error(event.error)
            if (event.text) {
              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + event.text,
                }
                return updated
              })
            }
          } catch (parseErr) {
            if (parseErr.message !== 'Unexpected end of JSON input') {
              throw parseErr
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Something went wrong. Please try again.')
        setMessages(prev => prev.filter((_, i) => i !== prev.length - 1))
      }
    } finally {
      setStreaming(false)
      userScrolled.current = false
    }
  }, [messages, streaming, session, includeRefs])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const showSuggestions = messages.length <= 1

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      maxWidth: '1100px',
      width: '100%',
      margin: '0 auto',
      position: 'relative',
      zIndex: 1,
      paddingTop: '52px',
    }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--chat-bg)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
        gap: '10px',
        flexWrap: 'nowrap',
      }}>
        {/* Left: chart identity */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: '16px',
            fontWeight: 400,
            color: 'var(--cream)',
            letterSpacing: '0.02em',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}>
            {session.name && session.name !== 'Friend' ? session.name : 'Your Chart'}
          </div>
          <div style={{ display: 'flex', gap: '10px', marginTop: '2px', flexWrap: 'wrap' }}>
            {[
              `☉ ${session.sun_sign}`,
              `☽ ${session.moon_sign}`,
              `↑ ${session.ascendant}`,
            ].map(tag => (
              <span key={tag} style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                color: 'var(--text-dim)',
                letterSpacing: '0.05em',
              }}>
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Centre: planetary reference toggle */}
        <ReferenceToggle value={includeRefs} onChange={setIncludeRefs} />

        {/* Right: new chart */}
        <button
          onClick={onReset}
          style={{
            background: 'none',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            color: 'var(--text-dim)',
            fontFamily: 'var(--font-body)',
            fontSize: '12px',
            padding: '6px 10px',
            cursor: 'pointer',
            transition: 'all 0.2s',
            letterSpacing: '0.04em',
            flexShrink: 0,
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
          New Chart
        </button>
      </header>

      {/* ── Messages ───────────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            msg={msg}
            isStreaming={streaming && i === messages.length - 1 && msg.role === 'assistant'}
          />
        ))}

        {showSuggestions && !streaming && (
          <div style={{ marginTop: '20px' }}>
            <div style={{
              fontFamily: 'var(--font-display)',
              fontSize: '11px',
              letterSpacing: '0.18em',
              textTransform: 'uppercase',
              color: 'var(--text-dim)',
              marginBottom: '14px',
              paddingLeft: '4px',
            }}>
              Explore your chart
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  style={{
                    background: 'rgba(18,21,42,0.7)',
                    border: '1px solid rgba(180,155,100,0.2)',
                    borderRadius: '24px',
                    color: 'var(--text)',
                    fontFamily: 'var(--font-body)',
                    fontSize: '13.5px',
                    padding: '9px 16px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    textAlign: 'left',
                    backdropFilter: 'blur(8px)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'rgba(201,168,76,0.4)'
                    e.currentTarget.style.color = 'var(--gold-light)'
                    e.currentTarget.style.background = 'rgba(201,168,76,0.08)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'rgba(180,155,100,0.2)'
                    e.currentTarget.style.color = 'var(--text)'
                    e.currentTarget.style.background = 'rgba(18,21,42,0.7)'
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div style={{
            background: 'rgba(196,106,106,0.1)',
            border: '1px solid rgba(196,106,106,0.3)',
            borderRadius: '10px',
            padding: '12px 16px',
            color: '#d88080',
            fontSize: '14px',
            marginTop: '8px',
          }}>
            {error}
          </div>
        )}
      </div>

      {/* ── Input bar ──────────────────────────────────────────────────── */}
      <div style={{
        padding: '12px 16px 18px',
        borderTop: '1px solid var(--border)',
        background: 'var(--chat-bg)',
        backdropFilter: 'blur(16px)',
        flexShrink: 0,
      }}>
        <div style={{
          display: 'flex',
          gap: '12px',
          alignItems: 'flex-end',
          background: 'var(--input-bg)',
          border: '1px solid rgba(180,155,100,0.22)',
          borderRadius: '14px',
          padding: '4px 4px 4px 18px',
          transition: 'border-color 0.2s',
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your chart…"
            rows={1}
            disabled={streaming}
            style={{
              flex: 1,
              background: 'none',
              border: 'none',
              outline: 'none',
              resize: 'none',
              color: 'var(--cream)',
              fontFamily: 'var(--font-body)',
              fontSize: '15.5px',
              lineHeight: 1.6,
              padding: '10px 0',
              maxHeight: '120px',
              overflowY: 'auto',
              opacity: streaming ? 0.5 : 1,
            }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || streaming}
            style={{
              width: '42px', height: '42px', flexShrink: 0,
              borderRadius: '10px',
              background: (!input.trim() || streaming)
                ? 'rgba(201,168,76,0.08)'
                : 'linear-gradient(135deg, rgba(201,168,76,0.35), rgba(201,168,76,0.18))',
              border: '1px solid',
              borderColor: (!input.trim() || streaming)
                ? 'rgba(201,168,76,0.12)'
                : 'var(--border-glow)',
              color: (!input.trim() || streaming) ? 'var(--text-muted)' : 'var(--gold-light)',
              cursor: (!input.trim() || streaming) ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.2s',
              fontSize: '18px',
            }}
          >
            {streaming ? '…' : '↑'}
          </button>
        </div>
        <p style={{
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '11px',
          fontFamily: 'var(--font-body)',
          letterSpacing: '0.05em',
          marginTop: '10px',
        }}>
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
