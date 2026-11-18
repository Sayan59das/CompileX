import React from 'react'

// The loading screen shown while a page's file is still arriving: the CompileX brackets slide apart and the name opens up between
// them. The styles live in index.html (the same ones the first-paint splash uses), so the splash before the app starts and this one
// look identical. Moving between pages rarely shows it: navigations keep the current page up until the next is ready (App.jsx).
export default function PageLoader() {
  return (
    <div className="cx-loader" role="status" aria-live="polite">
      <div className="cx-open" aria-hidden="true">
        <span className="cx-half cx-l"><svg viewBox="6 9 13 22"><path d="M17 11 8 20l9 9" stroke="#3DE0FF" /></svg></span>
        <span className="cx-word">Compile<span className="cx-x">X</span></span>
        <span className="cx-half cx-r"><svg viewBox="21 9 13 22"><path d="M23 11l9 9-9 9" stroke="#9B7BFF" /></svg></span>
      </div>
      <span className="cx-sr">Loading CompileX</span>
    </div>
  )
}
