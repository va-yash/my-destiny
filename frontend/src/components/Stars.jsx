import { useMemo } from 'react'

export default function Stars() {
  const stars = useMemo(() => {
    return Array.from({ length: 120 }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 1.6 + 0.3,
      delay: Math.random() * 6,
      dur: Math.random() * 3 + 4,
    }))
  }, [])

  return (
    <svg
      aria-hidden="true"
      className="stars-bg"
      style={{
        position: 'fixed', inset: 0, width: '100%', height: '100%',
        pointerEvents: 'none', zIndex: 0, opacity: 0.6,
        transition: 'opacity 0.4s',
      }}
    >
      {stars.map(s => (
        <circle
          key={s.id}
          cx={`${s.x}%`}
          cy={`${s.y}%`}
          r={s.size}
          fill="#c9a84c"
          opacity={0}
        >
          <animate
            attributeName="opacity"
            values="0;0.7;0"
            dur={`${s.dur}s`}
            begin={`${s.delay}s`}
            repeatCount="indefinite"
          />
        </circle>
      ))}
    </svg>
  )
}
