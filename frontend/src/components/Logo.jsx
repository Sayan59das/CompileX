import React from 'react'

// The mark is a solve balloon: contests hand one to a team for every problem
// they pass, so it doubles as the product's idea of "a correct answer".
export function LogoMark({ size = 28, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <circle cx="16" cy="12.5" r="11" fill="rgb(var(--tomato))" />
      <path d="M13.2 22.4h5.6L16 26.2z" fill="rgb(var(--tomato))" />
      <path
        d="M16 26.2c-1.9 1.5-1.9 2.7 0 3.8"
        stroke="rgb(var(--ink))"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M11.2 7.7l9.6 9.6M20.8 7.7l-9.6 9.6"
        stroke="#fff"
        strokeWidth="2.8"
        strokeLinecap="square"
      />
    </svg>
  )
}

export default function Logo({ size = 28, className = '', wordmark = true }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <LogoMark size={size} />
      {wordmark && (
        <span
          className="stretch-semi font-extrabold text-ink"
          style={{ fontSize: size * 0.72, letterSpacing: '-0.02em', lineHeight: 1 }}
        >
          CompileX
        </span>
      )}
    </span>
  )
}
