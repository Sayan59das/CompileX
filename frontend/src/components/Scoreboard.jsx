import React, { useEffect, useMemo, useRef, useState } from 'react'
import { balloonFill } from '../utils/balloons'
import Icon from './Icons'

// A sample match, scripted. It plays once and stops on the final standings,
// because the rule it demonstrates (first correct answer counts) only needs
// to be seen once. Rows move only when somebody's rank actually changes.

const PROBLEMS = [
  { id: 'A', color: 'tomato', points: 100 },
  { id: 'B', color: 'sky', points: 200 },
  { id: 'C', color: 'grass', points: 300 },
]
const PLAYERS = ['mira', 'dex', 'ola', 'you']

const TOTAL_MS = 11000
const MATCH_MINUTES = 20
const PLAYED_MINUTES = 15 // match minutes covered by the scripted run

// at: ms into the demo.  ok: false is a wrong submission.
const EVENTS = [
  { at: 1100, who: 'dex', p: 'A', ok: true },
  { at: 2300, who: 'mira', p: 'A', ok: true },
  { at: 3200, who: 'you', p: 'A', ok: false },
  { at: 4200, who: 'you', p: 'A', ok: true },
  { at: 5200, who: 'mira', p: 'B', ok: true },
  { at: 6200, who: 'ola', p: 'A', ok: true },
  { at: 7300, who: 'you', p: 'B', ok: true },
  { at: 8300, who: 'dex', p: 'B', ok: true },
  { at: 9800, who: 'you', p: 'C', ok: true },
]

const toMinutes = (ms) => (ms / TOTAL_MS) * PLAYED_MINUTES
const fmt = (minutes) => {
  const total = Math.max(0, Math.round(minutes * 60))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/** Standings after `now` ms of the script. Pure, so replay is just now = 0. */
function standingsAt(now) {
  const table = Object.fromEntries(
    PLAYERS.map((name) => [
      name,
      { name, points: 0, penalty: 0, cells: Object.fromEntries(PROBLEMS.map((p) => [p.id, { solvedAt: null, wrong: 0 }])) },
    ])
  )
  for (const e of EVENTS) {
    if (e.at > now) break
    const row = table[e.who]
    const cell = row.cells[e.p]
    if (!e.ok) { cell.wrong += 1; continue }
    cell.solvedAt = toMinutes(e.at)
    row.points += PROBLEMS.find((p) => p.id === e.p).points
    row.penalty += cell.solvedAt + cell.wrong * 20
  }
  const ranked = Object.values(table).sort(
    (a, b) => b.points - a.points || a.penalty - b.penalty || PLAYERS.indexOf(a.name) - PLAYERS.indexOf(b.name)
  )
  ranked.forEach((r, i) => { r.rank = i })
  return table
}

const ROW = 56
const COLS = 'grid-cols-[28px_minmax(0,1fr)_repeat(3,48px)_52px] sm:grid-cols-[32px_minmax(0,1fr)_repeat(3,60px)_64px]'

function Balloon({ color, solved, wrong }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-0.5">
      <span
        className="relative block h-6 w-6 rounded-full border-2 transition-transform duration-200 sm:h-7 sm:w-7"
        style={{
          borderColor: solved ? balloonFill(color) : 'rgb(var(--line-strong))',
          background: solved ? balloonFill(color) : 'transparent',
          transform: solved ? 'scale(1)' : 'scale(0.86)',
        }}
      >
        {!solved && wrong > 0 && (
          <Icon name="x" size={12} strokeWidth={2.6} className="absolute inset-0 m-auto text-tomato-ink" />
        )}
        {solved && <Icon name="check" size={13} strokeWidth={3} className="absolute inset-0 m-auto text-white" />}
      </span>
      <span className="tnum h-3 text-[10px] font-medium leading-none text-ink-3">
        {solved ? fmt(solved) : wrong > 0 ? `−${wrong}` : ''}
      </span>
    </div>
  )
}

export default function Scoreboard({ autoplay = true, className = '' }) {
  const reduceMotion = useMemo(
    () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
    []
  )
  const playing = autoplay && !reduceMotion
  const [now, setNow] = useState(playing ? 0 : TOTAL_MS)
  const timer = useRef(null)

  const start = () => {
    clearInterval(timer.current)
    setNow(0)
    const began = performance.now()
    timer.current = setInterval(() => {
      const t = Math.min(TOTAL_MS, performance.now() - began)
      setNow(t)
      if (t >= TOTAL_MS) clearInterval(timer.current)
    }, 100)
  }

  useEffect(() => {
    if (playing) start()
    return () => clearInterval(timer.current)
  }, [playing])

  const table = standingsAt(now)
  const done = now >= TOTAL_MS
  const remaining = MATCH_MINUTES - toMinutes(now)

  return (
    <figure className={`slab overflow-hidden ${className}`} data-theme="dark">
      <div className="flex items-center justify-between border-b border-line px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2.5">
          <span className="chip">Sample match</span>
          <span className="hidden text-sm text-ink-3 sm:inline">Room 4F2K</span>
        </div>
        <div className="flex items-baseline gap-2" aria-hidden="true">
          <span className="numeral text-3xl text-ink">{fmt(remaining)}</span>
          <span className="text-xs font-medium text-ink-3">left</span>
        </div>
      </div>

      <div aria-hidden="true">
        <div className={`grid ${COLS} items-center gap-x-1 border-b border-line px-4 py-2 text-xs font-semibold text-ink-3 sm:px-5`}>
          <span>#</span>
          <span>Player</span>
          {PROBLEMS.map((p) => (
            <span key={p.id} className="flex items-center justify-center gap-1.5">
              <span className="dot" style={{ background: balloonFill(p.color) }} />
              {p.id}
            </span>
          ))}
          <span className="text-right">Points</span>
        </div>

        <div className="relative" style={{ height: ROW * PLAYERS.length }}>
          {PLAYERS.map((name) => {
            const row = table[name]
            const isYou = name === 'you'
            return (
              <div
                key={name}
                className={`absolute inset-x-0 grid ${COLS} items-center gap-x-1 border-b border-line px-4 sm:px-5 ${
                  isYou ? 'bg-sun/15' : ''
                }`}
                style={{
                  height: ROW,
                  transform: `translateY(${row.rank * ROW}px)`,
                  transition: 'transform 450ms cubic-bezier(0.3, 0.7, 0.2, 1)',
                }}
              >
                <span className={`numeral text-2xl ${row.rank === 0 ? 'text-sun' : 'text-ink-2'}`}>{row.rank + 1}</span>
                <span className="truncate text-base font-semibold text-ink">{name}</span>
                {PROBLEMS.map((p) => (
                  <Balloon key={p.id} color={p.color} solved={row.cells[p.id].solvedAt} wrong={row.cells[p.id].wrong} />
                ))}
                <span className="numeral text-right text-2xl text-ink">{row.points}</span>
              </div>
            )
          })}
        </div>
      </div>

      <figcaption className="flex items-center justify-between gap-3 px-4 py-3 text-sm text-ink-3 sm:px-5">
        <span>{done ? 'Final standings: ranked by points, then by time.' : 'Standings update as each solution passes.'}</span>
        {autoplay && done && (
          <button type="button" onClick={start} className="inline-flex items-center gap-1.5 font-semibold text-ink-2 hover:text-ink">
            <Icon name="refresh" size={14} />
            Replay
          </button>
        )}
      </figcaption>

      <p className="sr-only">
        Sample match: after fifteen minutes you lead with three problems solved, ahead of mira, dex and ola.
      </p>
    </figure>
  )
}
