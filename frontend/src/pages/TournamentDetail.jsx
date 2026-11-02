import React, { useState, useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Loader2, Play, Trophy as TrophyIcon, Users } from 'lucide-react'
import AppShell from '../components/AppShell'
import { PageHeader, Panel, Button, Badge, Alert, EmptyState, Spinner, Avatar } from '../components/ui'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'


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
    return <AppShell><Spinner label="Loading tournament" /></AppShell>
  }

  if (error && !tournament) {
    return (
      <AppShell>
        <EmptyState icon={TrophyIcon} title="Tournament not found" action={<Button variant="secondary" onClick={() => nav('/tournaments')}>Back to tournaments</Button>}>
          {error}
        </EmptyState>
      </AppShell>
    )
  }

  const t = tournament
  const isParticipant = t?.participants?.some(p => p.user_id === user?.id)
  const isCreator = t?.created_by === user?.id
  const count = t.participants?.length ?? t.participant_count
  const STATUS = {
    registration: { tone: 'success', label: 'Open for registration' },
    in_progress: { tone: 'warning', label: 'In progress' },
    completed: { tone: 'neutral', label: 'Finished' },
  }
  const DIFF = { easy: 'success', medium: 'warning', hard: 'danger' }
  const facts = [
    ['Players', `${t.participant_count} / ${t.max_participants}`],
    ['Current stage', `Round ${t.current_bracket_round}`],
    ['Bracket rounds', Math.ceil(Math.log2(t.max_participants))],
    ['Code', t.code],
  ]

  return (
    <AppShell>
      <Link to="/tournaments" className="mb-4 inline-flex items-center gap-1.5 text-[14px] text-slate-400 transition-colors hover:text-white">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />Tournaments
      </Link>

      <PageHeader
        title={t.name}
        description={<span className="flex flex-wrap items-center gap-2">
          <Badge tone={STATUS[t.status]?.tone}>{STATUS[t.status]?.label || t.status}</Badge>
          <Badge tone={DIFF[t.difficulty]}>{t.difficulty}</Badge>
        </span>}
        actions={<>
          {t.status === 'registration' && !isParticipant && <Button variant="success" onClick={joinTournament}>Join tournament</Button>}
          {isCreator && t.status === 'registration' && (
            <Button icon={Play} onClick={startTournament} loading={starting} disabled={count < 2} title={count < 2 ? 'Needs at least 2 players' : undefined}>
              Start tournament
            </Button>
          )}
        </>}
      />

      {error && <div className="mb-6"><Alert>{error}</Alert></div>}

      {matchLobbyCode && (
        <div className="mb-6 flex flex-col gap-3 rounded-xl border border-emerald-500/40 bg-emerald-500/[0.06] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-[15px] font-semibold text-emerald-300">Your match is ready</div>
            <div className="text-[13px] text-slate-400">Lobby <span className="font-mono text-slate-200">{matchLobbyCode}</span></div>
          </div>
          <Button variant="success" icon={ArrowRight} disabled={!matchLobbyData}
            onClick={() => matchLobbyData && nav(`/lobby/${matchLobbyCode}`, { state: matchLobbyData })}>
            Go to match
          </Button>
        </div>
      )}

      {!matchLobbyCode && polling && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-white/10 bg-[#0A0A0A] px-5 py-4 text-[14px] text-slate-300" role="status">
          <Loader2 className="h-4 w-4 animate-spin text-arc" aria-hidden="true" />
          The tournament has started. Waiting for your match to be assigned.
        </div>
      )}

      <section className="mb-6 grid grid-cols-2 overflow-hidden rounded-xl border border-white/10 bg-[#0A0A0A] md:grid-cols-4" aria-label="Tournament facts">
        {facts.map(([k, v], i) => (
          <div key={k} className={`px-5 py-4 ${i % 2 ? 'border-l border-white/10' : ''} ${i > 1 ? 'border-t border-white/10 md:border-t-0' : ''} ${i === 2 ? 'md:border-l' : ''}`}>
            <div className="text-[13px] text-slate-400">{k}</div>
            <div className="mt-1 font-mono text-[20px] font-semibold tabular-nums text-white">{v}</div>
          </div>
        ))}
      </section>

      <Panel
        title="Participants"
        action={isParticipant && <Badge tone="success">You are registered</Badge>}
        bodyClassName=""
      >
        {!t.participants?.length ? (
          <EmptyState icon={Users} title="No participants yet">Share the code {t.code} with other players.</EmptyState>
        ) : (
          <ul className="grid sm:grid-cols-2 lg:grid-cols-3">
            {t.participants.map(p => (
              <li key={p.user_id} className={`flex items-center gap-3 border-b border-white/5 px-5 py-3 ${p.eliminated ? 'opacity-50' : ''}`}>
                <span className="w-7 font-mono text-[12px] text-slate-500">#{p.seed}</span>
                <Avatar name={p.username} size={28} />
                <span className="min-w-0 flex-1 truncate text-[14px] text-white">
                  {p.username}{p.user_id === user?.id && <span className="ml-1.5 text-slate-500">(you)</span>}
                </span>
                {p.eliminated && <Badge tone="danger">Out</Badge>}
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </AppShell>
  )
}
