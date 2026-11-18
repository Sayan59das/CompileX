import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import '@fontsource-variable/onest/wght.css'
import '@fontsource-variable/sora/wght.css'
import '@fontsource-variable/jetbrains-mono/index.css'
import './index.css'

// The loading screen in index.html (#cx-splash) covers the app while it starts. App.jsx calls this once the first page is on screen;
// the splash then stays until its animation has played and the finished mark has held for about a second (2.6 s after the page
// began to open), and fades out. If the app never gets that far, it goes after 8 s anyway, so it can never hide the page for good.
const SPLASH_MIN_MS = 2600
let splashGone = false
window.__cxPageReady = () => {
  const splash = document.getElementById('cx-splash')
  if (!splash || splashGone) return
  splashGone = true
  setTimeout(() => {
    splash.classList.add('cx-gone')
    setTimeout(() => splash.remove(), 900)
  }, Math.max(0, SPLASH_MIN_MS - performance.now()))
}
setTimeout(() => window.__cxPageReady(), 8000)

ReactDOM.createRoot(document.getElementById('root')).render(
  // v7_startTransition: a navigation keeps the current page on screen until the next one is ready (see the Suspense note in App.jsx)
  <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <App />
  </BrowserRouter>
)
