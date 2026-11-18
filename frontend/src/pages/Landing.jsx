import React, { useState, useEffect, useLayoutEffect, useRef } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import Lenis from 'lenis'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import ArenaCanvas from '../components/ArenaCanvas'
import './landing.css'

// ───────────────────────────────────────────────────────────────────────────
// Four chapters on black. A 3D laptop sits behind the page, somebody typing code on it, and the scroll steers it: it opens as
// you arrive, turns toward the match, swings side-on for the modes, and shuts at the end. The
// match in the middle is played by scrolling.
// ───────────────────────────────────────────────────────────────────────────

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
// how far below the top of the screen the match is pinned: just under the navigation bar
const PIN_TOP = 108
const ease = (t) => 1 - Math.pow(1 - t, 3)

const CHAPTERS = [
  { id: 'top', label: 'Arena' },
  { id: 'match', label: 'A match' },
  { id: 'modes', label: 'Modes' },
  { id: 'start', label: 'Start' },
]

// Where the laptop sits (x, y in world units), how big it is and how visible, per chapter. On a phone it stays centred and dim
// so the words stay readable.
const LAYOUT = {
  desktop: {
    offsets: [3.0, 0, 3.9, 3.3],
    ys: [0, 0, 0, 0.35],
    scales: [1.38, 0.9, 1.06, 0.95],
    opacities: [1, 0.22, 1, 1],
  },
  mobile: {
    offsets: [0, 0, 0, 0],
    ys: [-3.2, 0, 0, -2.6],
    scales: [0.72, 0.7, 0.7, 0.72],
    opacities: [0.85, 0.12, 0.16, 0.5],
  },
}

// Which chapter the page is on, as a continuous number. A chapter owns the page from its top to the top of the next one; the
// change of pose plays out over the last stretch of a chapter, so the new pose has arrived as the new section does.
function chapterCoord(els) {
  const vh = window.innerHeight
  const y = vh * 0.5
  const tops = els.map((e) => (e ? e.getBoundingClientRect().top : Infinity))
  const n = els.length
  if (y < tops[0]) return 0
  let i = 0
  for (let k = 0; k < n; k++) if (y >= tops[k]) i = k
  if (i === n - 1) return n - 1
  const bottom = tops[i + 1]
  const zone = Math.min(vh * 0.9, (bottom - tops[i]) * 0.5)
  const t = clamp((y - (bottom - zone)) / zone, 0, 1)
  return i + t * t * (3 - 2 * t)
}

// ── small pieces ───────────────────────────────────────────────────────────
function Words({ text, start = 0 }) {
  return text.split(' ').map((w, i) => (
    <React.Fragment key={i}>
      <span className="lp-word" aria-hidden="true"><span style={{ '--i': start + i }}>{w}</span></span>{' '}
    </React.Fragment>
  ))
}

function Arrow({ className = '' }) {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M4 12h15M13 6l6 6-6 6" />
    </svg>
  )
}

function Tilt({ children, max = 8, className = '' }) {
  const ref = useRef(null)
  const move = (e) => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width
    const y = (e.clientY - r.top) / r.height
    el.style.transform = `perspective(800px) rotateX(${((0.5 - y) * max).toFixed(2)}deg) rotateY(${((x - 0.5) * max).toFixed(2)}deg)`
    el.style.setProperty('--mx', `${(x * 100).toFixed(1)}%`)
    el.style.setProperty('--my', `${(y * 100).toFixed(1)}%`)
  }
  const leave = () => { if (ref.current) ref.current.style.transform = '' }
  return <div ref={ref} className={`tilt spot ${className}`} onPointerMove={move} onPointerLeave={leave}>{children}</div>
}

