import { useEffect, useLayoutEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

// Moving between pages cross-fades the old page into the new one, using the browser's View Transitions where it has them
// (Chrome, Edge, Safari 18+). A click on a link to another page of the site is taken over here: the browser keeps a picture of
// the current page, the router moves to the new one, and once React has put the new page in the DOM the picture fades out over
// it (the styles are the ::view-transition rules in index.css). Elsewhere, or with reduced motion, links work as they always did
// and the new page only fades in (.route-fade).
//
// The link's own onClick handlers still run: this only calls preventDefault, which also stops React Router's Link from
// navigating a second time. Same-page links (#anchors), new-tab clicks, downloads and other sites are left alone.
export default function PageTransitions() {
  const navigate = useNavigate()
  const { pathname, search } = useLocation()
  const pending = useRef(null)

  // the new page is in the DOM: let the cross-fade play
  useLayoutEffect(() => {
    pending.current?.()
    pending.current = null
  }, [pathname, search])

  useEffect(() => {
    if (typeof document.startViewTransition !== 'function') return undefined
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined
    const onClick = (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
      const a = e.target instanceof Element ? e.target.closest('a[href]') : null
      if (!a || (a.target && a.target !== '_self') || a.hasAttribute('download')) return
      const url = new URL(a.href, window.location.href)
      if (url.origin !== window.location.origin || url.pathname === window.location.pathname) return
      e.preventDefault()
      const to = url.pathname + url.search + url.hash
      const vt = document.startViewTransition(() => new Promise((resolve) => {
        pending.current = resolve
        navigate(to)
        // never hold the page still for long if the next one is slow to arrive
        setTimeout(resolve, 1200)
      }))
      // a skipped or timed-out transition is not an error worth reporting
      vt.ready.catch(() => {})
      vt.finished.catch(() => {})
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [navigate])

  return null
}
