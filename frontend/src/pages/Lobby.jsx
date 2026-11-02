import React, { useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { connectSocket } from '../services/socket'
import { useAuth } from '../context/AuthContext'
import { Check, Copy, Loader2, Play, Users } from 'lucide-react'
import AppShell from '../components/AppShell'
import { PageHeader, Panel, Button, Badge, Alert, EmptyState, Avatar } from '../components/ui'

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

  const modeLabel = { multiplayer: 'Multiplayer', '1v1': '1v1 duel', tournament: 'Tournament', solo: 'Solo practice' }
  const diff      = lobby?.difficulty || 'medium'
  const topics    = lobby?.topics ? (typeof lobby.topics === 'string' ? JSON.parse(lobby.topics) : lobby.topics) : []
  const isHost    = lobby?.created_by && user?.id && lobby.created_by === user.id

  // ── Countdown before the match ──────────────────────────────────────────
  if (countdown !== null) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black text-white" role="status" aria-live="assertive">
        <p className="mb-6 text-[15px] text-slate-400">Match starting</p>
        <div key={countdown} className="font-display text-[120px] font-bold leading-none tabular-nums animate-scale-in">
          {countdown || 'Go'}
        </div>
      </div>
    )
  }

  const settings = [
    ['Mode', modeLabel[lobby?.game_mode] || 'Multiplayer'],
    ['Difficulty', diff],
    ['Rounds', lobby?.num_rounds || 1],
    ['Questions per round', lobby?.questions_per_round || 1],
    ['Time per question', `${Math.floor((lobby?.time_per_question || 600) / 60)} min`],
    ['Max players', lobby?.max_players || 10],
  ]

  return (
    <AppShell>
      <PageHeader
        title={lobby?.name || 'Lobby'}
        description="Waiting room. Share the code so others can join."
        actions={
          <Button variant="secondary" icon={copied ? Check : Copy} onClick={copyCode} aria-label={`Copy room code ${code}`}>
            <span className="font-mono tracking-[0.15em]">{code}</span>
            <span className="text-slate-400">{copied ? 'Copied' : 'Copy'}</span>
          </Button>
        }
      />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Panel
          title="Players"
          action={<span className="font-mono text-[13px] tabular-nums text-slate-400">{players.length} / {lobby?.max_players || 10}</span>}
          bodyClassName=""
        >
          {players.length === 0 ? (
            <EmptyState icon={Users} title="Waiting for players">Players appear here as they join.</EmptyState>
          ) : (
            <ul>
              {players.map((p, i) => {
                const isYou = p.username === user.username
                return (
                  <li key={p.id ?? i} className="flex items-center gap-3 border-b border-white/5 px-5 py-3 animate-slide-right">
                    <Avatar name={p.username} size={32} />
                    <span className="min-w-0 flex-1 truncate text-[14px] text-white">{p.username}</span>
                    {isYou && <Badge tone="accent">You</Badge>}
                    {lobby?.created_by && p.user_id === lobby.created_by && <Badge>Host</Badge>}
                  </li>
                )
              })}
            </ul>
          )}
        </Panel>

        <div className="space-y-6">
          <Panel title="Match settings" bodyClassName="px-5 py-2">
            <dl className="divide-y divide-white/5">
              {settings.map(([k, v]) => (
                <div key={k} className="flex items-center justify-between py-2.5 text-[14px]">
                  <dt className="text-slate-400">{k}</dt>
                  <dd className="capitalize text-white">{v}</dd>
                </div>
              ))}
            </dl>
            {topics.length > 0 && (
              <div className="flex flex-wrap gap-1.5 border-t border-white/5 py-3">
                {topics.map(t => <Badge key={t} className="capitalize">{t}</Badge>)}
              </div>
            )}
          </Panel>

          {isHost ? (
            <div>
              <Button size="lg" icon={Play} className="w-full" onClick={startGame}>Start match</Button>
              {startError && <div className="mt-3"><Alert>{startError}</Alert></div>}
              <p className="mt-2 text-center text-[13px] text-slate-500">You created this room, so you start the match.</p>
            </div>
          ) : (
            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-[#0A0A0A] px-5 py-4 text-[14px] text-slate-300" role="status">
              <Loader2 className="h-4 w-4 animate-spin text-arc" aria-hidden="true" />
              Waiting for the host to start the match.
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
