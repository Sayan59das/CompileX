import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import AppHeader from '../components/AppHeader'
import { DifficultyTag } from '../components/Avatar'
import Icon from '../components/Icons'

const TOPICS = ['Arrays', 'Strings', 'Recursion', 'DP', 'Graphs', 'Trees', 'Sorting', 'Searching', 'Math', 'Greedy']

export const TOURNAMENT_STATUS = {
  registration: { label: 'Open to join', color: 'grass' },
  in_progress: { label: 'In progress', color: 'sun' },
  completed: { label: 'Finished', color: 'ink-3' },
}

export function StatusTag({ status }) {
  const s = TOURNAMENT_STATUS[status] || TOURNAMENT_STATUS.completed
  return (
    <span className="chip">
      <span className="dot" style={{ background: `rgb(var(--${s.color === 'ink-3' ? 'line-strong' : s.color}))` }} />
      {s.label}
    </span>
  )
}

export default function Tournaments() {
  const { user } = useAuth()
  const nav = useNavigate()

  const [tab, setTab] = useState('browse')
  const [tournaments, setTournaments] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Create form
  const [name, setName] = useState('')
  const [maxParticipants, setMaxParticipants] = useState(16)
  const [difficulty, setDifficulty] = useState('medium')
  const [selectedTopics, setSelectedTopics] = useState([])
  const [roundsPerMatch, setRoundsPerMatch] = useState(3)
  const [questionsPerRound, setQuestionsPerRound] = useState(1)
  const [timePerQuestion, setTimePerQuestion] = useState(600)
  const [creating, setCreating] = useState(false)

  // Join code
  const [joinCode, setJoinCode] = useState('')

  useEffect(() => { fetchTournaments() }, [])

  async function fetchTournaments() {
    setLoading(true)
    try {
      const { data } = await api.get('/tournaments')
      setTournaments(data)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  function toggleTopic(t) {
    setSelectedTopics((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))
  }

  async function createTournament(e) {
    e.preventDefault()
    setError('')
    setCreating(true)
    try {
      const { data } = await api.post('/tournaments', {
        name: name || `${user.username}'s Tournament`,
        max_participants: Number(maxParticipants),
        difficulty,
        topics: selectedTopics.length > 0 ? selectedTopics : null,
        rounds_per_match: Number(roundsPerMatch),
        questions_per_round: Number(questionsPerRound),
        time_per_question: Number(timePerQuestion),
      })
      nav(`/tournament/${data.code}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create the tournament.')
    } finally {
      setCreating(false)
    }
  }

  async function joinTournament(code) {
    setError('')
    try {
      await api.post(`/tournaments/${code}/join`)
      nav(`/tournament/${code}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not join that tournament.')
    }
  }

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <h1 className="display text-[clamp(2.4rem,5vw,3.75rem)]">Tournaments</h1>
        <p className="measure mt-3 text-lg text-ink-2">
          Bracket events that knock players out round by round. Each pairing plays its own match.
        </p>

        <div className="tabs mt-8" role="tablist">
          {[
            ['browse', 'Browse'],
            ['create', 'Create a tournament'],
            ['join', 'Join with a code'],
          ].map(([key, label]) => (
            <button key={key} role="tab" aria-selected={tab === key} onClick={() => setTab(key)} className="tab">
              {label}
            </button>
          ))}
        </div>

        {error && (
          <p role="alert" className="mt-6 flex items-start gap-2 text-sm font-medium text-tomato-ink">
            <Icon name="alert" size={16} className="mt-0.5" />
            {error}
          </p>
        )}

        {tab === 'browse' && (
          <section className="mt-6">
            {loading ? (
              <p className="py-12 text-ink-2" role="status">Loading tournaments…</p>
            ) : tournaments.length === 0 ? (
              <div className="py-16">
                <p className="stretch-narrow text-3xl font-extrabold tracking-tight">No tournaments are running</p>
                <p className="measure mt-2 text-ink-2">Start one and send the code to the people you want to play.</p>
                <button onClick={() => setTab('create')} className="btn btn-primary mt-6">Create a tournament</button>
              </div>
            ) : (
              <ul className="panel divide-y divide-line">
                {tournaments.map((t) => (
                  <li key={t.id} className="grid items-center gap-x-6 gap-y-3 px-5 py-4 md:grid-cols-[minmax(0,1fr)_15rem_6rem_9.5rem]">
                    <div className="min-w-0">
                      <div className="truncate text-lg font-bold">{t.name}</div>
                      <div className="mt-0.5 text-sm text-ink-3">
                        Code <span className="font-mono font-medium text-ink-2">{t.code}</span>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusTag status={t.status} />
                      <DifficultyTag level={t.difficulty} />
                    </div>
                    <div className="md:text-right">
                      <span className="numeral text-2xl">{t.participant_count}</span>
                      <span className="text-sm text-ink-3"> of {t.max_participants}</span>
                    </div>
                    <div className="flex gap-2 md:justify-end">
                      {t.status === 'registration' && (
                        <button onClick={() => joinTournament(t.code)} className="btn btn-primary btn-sm">Join</button>
                      )}
                      <button onClick={() => nav(`/tournament/${t.code}`)} className="btn btn-secondary btn-sm">View</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        {tab === 'create' && (
          <form onSubmit={createTournament} className="mt-8 max-w-xl space-y-6">
            <div>
              <label htmlFor="t-name" className="label">Name</label>
              <input id="t-name" className="field" placeholder={`${user?.username}'s Tournament`} value={name} onChange={(e) => setName(e.target.value)} />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="t-max" className="label">Max players</label>
                <input id="t-max" type="number" min="2" max="128" className="field tnum" value={maxParticipants} onChange={(e) => setMaxParticipants(e.target.value)} />
              </div>
              <div>
                <label htmlFor="t-rounds" className="label">Rounds per match</label>
                <input id="t-rounds" type="number" min="1" max="5" className="field tnum" value={roundsPerMatch} onChange={(e) => setRoundsPerMatch(e.target.value)} />
              </div>
              <div>
                <label htmlFor="t-q" className="label">Questions per round</label>
                <input id="t-q" type="number" min="1" max="3" className="field tnum" value={questionsPerRound} onChange={(e) => setQuestionsPerRound(e.target.value)} />
              </div>
              <div>
                <label htmlFor="t-time" className="label">Minutes per question</label>
                <input
                  id="t-time"
                  type="number"
                  min="1"
                  max="60"
                  className="field tnum"
                  value={Math.round(timePerQuestion / 60)}
                  onChange={(e) => setTimePerQuestion(Math.max(1, Number(e.target.value) || 1) * 60)}
                />
              </div>
            </div>

            <fieldset>
              <legend className="label">Difficulty</legend>
              <div className="seg" role="group">
                {['easy', 'medium', 'hard'].map((d) => (
                  <button key={d} type="button" aria-pressed={difficulty === d} onClick={() => setDifficulty(d)} className="capitalize">
                    {d}
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend className="label">Topics <span className="font-normal text-ink-3">leave empty for a mix</span></legend>
              <div className="flex flex-wrap gap-2">
                {TOPICS.map((t) => {
                  const on = selectedTopics.includes(t)
                  return (
                    <button
                      key={t}
                      type="button"
                      aria-pressed={on}
                      onClick={() => toggleTopic(t)}
                      className={`chip h-8 gap-1.5 px-3.5 text-sm transition-colors ${on ? 'border-ink bg-ink text-paper' : 'hover:border-ink hover:text-ink'}`}
                    >
                      {on && <Icon name="check" size={13} strokeWidth={2.6} />}
                      {t}
                    </button>
                  )
                })}
              </div>
            </fieldset>

            <button type="submit" disabled={creating} className="btn btn-primary btn-lg">
              {creating ? 'Creating…' : 'Create tournament'}
            </button>
          </form>
        )}

        {tab === 'join' && (
          <div className="mt-8 max-w-sm space-y-5">
            <div>
              <label htmlFor="t-code" className="label">Tournament code</label>
              <input
                id="t-code"
                className="field numeral h-16 text-center text-4xl uppercase tracking-[0.3em]"
                placeholder="ABC123"
                maxLength={6}
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                autoComplete="off"
              />
            </div>
            <button onClick={() => joinTournament(joinCode)} disabled={!joinCode} className="btn btn-primary btn-lg w-full">
              Join tournament
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
