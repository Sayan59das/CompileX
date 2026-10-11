import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import AppHeader from '../components/AppHeader'
import Icon from '../components/Icons'

const MODE_LABEL = { multiplayer: 'Arena match', '1v1': '1v1 duel', tournament: 'Tournament', solo: 'Solo practice' }

export default function MatchHistory() {
  const nav = useNavigate()

  const [matches, setMatches] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const limit = 15

  useEffect(() => { fetchHistory() }, [page])

  async function fetchHistory() {
    setLoading(true)
    try {
      const { data } = await api.get(`/users/me/history?limit=${limit}&offset=${page * limit}`)
      setMatches(data.matches)
      setTotal(data.total)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h1 className="display text-[clamp(2.4rem,5vw,3.75rem)]">Match history</h1>
          {total > 0 && <p className="tnum text-ink-2">{total} {total === 1 ? 'match' : 'matches'} played</p>}
        </div>

        {loading ? (
          <p className="py-12 text-ink-2" role="status">Loading your matches…</p>
        ) : matches.length === 0 ? (
          <div className="py-16">
            <p className="stretch-narrow text-3xl font-extrabold tracking-tight">You have not played a match yet</p>
            <p className="measure mt-2 text-ink-2">Create a room from the dashboard, or join one with a code, and it will be listed here.</p>
            <button onClick={() => nav('/dashboard')} className="btn btn-primary mt-6">Go to the dashboard</button>
          </div>
        ) : (
          <>
            <div className="panel mt-8 overflow-hidden">
              <div className="hidden grid-cols-[7rem_minmax(0,1fr)_6rem_8rem_5rem] gap-4 border-b border-line bg-sunken px-5 py-2.5 text-sm font-medium text-ink-3 md:grid">
                <span>Result</span>
                <span>Room</span>
                <span>Solved</span>
                <span>Played</span>
                <span className="text-right">Points</span>
              </div>
              <ul className="divide-y divide-line">
                {matches.map((m, i) => {
                  const isWin = m.player_rank === 1 && m.total_players > 1
                  return (
                    <li
                      key={i}
                      className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 px-5 py-4 md:grid-cols-[7rem_minmax(0,1fr)_6rem_8rem_5rem]"
                    >
                      <span className="flex items-center gap-2 font-semibold md:order-none">
                        <span className="dot" style={{ background: isWin ? 'rgb(var(--grass))' : 'rgb(var(--line-strong))' }} />
                        {isWin ? 'Won' : `Rank ${m.player_rank} of ${m.total_players}`}
                      </span>
                      <span className="col-span-2 min-w-0 md:col-span-1">
                        <span className="block truncate font-semibold">{m.lobby_name}</span>
                        <span className="text-sm text-ink-3">{MODE_LABEL[m.game_mode] || m.game_mode}</span>
                      </span>
                      <span className="tnum text-ink-2">{m.questions_solved} solved</span>
                      <span className="tnum text-ink-2">{new Date(m.played_at).toLocaleDateString()}</span>
                      <span className="numeral text-right text-2xl md:order-none">{m.player_score}</span>
                    </li>
                  )
                })}
              </ul>
            </div>

            {totalPages > 1 && (
              <nav className="mt-6 flex items-center justify-between" aria-label="Pagination">
                <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="btn btn-secondary btn-sm">
                  <Icon name="arrow-left" size={14} /> Newer
                </button>
                <span className="tnum text-sm text-ink-2">Page {page + 1} of {totalPages}</span>
                <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="btn btn-secondary btn-sm">
                  Older <Icon name="arrow-right" size={14} />
                </button>
              </nav>
            )}
          </>
        )}
      </main>
    </div>
  )
}
