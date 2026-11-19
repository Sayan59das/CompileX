import React from 'react'

// The mark: a code tag, </>, with a bracket for you (cyan), a bracket for the rival (violet) and a slash between them. On midnight.
// data-cx-logo and data-cx-word let the start-up splash (main.jsx) find the mark on screen and fly its own brackets and name onto it.
export default function Logo({ size = 40, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" className={className} role="img" aria-label="CompileX" data-cx-logo="">
      <rect width="40" height="40" rx="10" fill="#0A0A0A" />
      <rect x="0.5" y="0.5" width="39" height="39" rx="9.5" fill="none" stroke="rgba(255,255,255,0.28)" />
      <path d="M14 12 6.5 20 14 28" fill="none" stroke="#3DE0FF" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M26 12l7.5 8L26 28" fill="none" stroke="#9B7BFF" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M22 10 18 30" fill="none" stroke="#F2F4F8" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

// The wordmark: Compile in Sora, closed by an arc-coloured X.
export function Wordmark({ className = '' }) {
  return (
    <span className={`font-display inline-flex items-baseline font-bold leading-none tracking-[-0.04em] text-white ${className}`} aria-label="CompileX" data-cx-word="">
      <span aria-hidden="true">Compile</span>
      <span aria-hidden="true" className="text-arc">X</span>
    </span>
  )
}
