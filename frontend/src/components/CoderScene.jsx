import React, { lazy, Suspense, useEffect, useRef, useState } from 'react'

// The coder scene (three.js): someone at a desk writes code, the tests fail, they think, fix it, and the tests pass.
// three.js loads only when a page with the scene opens. Without WebGL the flat SVG version is shown instead.

const Flat = lazy(() => import('./CoderSceneFlat'))

export default function CoderScene({ className = '', lift = 0, fps = 45, dpr = 1.6, interactive = true, label = 'A developer at a desk writes code, hits a failing test, thinks it through, fixes it and the tests pass' }) {
  const ref = useRef(null)
  const [flat, setFlat] = useState(false)

  useEffect(() => {
    let dead = false
    let handle = null
    import('../three/coder')
      .then(({ createCoder }) => {
        if (dead || !ref.current) return
        try { handle = createCoder(ref.current, { lift, fps, dpr, interactive }) } catch (err) { console.warn('The 3D scene is unavailable:', err); setFlat(true) }
      })
      .catch(() => setFlat(true))
    return () => { dead = true; handle?.dispose() }
  }, [lift, fps, dpr, interactive])

  if (flat) {
    return (
      <div className={className}>
        <Suspense fallback={null}><Flat decorative className="block h-full w-full" /></Suspense>
      </div>
    )
  }
  return (
    <div className={className} role="img" aria-label={label}>
      <canvas ref={ref} className="block h-full w-full" />
    </div>
  )
}

// A big, fixed backdrop behind the signed-in pages. Content above it needs `relative z-10`.
export function SceneBackdrop() {
  return (
    <div className="cx-scene pointer-events-none fixed bottom-0 right-0 z-0 hidden md:block" aria-hidden="true">
      <CoderScene className="h-full w-full" interactive={false} fps={30} dpr={1.25} />
    </div>
  )
}
