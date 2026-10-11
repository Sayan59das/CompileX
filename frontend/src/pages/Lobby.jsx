import React, { useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { connectSocket } from '../services/socket'
import { useAuth } from '../context/AuthContext'
import AppHeader from '../components/AppHeader'
import Avatar, { DifficultyTag } from '../components/Avatar'
import Icon from '../components/Icons'

const MODE_LABEL = { multiplayer: 'Arena match', '1v1': '1v1 duel', tournament: 'Tournament', solo: 'Solo practice' }

function formatSeconds(total) {
  if (!total) return '—'
  if (total < 60) return `${total} sec`
  const m = Math.floor(total / 60)
  const s = total % 60
  return s ? `${m} min ${s} sec` : `${m} min`
}

export default function Lobby() {
  const { code } = useParams()
  const { state } = useLocation()
  const { user } = useAuth()
  const nav = useNavigate()

  const [players, setPlayers] = useState(() => {
    if (state?.lobby && state?.player_id && user?.username)
      return [{ id: state.player_id, username: user.username, score: 0 }]
    return []
  })
  const [copied, setCopied] = useState(false)
  const [lobbyState, setLobbyState] = useState(null)
  const [startError, setStartError] = useState('')
  const [countdown, setCountdown] = useState(null)

  const lobby = lobbyState || state?.lobby
  const playerId = state?.player_id

  useEffect(() => {
    if (!lobby || !playerId) { nav('/home'); return }
    const socket = connectSocket()

    socket.on('lobby_state', (data) => {
      const inc = data.players || []
      setPlayers((prev) => (inc.length > 0 ? inc : prev.length > 0 ? prev : inc))
      setLobbyState(data)
    })
    socket.on('player_joined', (data) => {
      setPlayers((prev) => (prev.find((p) => p.id === data.player_id) ? prev : [...prev, { id: data.player_id, username: data.username, score: 0 }]))
    })
    socket.on('player_left', (data) => setPlayers((prev) => prev.filter((p) => p.id !== data.player_id)))
    socket.on('game_started', (data) => {
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
    socket.once('error', (data) => setStartError(data.message || 'Could not start the match.'))
  }

  function copyCode() {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const difficulty = lobby?.difficulty || 'medium'
  const topics = lobby?.topics ? (typeof lobby.topics === 'string' ? JSON.parse(lobby.topics) : lobby.topics) : []
  const isHost = lobby?.created_by && user?.id && lobby.created_by === user.id

  // The only motion on this page: the numbers themselves, one per second.
  if (countdown !== null) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-ink text-paper" role="status" aria-live="assertive">
        <p className="h-7 text-xl font-medium text-paper/70">{countdown > 0 ? 'The match starts in' : ''}</p>
        <div className="numeral mt-2 text-[clamp(9rem,32vw,22rem)]" style={{ fontStretch: '62%' }}>
          {countdown > 0 ? countdown : 'Go'}
        </div>
      </div>
    )
  }

  const config = [
    ['Rounds', lobby?.num_rounds || 1],
    ['Questions per round', lobby?.questions_per_round || 1],
    ['Time per question', formatSeconds(lobby?.time_per_question || 600)],
    ['Max players', lobby?.max_players || 10],
  ]

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip">{MODE_LABEL[lobby?.game_mode] || 'Match'}</span>
          <span className="chip">{lobby?.is_public ? 'Public room' : 'Private room'}</span>
          <DifficultyTag level={difficulty} />
        </div>
        <h1 className="display mt-4 text-[clamp(2.2rem,4.8vw,3.5rem)]">{lobby?.name || 'Loading…'}</h1>

        <div className="mt-10 grid items-start gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <div className="space-y-8">
            <section className="panel p-6 sm:p-8">
              <p className="text-ink-2">Share this code. Anyone who enters it on the dashboard joins this room.</p>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
                <div
                  className="numeral select-all text-[clamp(3.5rem,11vw,6.5rem)] tracking-[0.12em]"
                  style={{ fontStretch: '72%' }}
                  aria-label={`Room code ${code.split('').join(' ')}`}
                >
                  {code}
                </div>
                <button onClick={copyCode} className="btn btn-secondary">
                  <Icon name={copied ? 'check' : 'copy'} size={16} />
                  {copied ? 'Copied' : 'Copy code'}
                </button>
              </div>
            </section>

            <section className="panel">
              <h2 className="border-b border-line px-6 py-4 font-bold">Match settings</h2>
              <dl>
                {config.map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between border-b border-line px-6 py-3.5 last:border-b-0">
                    <dt className="text-ink-2">{k}</dt>
                    <dd className="font-semibold tnum">{v}</dd>
                  </div>
                ))}
                {topics.length > 0 && (
                  <div className="flex items-start justify-between gap-6 px-6 py-3.5">
                    <dt className="text-ink-2">Topics</dt>
                    <dd className="flex flex-wrap justify-end gap-1.5">
                      {topics.map((t) => (
                        <span key={t} className="chip capitalize">{t}</span>
                      ))}
                    </dd>
                  </div>
                )}
              </dl>
            </section>
          </div>

          <div className="space-y-6">
            <section className="panel">
              <div className="flex items-center justify-between border-b border-line px-6 py-4">
                <h2 className="font-bold">Players</h2>
                <span className="tnum text-sm text-ink-2">
                  {players.length} of {lobby?.max_players}
                </span>
              </div>
              {players.length === 0 ? (
                <p className="px-6 py-8 text-sm text-ink-2">Waiting for players to join.</p>
              ) : (
                <ul>
                  {players.map((p, i) => {
                    const isYou = p.username === user.username
                    return (
                      <li
                        key={p.id ?? i}
                        className={`flex items-center gap-3 border-b border-line px-6 py-3.5 last:border-b-0 ${isYou ? 'bg-sun/15' : ''}`}
                      >
                        <Avatar name={p.username} size={34} />
                        <span className="flex-1 truncate font-semibold">{p.username}</span>
                        {isYou && <span className="chip">You</span>}
                      </li>
                    )
                  })}
                </ul>
              )}
            </section>

            {isHost ? (
              <div>
                <button onClick={startGame} className="btn btn-primary btn-lg w-full">
                  <Icon name="play" size={16} />
                  Start the match
                </button>
                {startError && (
                  <p role="alert" className="mt-3 flex items-start gap-2 text-sm font-medium text-tomato-ink">
                    <Icon name="alert" size={16} className="mt-0.5" />
                    {startError}
                  </p>
                )}
                <p className="mt-3 text-sm text-ink-3">You created this room, so only you can start it.</p>
              </div>
            ) : (
              <div className="panel-sunken flex items-center gap-3 px-5 py-4" role="status">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-ink" />
                <p className="font-medium">Waiting for the host to start the match</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
