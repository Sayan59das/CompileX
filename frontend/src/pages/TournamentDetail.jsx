import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import AppHeader from '../components/AppHeader'
import Avatar, { DifficultyTag } from '../components/Avatar'
import Icon from '../components/Icons'
import { StatusTag } from './Tournaments'

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

  // Poll for the match lobby once the tournament is in progress.
  useEffect(() => {
    if (!tournament || tournament.status !== 'in_progress') return
    const isParticipant = tournament.participants?.some((p) => p.user_id === user?.id)
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
          } catch (e) { console.error(e) }
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
      await fetchTournament() // refresh to trigger the polling effect
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not start the tournament.')
    } finally {
      setStarting(false)
    }
  }

  async function joinTournament() {
    try {
      await api.post(`/tournaments/${code}/join`)
      fetchTournament()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not join the tournament.')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-paper">
        <AppHeader />
        <p className="mx-auto max-w-6xl px-5 py-16 text-ink-2 sm:px-8" role="status">Loading tournament…</p>
      </div>
    )
  }

  if (error && !tournament) {
    return (
      <div className="min-h-screen bg-paper">
        <AppHeader />
        <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
          <p className="stretch-narrow text-3xl font-extrabold tracking-tight">{error}</p>
          <button onClick={() => nav('/tournaments')} className="btn btn-primary mt-6">Back to tournaments</button>
        </div>
      </div>
    )
  }

  const t = tournament
  const isParticipant = t?.participants?.some((p) => p.user_id === user?.id)
  const isCreator = t?.created_by === user?.id
  const enoughPlayers = (t?.participants?.length ?? t?.participant_count) >= 2

  const facts = [
    ['Current round', `Round ${t.current_bracket_round}`],
    ['Players', `${t.participant_count} of ${t.max_participants}`],
    ['Bracket rounds', Math.ceil(Math.log2(t.max_participants))],
  ]

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <Link to="/tournaments" className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-2 hover:text-ink">
          <Icon name="arrow-left" size={14} />
          All tournaments
        </Link>

        {error && (
          <p role="alert" className="mt-4 flex items-start gap-2 text-sm font-medium text-tomato-ink">
            <Icon name="alert" size={16} className="mt-0.5" />
            {error}
          </p>
        )}

        {matchLobbyCode && (
          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-lg border border-grass-ink/50 bg-grass/10 p-5">
            <div>
              <div className="text-lg font-bold">Your match is ready</div>
              <div className="text-sm text-ink-2">
                Room <span className="font-mono font-medium text-ink">{matchLobbyCode}</span>
              </div>
            </div>
            <button
              onClick={() => (matchLobbyData ? nav(`/lobby/${matchLobbyCode}`, { state: matchLobbyData }) : null)}
              disabled={!matchLobbyData}
              className="btn btn-good"
            >
              Go to the match
            </button>
          </div>
        )}

        {!matchLobbyCode && polling && (
          <div className="panel-sunken mt-6 flex items-center gap-3 px-5 py-4" role="status">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-ink" />
            <span className="font-medium">The tournament has started. Waiting for your match to be assigned.</span>
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-start justify-between gap-6">
          <div>
            <h1 className="display text-[clamp(2.2rem,4.8vw,3.5rem)]">{t.name}</h1>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <StatusTag status={t.status} />
              <DifficultyTag level={t.difficulty} />
              <span className="chip">
                Code <span className="ml-1 font-mono font-semibold text-ink">{t.code}</span>
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {t.status === 'registration' && !isParticipant && (
              <button onClick={joinTournament} className="btn btn-primary btn-lg">Join tournament</button>
            )}
            {isParticipant && (
              <span className="chip h-10 px-4 text-sm font-semibold text-grass-ink">
                <Icon name="check" size={14} strokeWidth={2.6} />
                You are registered
              </span>
            )}
            {isCreator && t.status === 'registration' && (
              <div>
                <button onClick={startTournament} disabled={starting || !enoughPlayers} className="btn btn-primary btn-lg">
                  <Icon name="play" size={14} />
                  {starting ? 'Starting…' : 'Start the tournament'}
                </button>
                {!enoughPlayers && <p className="mt-2 text-sm text-ink-3">At least 2 players are needed to start.</p>}
              </div>
            )}
          </div>
        </div>

        <dl className="panel mt-8 grid grid-cols-1 divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          {facts.map(([k, v]) => (
            <div key={k} className="px-6 py-5">
              <dd className="numeral text-4xl">{v}</dd>
              <dt className="mt-2 text-sm text-ink-3">{k}</dt>
            </div>
          ))}
        </dl>

        <section className="mt-10">
          <h2 className="stretch-narrow border-b border-line pb-3 text-3xl font-extrabold tracking-tight">Players</h2>
          {t.participants?.length === 0 ? (
            <p className="py-8 text-ink-2">Nobody has joined yet.</p>
          ) : (
            <ul className="grid gap-x-10 md:grid-cols-2">
              {t.participants?.map((p) => (
                <li
                  key={p.user_id}
                  className={`flex items-center gap-3 border-b border-line py-3.5 ${p.eliminated ? 'opacity-50' : ''} ${p.user_id === user?.id ? 'bg-sun/15 px-3' : ''}`}
                >
                  <span className="numeral w-9 text-xl text-ink-3">#{p.seed}</span>
                  <Avatar name={p.username} size={32} />
                  <span className={`flex-1 truncate font-semibold ${p.eliminated ? 'line-through' : ''}`}>{p.username}</span>
                  {p.eliminated && <span className="text-sm text-ink-3">Eliminated</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
