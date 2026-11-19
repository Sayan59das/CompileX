import React from 'react'

// The loading screen shown while a page's file is still arriving: the CompileX code tag (</>) opens, the brackets slide apart and the
// name appears between them. The styles live in index.html (the same ones the first-paint splash uses), so the splash before the app starts and this one
// look identical. Moving between pages rarely shows it: navigations keep the current page up until the next is ready (App.jsx).
export default function PageLoader() {
  return (
    <div className="cx-loader" role="status" aria-live="polite">
      <div className="cx-open" aria-hidden="true">
        <span className="cx-half cx-l"><svg viewBox="4 10 12 20"><path d="M14 12 6.5 20 14 28" stroke="#3DE0FF" /></svg></span>
        <span className="cx-slash"><svg viewBox="16 8 8 24"><path d="M22 10 18 30" stroke="#F2F4F8" /></svg></span>
        <span className="cx-word">Compile<span className="cx-x">X</span></span>
        <span className="cx-half cx-r"><svg viewBox="24 10 12 20"><path d="M26 12l7.5 8L26 28" stroke="#9B7BFF" /></svg></span>
      </div>
      <span className="cx-sr">Loading CompileX</span>
    </div>
  )
}
