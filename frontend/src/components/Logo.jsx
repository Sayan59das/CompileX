import React from 'react'

export default function Logo({ size = 40, className = '' }) {
  const id = `cx${size}`
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id={`${id}-a`} x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#3b82f6" />
        </linearGradient>
        <linearGradient id={`${id}-b`} x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#a5b4fc" />
          <stop offset="100%" stopColor="#e879f9" />
        </linearGradient>
      </defs>

      {/* Background */}
      <rect width="40" height="40" rx="10" fill={`url(#${id}-a)`} />

      {/* Bold "cx" text-style mark using paths */}
      {/* C — open arc left side */}
      <path
        d="M19 13 C14.5 13 11 16.1 11 20 C11 23.9 14.5 27 19 27"
        stroke="white"
        strokeWidth="3.2"
        strokeLinecap="round"
        fill="none"
      />

      {/* X — two diagonal strokes */}
      <line x1="22" y1="14" x2="29" y2="26" stroke={`url(#${id}-b)`} strokeWidth="3.2" strokeLinecap="round" />
      <line x1="29" y1="14" x2="22" y2="26" stroke={`url(#${id}-b)`} strokeWidth="3.2" strokeLinecap="round" />
    </svg>
  )
}