// syntax colour: the colour of the code is the product's own
const TOKEN = /(#.*$)|(\b(?:def|for|in|return|if|else)\b)|(\b(?:range|max|sum|min|len)\b)|(\b\d+\b)|(\w+|\s+|.)/g
const SYNTAX = { comment: '#737373', keyword: '#A387FF', builtin: '#3DE0FF', number: '#FFC857' }
function Code({ text }) {
  const out = []
  let i = 0
  for (const m of text.matchAll(TOKEN)) {
    const color = m[1] ? SYNTAX.comment : m[2] ? SYNTAX.keyword : m[3] ? SYNTAX.builtin : m[4] ? SYNTAX.number : undefined
    out.push(<span key={i++} style={color ? { color } : undefined}>{m[0]}</span>)
  }
  return <>{out}</>
}

const SOLUTION = [
  'def max_gain(n, prices):',
  '    best = cur = 0',
  '    for p in prices:',
  '        cur = max(0, cur + p)',
  '        best = max(best, cur)',
  '    return best',
]

const MODES = [
  { name: 'Practice', to: '/practice', text: 'Solve alone, in five languages.' },
  { name: 'Skill rating', to: '/skill-assessment', text: 'Five questions set your level.' },
  { name: 'Arena', to: '/dashboard', text: 'Race a lobby on one problem.' },
  { name: 'Tournament', to: '/tournaments', text: 'Win your bracket.' },
]

// ── the match, played by scrolling ─────────────────────────────────────────
function MatchSection() {
  const ref = useRef(null)
  const pin = useRef(null)
  const [p, setP] = useState(0)

  useEffect(() => {
    let frame = 0
    const measure = () => {
      frame = 0
      const el = ref.current
      if (!el || !pin.current) return
      const r = el.getBoundingClientRect()
      const span = Math.max(1, r.height - pin.current.offsetHeight)
      const v = clamp((PIN_TOP - r.top) / span, 0, 1)
      setP((prev) => (Math.abs(prev - v) > 0.002 ? v : prev))
    }
    // one measurement per frame, however many scroll events arrive
    const on = () => { if (!frame) frame = requestAnimationFrame(measure) }
    measure()
    window.addEventListener('scroll', on, { passive: true })
    window.addEventListener('resize', on)
    return () => { cancelAnimationFrame(frame); window.removeEventListener('scroll', on); window.removeEventListener('resize', on) }
  }, [])

  const full = SOLUTION.join('\n')
  const typed = Math.floor(ease(clamp((p - 0.03) / 0.3, 0, 1)) * full.length)
  const lines = full.slice(0, typed).split('\n')
  const passes = Math.floor(clamp((p - 0.36) / 0.16, 0, 1) * 5)
  const rivalPasses = Math.floor(clamp((p - 0.22) / 0.4, 0, 1) * 3)
  const done = p >= 0.52
  const won = p >= 0.57
  const status = p < 0.05 ? 'Ready' : typed < full.length ? 'Writing' : passes < 5 ? 'Running tests' : 'All tests passed'
  const e = ease(clamp(p / 0.1, 0, 1))
  const rivalBar = clamp((p - 0.05) / 0.6, 0, 1) * 0.8

  return (
    <section id="match" ref={ref} className="relative z-10 pt-6" style={{ height: '165vh' }} data-chapter>
      <div ref={pin} className="sticky pb-6" style={{ top: PIN_TOP }}>
        <div className="mx-auto w-full max-w-[1280px] px-5 md:px-8">
          <h2 className="display mb-7 text-[clamp(2.1rem,4vw,3.5rem)] text-white">
            Two coders. One problem. <span className="text-arc">One winner.</span>
          </h2>

          <div className="grid gap-5 lg:grid-cols-12" style={{ perspective: '1400px' }}>
            {/* editor */}
            <div
              className="lp-panel-solid flex flex-col overflow-hidden lg:col-span-7"
              style={{ transform: `rotateY(${(1 - e) * -14}deg) rotateX(${(1 - e) * 6}deg) translateY(${(1 - e) * 40}px)`, opacity: 0.35 + 0.65 * e, transformOrigin: '0% 50%' }}
            >
              <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
                <span className="font-mono text-[14px] text-slate-400">max_gain.py</span>
                <span className={`rounded-md border px-2.5 py-1 text-[13px] font-semibold ${done ? 'border-pass/40 text-pass' : 'border-white/15 text-slate-300'}`}>{status}</span>
              </div>
              <div className="min-h-[180px] flex-1 py-3 font-mono text-[14px] leading-[1.75] md:min-h-[200px] md:text-[16px]">
                {lines.map((l, i) => (
                  <div key={i} className="flex whitespace-pre">
                    <span className="w-11 shrink-0 select-none pr-4 text-right text-slate-600">{i + 1}</span>
                    <span className="min-w-0 pr-4">
                      <Code text={l} />
                      {i === lines.length - 1 && !done && <span className="cursor-blink ml-px inline-block h-[1.05em] w-[6px] translate-y-[2px] bg-arc" />}
                    </span>
                  </div>
                ))}
              </div>
              <dl className="grid grid-cols-3 border-t border-white/10">
                {[
                  ['Tests', `${passes} / 5`, passes === 5 ? '#35F2A0' : undefined],
                  ['Time', done ? 'O(n)' : '...', done ? '#3DE0FF' : undefined],
                  ['Space', done ? 'O(1)' : '...', done ? '#3DE0FF' : undefined],
                ].map(([k, v, c], i) => (
                  <div key={k} className={`px-5 py-3 ${i > 0 ? 'border-l border-white/10' : ''}`}>
                    <dt className="text-[12px] font-semibold uppercase tracking-[0.1em] text-slate-500">{k}</dt>
                    <dd className="mt-1 font-mono text-[18px] font-semibold tabular-nums" style={{ color: c || '#F2F2F2' }}>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* scoreboard */}
            <div
              className="lp-panel-solid p-6 lg:col-span-5"
              style={{ transform: `rotateY(${(1 - e) * 14}deg) rotateX(${(1 - e) * 6}deg) translateY(${(1 - e) * 40}px)`, opacity: 0.35 + 0.65 * e, transformOrigin: '100% 50%' }}
            >
              <div className="flex items-end justify-between">
                <span className="text-[13px] font-semibold uppercase tracking-[0.12em] text-slate-400">Scoreboard</span>
              </div>
              <div className="my-5 h-px bg-white/10" />

              {[
                { who: 'You', color: '#3DE0FF', cells: passes, bar: clamp((typed / full.length) * 0.99, 0, 1), note: passes === 5 ? '5 / 5 passed' : status },
                { who: 'Rival', color: '#9B7BFF', cells: rivalPasses, bar: rivalBar, note: won ? 'Still running' : `${rivalPasses} / 5 passing` },
              ].map((r) => (
                <div key={r.who} className="mb-5 last:mb-0">
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="flex items-center gap-2 text-[18px] font-semibold" style={{ color: r.color }}>
                      <span className="h-2.5 w-2.5 rounded-sm" style={{ background: r.color }} />{r.who}
                    </span>
                    <span className="font-mono text-[13px] text-slate-400">{r.note}</span>
                  </div>
                  <div className="sim-bar mb-2"><i style={{ background: r.color, transform: `scaleX(${r.bar})` }} /></div>
                  <div className="grid grid-cols-5 gap-2">
                    {Array.from({ length: 5 }, (_, i) => <span key={i} className={`sim-cell ${i < r.cells ? 'on' : ''}`} />)}
                  </div>
                </div>
              ))}

              <div className={`mt-6 rounded-xl border px-4 py-3.5 transition-all duration-500 ${won ? 'border-pass/50 bg-pass/10 opacity-100' : 'border-white/10 opacity-40'}`}>
                <div className={`font-display text-[20px] font-bold tracking-tight ${won ? 'text-pass' : 'text-slate-400'}`}>{won ? 'You solved it first' : 'Match in progress'}</div>
                <div className="mt-1 text-[15px] text-slate-400">{won ? 'All five hidden tests passed before the rival finished.' : 'Keep scrolling.'}</div>
              </div>
            </div>
          </div>
          <p className="mt-5 text-[15px] text-slate-500">A simulated match. Hidden tests and a locked harness, graded on the server.</p>
        </div>
      </div>
    </section>
  )
}

// ── page ───────────────────────────────────────────────────────────────────
export default function Landing() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const { hash } = useLocation()
  const arena = useRef(null)
  const [active, setActive] = useState(0)

  useLayoutEffect(() => {
    document.documentElement.classList.add('lp-js')
    return () => document.documentElement.classList.remove('lp-js')
  }, [])

  // OAuth callback: the provider sends the player back here with a token.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    const username = params.get('username')
    const oauthSuccess = params.get('oauth_success')
    const oauthError = params.get('oauth_error')

    if (oauthError) {
      console.error('OAuth error:', oauthError)
      window.history.replaceState({}, document.title, window.location.pathname)
      return
    }
    if (oauthSuccess === 'true' && token && username) {
      localStorage.setItem('token', token)
      login({ username }, token)
      window.history.replaceState({}, document.title, window.location.pathname)
      navigate('/home')
    }
  }, [login, navigate])

  // Section links from other pages arrive as /#modes etc.
  useEffect(() => {
    if (!hash) return
    const el = document.getElementById(hash.slice(1))
    if (el) el.scrollIntoView()
  }, [hash])

  // Smooth scrolling, and the loop that tells the 3D scene where the page is.
  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const lenis = reduce ? null : new Lenis({ lerp: 0.065, wheelMultiplier: 0.85, smoothWheel: true, anchors: true })
    if (lenis) window.__lenis = lenis
    const els = CHAPTERS.map((c) => document.getElementById(c.id))
    const root = document.documentElement
    const layout = () => arena.current?.setLayout(window.innerWidth < 900 ? LAYOUT.mobile : LAYOUT.desktop)
    layout()
    window.addEventListener('resize', layout)

    let raf = 0
    let lastY = window.scrollY
    let lastActive = 0
    const tick = (t) => {
      raf = requestAnimationFrame(tick)
      lenis?.raf(t)
      const y = window.scrollY
      arena.current?.pulse(y - lastY)
      lastY = y
      const c = chapterCoord(els)
      arena.current?.setChapter(c)
      const max = root.scrollHeight - window.innerHeight
      root.style.setProperty('--p', max > 0 ? (y / max).toFixed(4) : '0')
      const a = Math.round(c)
      if (a !== lastActive) { lastActive = a; setActive(a) }
    }
    raf = requestAnimationFrame(tick)

    // blocks arrive in 3D as they enter the screen
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target) } })
    }, { threshold: 0.14, rootMargin: '0px 0px -6% 0px' })
    const watch = () => document.querySelectorAll('[data-reveal]:not(.in)').forEach((el) => io.observe(el))
    watch()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', layout)
      io.disconnect()
      lenis?.destroy()
      delete window.__lenis
      root.style.removeProperty('--p')
    }
  }, [])

  const start = user ? '/dashboard' : '/register'
  const startLabel = user ? 'Go to dashboard' : 'Create account'

  return (
    <div className="lp-root relative min-h-screen overflow-x-clip bg-black font-sans text-white">
      <div className="lp-progress" aria-hidden="true" />

      {/* the 3D laptop, fixed behind everything */}
      <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
        <ArenaCanvas ref={arena} className="block h-full w-full" />
      </div>

      <Navbar />

      {/* chapter dots */}
      <nav className="fixed right-4 top-1/2 z-40 hidden -translate-y-1/2 flex-col items-center gap-3 md:flex" aria-label="Chapters">
        {CHAPTERS.map((c, i) => (
          <a key={c.id} href={`#${c.id}`} aria-label={c.label} title={c.label} className={`lp-dot ${active === i ? 'on' : ''}`} />
        ))}
      </nav>

      {/* ── 1. Arena ─────────────────────────────────────────────────────── */}
      <section id="top" data-chapter className="relative z-10 flex min-h-[88svh] items-center pb-6 pt-24">
        <div className="mx-auto w-full max-w-[1280px] px-5 md:px-8">
          <div className="max-w-[32rem] md:max-w-[40rem]">
            <h1 className="display text-[clamp(3.1rem,6.8vw,6.2rem)] text-white" aria-label="Outcode your rival.">
              <Words text="Outcode" start={0} /><br />
              <Words text="your" start={1} /><span className="text-rival"><Words text="rival." start={2} /></span>
            </h1>
            <p className="lp-in mt-7 text-[19px] leading-relaxed text-slate-300 md:text-[22px]" style={{ '--d': '1.05s' }}>
              Live coding matches on problems nobody has seen. You write the logic, we run the match.
            </p>
            <div className="lp-in mt-9 flex flex-wrap gap-4" style={{ '--d': '1.25s' }}>
              <Link to={start} className="btn btn-primary btn-lg">{startLabel}<Arrow /></Link>
              <a href="#match" className="btn btn-secondary btn-lg">Watch a match</a>
            </div>
            <p className="lp-in mt-8 text-[16px] text-slate-400" style={{ '--d': '1.45s' }}>Python · C++ · Java · JavaScript · C</p>
          </div>
        </div>
      </section>

      {/* ── 2. A match, played by scrolling ──────────────────────────────── */}
      <MatchSection />

      {/* ── 3. Modes ─────────────────────────────────────────────────────── */}
      <section id="modes" data-chapter className="relative z-10 py-14 md:py-20">
        <div className="mx-auto max-w-[1280px] px-5 md:px-8">
          <div className="lg:w-[57%]">
            <h2 data-reveal className="display text-[clamp(2.1rem,4.2vw,3.7rem)]">Four ways to <span className="text-rival">play.</span></h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              {MODES.map((m, i) => (
                <div key={m.name} data-reveal style={{ '--d': `${i * 0.07}s` }}>
                  <Tilt max={7} className="lp-panel">
                    <Link to={user ? m.to : '/register'} className="lp-mode group block p-7">
                      <span className="flex items-center justify-between">
                        <span className="font-display text-[25px] font-bold tracking-tight">{m.name}</span>
                        <Arrow className="arrow text-[24px] text-slate-400" />
                      </span>
                      <span className="mt-2 block text-[17px] leading-snug text-slate-400">{m.text}</span>
                    </Link>
                  </Tilt>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. Start ─────────────────────────────────────────────────────── */}
      <section id="start" data-chapter className="relative z-10 flex min-h-[56svh] items-center py-12 md:py-16">
        <div className="mx-auto w-full max-w-[1280px] px-5 md:px-8">
          <div className="lg:w-[52%]">
            <h2 data-reveal className="display text-[clamp(3rem,6.6vw,5.6rem)]">Your <span className="text-arc">move.</span></h2>
            <p data-reveal style={{ '--d': '0.06s' }} className="mt-4 max-w-md text-[19px] leading-relaxed text-slate-300">
              Take the five-question skill check, get your rating, then step into your first match.
            </p>
            <div data-reveal style={{ '--d': '0.12s' }} className="mt-8 flex flex-wrap gap-4">
              <Link to={start} className="btn btn-primary btn-xl">{startLabel}<Arrow /></Link>
              {!user && <Link to="/login" className="btn btn-secondary btn-xl">Log in</Link>}
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}
