import React from 'react'

// The loading screen shown while a page's file is still arriving. The styles live in index.html (the same ones the first-paint splash uses),
// so the splash before the app starts and this one between pages look identical and nothing flickers when one hands over to the other.
export default function PageLoader() {
  return (
    <div className="cx-loader" role="status" aria-live="polite">
      <svg className="cx-loader-mark" width="64" height="64" viewBox="0 0 40 40" aria-hidden="true">
        <rect width="40" height="40" rx="10" fill="#0A0A0A" />
        <rect x="0.5" y="0.5" width="39" height="39" rx="9.5" fill="none" stroke="rgba(255,255,255,0.28)" />
        <path className="cx-b1" pathLength="1" d="M17 11 8 20l9 9" fill="none" stroke="#3DE0FF" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" />
        <path className="cx-b2" pathLength="1" d="M23 11l9 9-9 9" fill="none" stroke="#9B7BFF" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="cx-loader-bar" aria-hidden="true" />
      <span className="cx-sr">Loading CompileX</span>
    </div>
  )
}
