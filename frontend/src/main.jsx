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
// began to open). Then the mark flies home: the black fades away, the name shrinks onto the CompileX in the top bar and the two
// brackets onto the brackets of its logo, and the real logo takes over where they land. Where there is no logo in view, or with
// reduced motion, the splash simply fades. If the app never gets that far, it goes after 8 s anyway, so it never hides the page.
const SPLASH_MIN_MS = 2600
const FLY_MS = 1400
let splashGone = false

// The site's own logo and name near the top of the screen (components/Logo.jsx marks them), or null.
function brandOnScreen() {
  for (const logo of document.querySelectorAll('[data-cx-logo]')) {
    const r = logo.getBoundingClientRect()
    if (!r.width || r.top < 0 || r.bottom > 160 || r.left < 0 || r.right > window.innerWidth) continue
    const brand = logo.closest('a') || logo.parentElement
    const word = brand.querySelector('[data-cx-word]')
    return { brand, logo, word: word && word.getBoundingClientRect().width ? word : null }
  }
  return null
}

function flyHome(splash) {
  const target = brandOnScreen()
  const word = splash.querySelector('.cx-word')
  const left = splash.querySelector('.cx-l svg')
  const right = splash.querySelector('.cx-r svg')
  if (!target || !word || !left || !right || !word.animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false

  // where each piece lands: the name on the top bar's name (scaled by font size), and each bracket on the matching bracket of the
  // logo, whose drawing (viewBox 0 0 40 40) holds the left bracket in x 6..19, y 9..31 and the right one in x 21..34
  const L = target.logo.getBoundingClientRect()
  // a flight: from where the piece is to a box (left, top, width), as a shift and a scale about the piece's top-left corner
  const toBox = (el, box) => {
    const r = el.getBoundingClientRect()
    return { el, dx: box.left - r.left, dy: box.top - r.top, s: box.width / r.width, lift: 0 }
  }
  const inLogo = (x, y, w) => ({ left: L.left + (x / 40) * L.width, top: L.top + (y / 40) * L.height, width: (w / 40) * L.width })
  const wordHeight = word.getBoundingClientRect().height
  const flights = [
    toBox(left, inLogo(6, 9, 13)),
    // the right bracket's home is left of the name, so it hops up and over the name instead of sliding through its letters
    { ...toBox(right, inLogo(21, 9, 13)), lift: wordHeight * 1.5 },
  ]
  if (target.word) {
    const T = target.word.getBoundingClientRect()
    flights.push(toBox(word, { left: T.left, top: T.top, width: (T.height / wordHeight) * word.getBoundingClientRect().width }))
  }
  // keyframes along the path (a straight line, or an arc for a piece that lifts), all measured before anything moves
  const frames = ({ dx, dy, s, lift }) => {
    const steps = lift ? 48 : 1                                   // enough points that the arc is a curve, not a polyline
    return Array.from({ length: steps + 1 }, (_, i) => {
      const t = i / steps
      return { offset: t, transform: `translate(${dx * t}px, ${dy * t - lift * Math.sin(Math.PI * t)}px) scale(${1 + (s - 1) * t})` }
    })
  }
  // a soft start, a long gentle settle (the pieces slow into place rather than stopping short)
  const ease = { duration: FLY_MS, easing: 'cubic-bezier(0.45, 0, 0.1, 1)', fill: 'forwards' }
  const paths = flights.map((f) => [f.el, frames(f)])

  target.brand.style.opacity = '0'                                // the real mark waits, hidden, under the flying one
  splash.classList.add('cx-flying')                               // the black fades and the page shows through
  for (const [el, keyframes] of paths) {
    el.style.transformOrigin = '0 0'
    el.animate(keyframes, ease)
  }
  if (!target.word) word.animate([{ opacity: 1 }, { opacity: 0 }], { duration: FLY_MS * 0.6, fill: 'forwards' })

  // landed: the real logo (with its square) fades in while the flown pieces fade out over it, so the hand-off is a cross-fade, then
  // the splash goes
  setTimeout(() => {
    target.brand.style.transition = 'opacity 0.45s ease'
    target.brand.style.opacity = ''
    splash.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 450, easing: 'ease', fill: 'forwards' })
    setTimeout(() => { splash.remove(); target.brand.style.transition = '' }, 500)
  }, FLY_MS)
  return true
}

window.__cxPageReady = () => {
  const splash = document.getElementById('cx-splash')
  if (!splash || splashGone) return
  splashGone = true
  setTimeout(() => {
    // Give the pieces their own layers one frame before they move, and start on a quiet frame: the page has just mounted and is
    // busy (the 3D scene, fonts), and starting in the middle of that is what makes the first moment of a flight stutter.
    splash.classList.add('cx-prep')
    requestAnimationFrame(() => requestAnimationFrame(() => {
      let flew = false
      try { flew = flyHome(splash) } catch { flew = false }
      if (!flew) {
        splash.classList.add('cx-gone')
        setTimeout(() => splash.remove(), 900)
      }
    }))
  }, Math.max(0, SPLASH_MIN_MS - performance.now()))
}
setTimeout(() => window.__cxPageReady(), 8000)

ReactDOM.createRoot(document.getElementById('root')).render(
  // v7_startTransition: a navigation keeps the current page on screen until the next one is ready (see the Suspense note in App.jsx)
  <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <App />
  </BrowserRouter>
)
