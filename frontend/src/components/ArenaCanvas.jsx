import React, { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { createArena } from '../three/arena'

// The 3D scene as a fixed full-screen canvas. The page drives it through the ref:
//   ref.current.setChapter(c)  which shape, as a continuous coordinate
//   ref.current.setLayout({ offsets, opacities })
//   ref.current.pulse(dy)      scroll distance, so the cloud turns with the page
//   ref.current.fitUnder(px, scale)  where to put the laptop so it sits just below a point on the page (see arena.js)
const ArenaCanvas = forwardRef(function ArenaCanvas({ className = '' }, ref) {
  const canvasRef = useRef(null)
  const arena = useRef(null)

  useEffect(() => {
    try {
      arena.current = createArena(canvasRef.current, { count: window.innerWidth < 768 ? 5200 : 9500 })
    } catch (err) {
      // No WebGL: the page still reads, it just has no 3D behind it.
      console.warn('The 3D scene is unavailable:', err)
    }
    return () => { arena.current?.dispose(); arena.current = null }
  }, [])

  useImperativeHandle(ref, () => ({
    setChapter: (c) => arena.current?.setChapter(c),
    setLayout: (l) => arena.current?.setLayout(l),
    pulse: (d) => arena.current?.pulse(d),
    fitUnder: (px, scale) => arena.current?.fitUnder(px, scale) ?? null,
  }), [])

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />
})

export default ArenaCanvas
