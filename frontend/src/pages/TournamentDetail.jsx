import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const diffColor = {
  easy: 'text-emerald bg-emerald/10 border-emerald/20',
  medium: 'text-amber bg-amber/10 border-amber/20',
  hard: 'text-rose bg-rose/10 border-rose/20',
}

export default function TournamentDetail() {
  const { code } = useParams()
  const { user } = useAuth()
  const nav = useNavigate()

  const [tournament, setTournament] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [starting, setStarting] = useState(false)
  const [matchLobbyCode, setMatchLobbyCode] = useState(null)
  const [matchLobbyData, setMatchLobbyData] = useState(null)
  const [polling, setPolling] = useState(false)

  useEffect(() => { fetchTournament() }, [code])

  // Poll for match lobby once tournament is in_progress
  useEffect(() => {
    if (!tournament || tournament.status !== 'in_progress') return
    const isParticipant = tournament.participants?.some(p => p.user_id === user?.id)
    if (!isParticipant) return

    setPolling(true)
    const interval = setInterval(async () => {
      try {
        const { data } = await api.get(`/tournaments/${code}/my-match`)
        if (data.lobby_code) {
          clearInterval(interval)
          setPolling(false)
          try {
            const { data: lobby } = await api.get(`/lobbies/${data.lobby_code}`)
            const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
            setMatchLobbyData({ lobby, player_id: player.player_id })
          } catch(e) { console.error(e) }
          setMatchLobbyCode(data.lobby_code)
        }
      } catch { /* ignore */ }
    }, 1500)
    return () => clearInterval(interval)
  }, [tournament?.status])

  async function fetchTournament() {
    try {
      const { data } = await api.get(`/tournaments/${code}`)
      setTournament(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Tournament not found')
    } finally {
      setLoading(false)
    }
  }

  async function startTournament() {
    setStarting(true)
    setError('')
    try {
      await api.post(`/tournaments/${code}/start`)
      await fetchTournament()  // refresh to trigger the polling useEffect
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start tournament')
    } finally {
      setStarting(false)
    }
  }

  async function joinTournament() {
    try {
      await api.post(`/tournaments/${code}/join`)
      fetchTournament()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to join')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080b14]">
        <div className="text-slate-400 animate-pulse">Loading tournament...</div>
      </div>
    )
  }

  if (error && !tournament) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080b14]">
        <div className="text-center">
          <p className="text-rose mb-4">{error}</p>
          <button onClick={() => nav('/tournaments')} className="btn-primary">Back to Tournaments</button>
        </div>
      </div>
    )
  }

  const t = tournament
  const isParticipant = t?.participants?.some(p => p.user_id === user?.id)
  const isCreator = t?.created_by === user?.id

  const statusLabel = {
    registration: 'Open for Registration',
    in_progress: 'In Progress',
    completed: 'Completed',
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-[#080b14]">
      <div className="absolute inset-0 bg-hero-glow pointer-events-none" />

      <nav className="relative border-b border-white/5 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => nav('/tournaments')} className="text-slate-400 hover:text-white transition">&larr; Tournaments</button>
          </div>
          <span className="text-sm text-slate-300">{user?.username}</span>
        </div>
      </nav>

      <div className="relative max-w-4xl mx-auto px-6 py-10">
        {error && (
          <div className="bg-rose/10 border border-rose/20 text-rose rounded-xl p-3 mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Match ready banner */}
        {matchLobbyCode && (
          <div className="flex items-center justify-between bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 mb-6 animate-pulse">
            <div className="flex items-center gap-3">
              <span className="text-2xl">⚔️</span>
              <div>
                <div className="text-emerald-400 font-bold">Your match is ready!</div>
                <div className="text-xs text-slate-400">Lobby: <span className="font-mono text-emerald-300">{matchLobbyCode}</span></div>
              </div>
            </div>
            <button
              onClick={() => matchLobbyData ? nav(`/lobby/${matchLobbyCode}`, { state: matchLobbyData }) : null}
              disabled={!matchLobbyData}
              className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm font-bold hover:shadow-lg hover:shadow-emerald-500/50 transition-all duration-300 disabled:opacity-50"
            >
              Go to Match →
            </button>
          </div>
        )}

        {/* Waiting for match banner */}
        {!matchLobbyCode && polling && (
          <div className="flex items-center gap-3 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-6">
            <div className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-amber-400 text-sm">Tournament started — waiting for your match to be assigned...</span>
          </div>
        )}

        {/* Header */}
        <div className="glass-panel p-8 mb-8 glow ">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-extrabold text-white mb-2">{t.name}</h1>
              <div className="flex items-center gap-2 mb-4">
                <span className={`text-xs px-3 py-1 rounded-full border font-medium ${
 t.status === 'registration' ? 'text-emerald bg-emerald/10 border-emerald/20' :
                  t.status === 'in_progress' ? 'text-amber bg-amber/10 border-amber/20' :
                  'text-slate-400 bg-white/5 border-white/10'
                }`}>
                  {statusLabel[t.status]}
                </span>
                <span className={`text-xs px-3 py-1 rounded-full border font-medium ${diffColor[t.difficulty]}`}>
                  {t.difficulty}
                </span>
                <span className="font-mono text-xs text-slate-400 glass rounded-full px-3 py-1">{t.code}</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold text-indigo-light">{t.participant_count}</div>
              <div className="text-xs text-slate-500">/ {t.max_participants} players</div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="bg-white/[0.03] rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-white">Bracket Round {t.current_bracket_round}</div>
              <div className="text-xs text-slate-500">Current Stage</div>
            </div>
            <div className="bg-white/[0.03] rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-white">{t.participant_count}</div>
              <div className="text-xs text-slate-500">Participants</div>
            </div>
            <div className="bg-white/[0.03] rounded-lg p-3 text-center">
              <div className="text-xl font-bold text-white">{Math.ceil(Math.log2(t.max_participants))}</div>
              <div className="text-xs text-slate-500">Bracket Rounds</div>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-6 flex gap-3 flex-wrap items-center">
            {t.status === 'registration' && !isParticipant && (
              <button onClick={joinTournament} className="btn-success py-2.5 px-6">
                Join Tournament
              </button>
            )}
            {isParticipant && (
              <span className="glass rounded-full px-4 py-2 text-sm text-emerald font-medium">You're registered!</span>
            )}
            {isCreator && t.status === 'registration' && (
              <div className="flex flex-col gap-1">
                <button
                  onClick={startTournament}
                  disabled={starting || (t.participants?.length ?? t.participant_count) < 2}
                  className="py-2.5 px-6 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 text-white text-sm font-medium hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {starting ? 'Starting...' : '🚀 Start Tournament'}
                </button>
                {(t.participants?.length ?? t.participant_count) < 2 && (
                  <span className="text-xs text-amber-400 text-center">Need at least 2 participants</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Participants */}
        <div className="glass-panel p-6 ">
          <h2 className="text-lg font-bold text-white mb-4">Participants</h2>
          {t.participants?.length === 0 ? (
            <p className="text-slate-500 text-center py-8">No participants yet</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {t.participants?.map((p, i) => (
                <div
                  key={p.user_id}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 border ${
 p.eliminated
                      ? 'bg-white/[0.01] border-white/5 opacity-50'
                      : p.user_id === user?.id
                        ? 'bg-indigo/10 border-indigo/30'
                        : 'bg-white/[0.03] border-white/5'
                  }`}
                >
                  <div className="text-xs text-slate-500 font-mono w-4">#{p.seed}</div>
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo to-violet flex items-center justify-center text-white text-xs font-bold">
                    {p.username?.[0]?.toUpperCase()}
                  </div>
                  <span className="font-medium text-sm text-white truncate">{p.username}</span>
                  {p.eliminated && <span className="text-[10px] text-rose ml-auto">Eliminated</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
