import { useEffect, useRef } from 'react'
import Lenis from 'lenis'

// Eased wheel scrolling for the pages that scroll as a document, and a fresh start at the top of every page.
// The landing page runs its own Lenis (it drives the 3D scene), and the full-screen editors scroll inside their own panes,
// so the app turns this off for those routes with `enabled={false}`.
export default function SmoothScroll({ enabled, pathname }) {
  const lenis = useRef(null)

  useEffect(() => {
    if (!enabled) return undefined
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    const l = new Lenis({ lerp: 0.11, wheelMultiplier: 0.9, smoothWheel: true, anchors: true, allowNestedScroll: true })
    lenis.current = l
    let raf = requestAnimationFrame(function loop(t) { l.raf(t); raf = requestAnimationFrame(loop) })
    return () => { cancelAnimationFrame(raf); l.destroy(); lenis.current = null }
  }, [enabled])

  useEffect(() => {
    if (lenis.current) lenis.current.scrollTo(0, { immediate: true, force: true })
    else window.scrollTo(0, 0)
  }, [pathname])

  return null
}
