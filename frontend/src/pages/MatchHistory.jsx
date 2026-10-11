import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const modeIcon = {
  multiplayer: 'users',
  '1v1': 'duel',
  tournament: 'trophy',
  solo: 'target',
}

import AnimatedBackgroundCSS from '../components/AnimatedBackgroundCSS'
import Icon from '../components/Icons'

export default function MatchHistory() {
  const { user } = useAuth()
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
    <div className="min-h-screen relative overflow-hidden bg-[#0a0f1c]">
      <AnimatedBackgroundCSS />

      <nav className="relative border-b border-white/10 backdrop-blur-xl bg-slate-900/50 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => nav('/profile')} className="text-slate-400 hover:text-white transition-colors duration-300 flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Profile
            </button>
            <div className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Match History</div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 backdrop-blur-sm border border-white/10">
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-sm text-slate-300">{user?.username}</span>
          </div>
        </div>
      </nav>

      <div className="relative max-w-4xl mx-auto px-6 py-10 ">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent mb-2">Your Battles</h1>
          <p className="text-slate-400 text-sm">{total} matches played</p>
        </div>

        {loading ? (
          <div className="text-center py-12 text-slate-500 animate-pulse">Loading matches...</div>
        ) : matches.length === 0 ? (
          <div className="relative overflow-hidden rounded-3xl bg-[#0a0f1c]/60 backdrop-blur-xl border border-white/[0.05] p-12 sm:p-16 text-center shadow-2xl">
            {/* Glowing background effects inside the card */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[200px] bg-gradient-to-b from-blue-500/10 to-transparent pointer-events-none" />
            <div className="absolute -bottom-[50px] -right-[50px] w-[200px] h-[200px] bg-cyan-500/10 blur-[80px] pointer-events-none rounded-full" />
            <div className="absolute -top-[50px] -left-[50px] w-[200px] h-[200px] bg-blue-600/10 blur-[80px] pointer-events-none rounded-full" />
            
            <div className="relative z-10 flex flex-col items-center">
              {/* Animated Radar/Matchmaking Icon */}
              <div className="relative flex items-center justify-center w-24 h-24 mb-6">
                <div className="absolute inset-0 rounded-full border border-blue-500/30 " style={{ animationDuration: '3s' }} />
                <div className="absolute inset-2 rounded-full border border-cyan-400/20 " style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
                <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center shadow-[0_0_30px_rgba(59,130,246,0.5)]">
                  <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
              </div>
              
              <h2 className="text-2xl font-extrabold text-white mb-3 tracking-tight">No Battles Yet</h2>
              <p className="text-slate-400 max-w-md mx-auto mb-8 leading-relaxed">
                Your match history is currently empty. Step into the arena, compete against others, and start building your legacy!
              </p>
              
              <button 
                onClick={() => nav('/home')} 
                className="group relative px-8 py-3.5 rounded-xl bg-blue-500 text-white font-bold tracking-wide overflow-hidden transition-all active:scale-95 shadow-[0_0_20px_rgba(59,130,246,0.4)]"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-600 bg-[length:200%_auto] animate-[shine_3s_linear_infinite]" />
                <div className="absolute inset-0 bg-white/0 group-hover:bg-white/20 transition-colors" />
                <span className="relative z-10 flex items-center gap-2">
                  Find a Match
                  <svg className="w-4 h-4 transition-transform " fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </span>
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {matches.map((m, i) => {
                const isWin = m.player_rank === 1 && m.total_players > 1
                return (
                  <div
                    key={i}
                    className={`bg-white/5 backdrop-blur-sm border rounded-xl p-4 flex items-center gap-4 transition-all duration-300 hover:bg-white/10 hover:border-blue-500/30 group ${
 isWin ? 'border-emerald-500/50 shadow-lg shadow-emerald-500/10' : 'border-white/10'
                    }`}
                  >
                    <div className="text-2xl w-10 text-center shrink-0 transition-transform duration-300 ">
                      <Icon name={modeIcon[m.game_mode] || 'play'} size={22} className="mx-auto text-slate-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-semibold text-white text-sm truncate group-hover:text-blue-300 transition-colors duration-300">{m.lobby_name}</span>
                        <span className="text-[10px] text-slate-400 bg-white/5 border border-white/10 rounded-full px-2 py-0.5 shrink-0">{m.game_mode}</span>
                        {isWin && <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5 shrink-0 font-medium">WIN</span>}
                      </div>
                      <div className="text-xs text-slate-400">
                        {m.questions_solved} solved &middot; Rank #{m.player_rank} of {m.total_players} &middot; {new Date(m.played_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-lg font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">{m.player_score}</div>
                      <div className="text-[10px] text-slate-500">pts</div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center gap-2 mt-6">
                <button
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="text-xs px-3 py-1.5 rounded-lg bg-white/5 backdrop-blur-sm border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-30 transition-all duration-300"
                >
                  Prev
                </button>
                <span className="text-xs text-slate-400 px-3 py-1.5 bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="text-xs px-3 py-1.5 rounded-lg bg-white/5 backdrop-blur-sm border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 disabled:opacity-30 transition-all duration-300"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
