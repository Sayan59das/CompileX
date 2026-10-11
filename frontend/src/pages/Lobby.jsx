import React, { useEffect, useState, useRef } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { connectSocket } from '../services/socket'
import { useAuth } from '../context/AuthContext'
import Icon from '../components/Icons'

// ── Animated waiting indicator ───────────────────────────────────────────────
function PulseDot() {
  return (
    <span className="relative flex w-2.5 h-2.5">
      <span className=" absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
      <span className="relative inline-flex rounded-full w-2.5 h-2.5 bg-emerald-400" />
    </span>
  )
}

// ── Player avatar with initials ──────────────────────────────────────────────
function Avatar({ name, size = 'md', isYou = false }) {
  const colors = ['from-blue-600 to-cyan-600','from-blue-600 to-cyan-500','from-emerald-600 to-teal-500','from-orange-500 to-red-500','from-cyan-600 to-rose-500']
  const idx = name ? name.charCodeAt(0) % colors.length : 0
  const sz = size === 'lg' ? 'w-12 h-12 text-lg' : 'w-9 h-9 text-sm'
  return (
    <div className={`relative ${sz} rounded-xl bg-gradient-to-br ${colors[idx]} flex items-center justify-center font-extrabold text-white shadow-lg flex-shrink-0`}>
      {name?.[0]?.toUpperCase()}
      {isYou && <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-blue-500 border-2 border-[#060a12] flex items-center justify-center"><svg width="7" height="7" viewBox="0 0 24 24" fill="white"><path d="M20 6L9 17l-5-5"/></svg></div>}
    </div>
  )
}

// ── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, icon }) {
  return (
    <div className="flex flex-col items-center py-4 px-3 rounded-2xl bg-white/[0.03] border border-white/[0.07] hover:border-blue-500/25 hover:bg-blue-500/5 transition-all duration-300 group">
      <Icon name={icon} size={18} className="mb-1 text-slate-400" />
      <span className="text-xl font-extrabold text-white">{value}</span>
      <span className="text-[10px] text-slate-500 font-semibold mt-0.5">{label}</span>
    </div>
  )
}

export default function Lobby() {
  const { code }  = useParams()
  const { state } = useLocation()
  const { user }  = useAuth()
  const nav       = useNavigate()

  const [players, setPlayers] = useState(() => {
    if (state?.lobby && state?.player_id && user?.username)
      return [{ id: state.player_id, username: user.username, score: 0 }]
    return []
  })
  const [copied, setCopied]         = useState(false)
  const [lobbyState, setLobbyState] = useState(null)
  const [startError, setStartError] = useState('')
  const [countdown, setCountdown]   = useState(null)
  const dots = useRef([...Array(3)].map(() => ({ x: Math.random() * 100, y: Math.random() * 100 })))

  const lobby    = lobbyState || state?.lobby
  const playerId = state?.player_id

  useEffect(() => {
    if (!lobby || !playerId) { nav('/home'); return }
    const socket = connectSocket()

    socket.on('lobby_state', (data) => {
      const inc = data.players || []
      setPlayers(prev => inc.length > 0 ? inc : prev.length > 0 ? prev : inc)
      setLobbyState(data)
    })
    socket.on('player_joined', (data) => {
      setPlayers(prev => prev.find(p => p.id === data.player_id) ? prev : [...prev, { id: data.player_id, username: data.username, score: 0 }])
    })
    socket.on('player_left',   (data) => setPlayers(prev => prev.filter(p => p.id !== data.player_id)))
    socket.on('game_started',  (data) => {
      setCountdown(3)
      let c = 3
      const iv = setInterval(() => {
        c -= 1; setCountdown(c)
        if (c <= 0) {
          clearInterval(iv)
          nav(`/game/${code}`, { state: { lobby, player_id: playerId, started_at: data.started_at, time_limit: data.time_limit, num_rounds: data.num_rounds, questions_per_round: data.questions_per_round, time_per_question: data.time_per_question, game_mode: data.game_mode } })
        }
      }, 1000)
    })

    socket.emit('join_lobby', { lobby_id: lobby.id, player_id: playerId, user_id: user.id, username: user.username })
    return () => { socket.off('lobby_state'); socket.off('player_joined'); socket.off('player_left'); socket.off('game_started') }
  }, [])

  function startGame() {
    setStartError('')
    const socket = connectSocket()
    socket.emit('start_game', { lobby_id: lobby.id })
    socket.once('error', (data) => setStartError(data.message || 'Failed to start game'))
  }

  function copyCode() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const modeLabel = { multiplayer: 'Multiplayer', '1v1': '1v1 Battle', tournament: 'Tournament', solo: 'Solo Practice' }
  const modeIcon  = { multiplayer: 'users', '1v1': 'duel', tournament: 'trophy', solo: 'target' }
  const diff      = lobby?.difficulty || 'medium'
  const diffStyle = { easy: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25', medium: 'text-amber-400 bg-amber-500/10 border-amber-500/25', hard: 'text-rose-400 bg-rose-500/10 border-rose-500/25' }
  const topics    = lobby?.topics ? (typeof lobby.topics === 'string' ? JSON.parse(lobby.topics) : lobby.topics) : []
  const isHost    = lobby?.created_by && user?.id && lobby.created_by === user.id

  // ── Countdown overlay ────────────────────────────────────────────────────
  if (countdown !== null) {
    return (
      <div className="fixed inset-0 bg-[#040811] flex flex-col items-center justify-center z-50">
        <style>{`@keyframes countPop{0%{opacity:0;transform:scale(0.4)}60%{transform:scale(1.15)}100%{opacity:1;transform:scale(1)}}`}</style>
        <p className="text-slate-400 text-sm mb-8 font-bold">Match starting</p>
        <div key={countdown} className="text-[120px] font-extrabold text-white leading-none" style={{ animation: 'countPop 0.4s cubic-bezier(0.16,1,0.3,1)', background: 'linear-gradient(135deg,#60a5fa,#22d3ee)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          {countdown || 'GO!'}
        </div>
      </div>
    )
  }

  return (
    <>
      <style>{`
      `}</style>

      <div className="min-h-screen bg-[#040811] relative overflow-hidden" style={{ fontFamily: 'Inter, sans-serif' }}>
        {/* Background */}
        <div className="fixed inset-0 -z-10 pointer-events-none">
          <div className="absolute inset-0" style={{ backgroundImage: 'linear-gradient(rgba(59, 130, 246,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246,0.04) 1px, transparent 1px)', backgroundSize: '64px 64px' }} />
          <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-blue-600/8 rounded-full blur-[120px]"  />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-cyan-600/6 rounded-full blur-[100px]"  />
        </div>

        {/* Nav */}
        <nav className="border-b border-white/[0.05] bg-white/[0.02] backdrop-blur-sm px-6 py-3.5">
          <div className="max-w-xl mx-auto flex items-center justify-between">
            <button onClick={() => nav('/home')} className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center shadow-lg shadow-blue-500/20 transition-all duration-300">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              </div>
              <span className="font-extrabold text-white text-base tracking-tight">CompileX</span>
            </button>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.07]">
              <PulseDot />
              <span className="text-xs font-bold text-emerald-400">Waiting Room</span>
            </div>
          </div>
        </nav>

        {/* Content */}
        <div className="max-w-xl mx-auto px-4 py-8 space-y-4">

          {/* Title */}
          <div className="text-center pt-2 pb-2">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.07] text-xs font-bold text-slate-400 mb-4">
              <Icon name={modeIcon[lobby?.game_mode] || 'duel'} size={14} />
              {modeLabel[lobby?.game_mode] || 'Match'}
              {lobby?.is_public && <><span className="w-1 h-1 rounded-full bg-white/20" /><span className="text-emerald-400">Public</span></>}
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">{lobby?.name || 'Loading…'}</h1>
          </div>

          {/* Lobby code */}
          <div className="" style={{ animationDelay: '0.06s' }}>
            <button onClick={copyCode}
              className="relative w-full py-7 rounded-2xl border transition-all duration-300 overflow-hidden group active:scale-[0.99]"
              style={{ background: 'linear-gradient(135deg, rgba(59, 130, 246,0.08), rgba(244,114,182,0.05))', borderColor: copied ? 'rgba(59, 130, 246,0.5)' : 'rgba(255,255,255,0.08)' }}>
              {/* Shimmer on hover */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.04] to-transparent -translate-x-full transition-transform duration-700" />
              <p className="text-[10px] font-extrabold text-slate-500 mb-3">Lobby Code</p>
              <p className="font-mono font-extrabold text-5xl tracking-[0.18em] text-white" style={{ background: 'linear-gradient(135deg, #60a5fa, #22d3ee)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                {code}
              </p>
              <p className={`text-xs mt-3 font-semibold transition-colors duration-300 ${copied ? 'text-emerald-400' : 'text-slate-600 group-hover:text-slate-400'}`}>
                {copied ? 'Copied' : 'Tap to copy'}
              </p>
            </button>
          </div>

          {/* Match config */}
          <div className="" style={{ animationDelay: '0.12s' }}>
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-5">
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs font-bold text-slate-400">Match Config</p>
                <span className={`text-[10px] font-extrabold px-2.5 py-1 rounded-full border ${diffStyle[diff]}`}>{diff}</span>
              </div>
              <div className="grid grid-cols-4 gap-2">
                <StatCard label="Rounds"  value={lobby?.num_rounds || 1}                                      icon="refresh" />
                <StatCard label="Q/Round" value={lobby?.questions_per_round || 1}                             icon="list" />
                <StatCard label="Time"    value={`${Math.floor((lobby?.time_per_question || 600) / 60)}m`}    icon="clock" />
                <StatCard label="Max"     value={lobby?.max_players || 10}                                    icon="users" />
              </div>
              {topics.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-white/[0.05]">
                  {topics.map(t => (
                    <span key={t} className="text-[10px] px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 font-semibold capitalize">{t}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Players */}
          <div className="" style={{ animationDelay: '0.18s' }}>
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.05]">
                <p className="text-xs font-bold text-slate-400">Players</p>
                <div className="flex items-center gap-2">
                  <div className="flex -space-x-2">
                    {players.slice(0, 3).map((p, i) => (
                      <div key={i} className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-600 to-cyan-600 border border-[#040811] flex items-center justify-center text-[8px] font-extrabold text-white">
                        {p.username?.[0]?.toUpperCase()}
                      </div>
                    ))}
                  </div>
                  <span className="text-xs font-bold text-slate-400 bg-white/[0.05] px-2.5 py-1 rounded-full border border-white/[0.08]">
                    {players.length}<span className="text-slate-600">/{lobby?.max_players}</span>
                  </span>
                </div>
              </div>
              <div className="p-3 space-y-1.5 min-h-[80px]">
                {players.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-8 text-slate-600">
                    <Icon name="users" size={26} className="mx-auto mb-2" />
                    <p className="text-xs font-semibold">Waiting for players…</p>
                  </div>
                ) : (
                  players.map((p, i) => {
                    const isYou = p.username === user.username
                    return (
                      <div key={p.id ?? i} className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 hover:bg-white/[0.04]"
                        style={{ animationDelay: `${i * 60}ms`, background: isYou ? 'rgba(59, 130, 246,0.06)' : 'transparent', border: isYou ? '1px solid rgba(59, 130, 246,0.2)' : '1px solid transparent' }}>
                        <Avatar name={p.username} isYou={isYou} />
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-sm text-white">{p.username}</p>
                          {isYou && <p className="text-[10px] text-blue-400 font-semibold">That's you</p>}
                        </div>
                        <PulseDot />
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </div>

          {/* Action */}
          <div className="pb-8" style={{ animationDelay: '0.24s' }}>
            {isHost ? (
              <>
                <button onClick={startGame}
                  className="relative w-full py-4 rounded-2xl font-extrabold text-white text-base overflow-hidden group transition-all duration-300 active:scale-[0.98] hover:shadow-xl hover:shadow-blue-500/20">
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600" />
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                  {/* Shimmer */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full transition-transform duration-600" />
                  <span className="relative z-10 flex items-center justify-center gap-2">
                    <Icon name="play" size={14} />
                    Launch Match
                  </span>
                </button>
                {startError && (
                  <p className="text-center text-xs text-rose-400 mt-2 bg-rose-500/8 border border-rose-500/15 rounded-xl px-4 py-2.5">{startError}</p>
                )}
                <p className="text-center text-[11px] text-slate-600 mt-3">Only you can start — you created this lobby</p>
              </>
            ) : (
              <div className="flex flex-col items-center gap-3 py-5">
                <div className="flex items-center gap-3 text-sm font-semibold text-amber-400">
                  <div className="flex gap-1">
                    {[0,1,2].map(i => (
                      <div key={i} className="w-2 h-2 rounded-full bg-amber-400" style={{ animation: `bounce 1.2s ${i * 0.15}s ease-in-out infinite` }} />
                    ))}
                  </div>
                  Waiting for host to start…
                </div>
                <p className="text-[11px] text-slate-600">Hang tight — the match will begin shortly</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
