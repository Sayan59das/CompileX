import React, { useState, useEffect } from 'react'
import { Hourglass, Plus, Swords, Trophy as TrophyIcon, UserPlus } from 'lucide-react'
import AppShell from '../components/AppShell'
import { PageHeader, Panel, Button, Label, Input, Tabs, Segmented, Badge, Alert, EmptyState, Spinner } from '../components/ui'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const TOPICS = ['Arrays', 'Strings', 'Recursion', 'DP', 'Graphs', 'Trees', 'Sorting', 'Searching', 'Math', 'Greedy']

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
    setSelectedTopics(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t])
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
      setError(err.response?.data?.detail || 'Failed to create tournament')
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
      setError(err.response?.data?.detail || 'Failed to join')
    }
  }

  const STATUS = {
    registration: { tone: 'success', label: 'Open' },
    in_progress: { tone: 'warning', label: 'In progress' },
    completed: { tone: 'neutral', label: 'Finished' },
  }
  const DIFF = { easy: 'success', medium: 'warning', hard: 'danger' }
  const counts = {
    registration: tournaments.filter(t => t.status === 'registration').length,
    in_progress: tournaments.filter(t => t.status === 'in_progress').length,
    completed: tournaments.filter(t => t.status === 'completed').length,
  }
  const STEPS = [
    { icon: UserPlus, title: 'Register', text: 'Join an open tournament, or create one and share its code.' },
    { icon: Swords, title: 'Play your match', text: 'When the host starts it, you are drawn against another player in a lobby.' },
    { icon: TrophyIcon, title: 'Advance', text: 'Win to move up the bracket. The last player standing takes the tournament.' },
  ]

  return (
    <AppShell>
      <PageHeader
        title="Tournaments"
        description="Bracket elimination. Win your match to move on."
        actions={tab !== 'create' && <Button icon={Plus} onClick={() => setTab('create')}>New tournament</Button>}
      />

      <section className="mb-6 grid grid-cols-3 gap-4" aria-label="Tournament summary">
        {[['Open for registration', counts.registration, '#35F2A0'], ['In progress', counts.in_progress, '#FFC857'], ['Finished', counts.completed, '#8C8C8C']].map(([k, v, c]) => (
          <div key={k} className="rounded-xl border border-white/10 bg-[#0A0A0A] px-5 py-4">
            <div className="flex items-center gap-2 text-[13px] text-slate-400">
              <span className="h-2 w-2 rounded-full" style={{ background: c }} aria-hidden="true" />{k}
            </div>
            <div className="mt-1 font-mono text-[24px] font-semibold tabular-nums">{loading ? '–' : v}</div>
          </div>
        ))}
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
      <Panel bodyClassName="">
        <Tabs
          value={tab}
          onChange={(v) => { setTab(v); setError('') }}
          tabs={[{ value: 'browse', label: 'Browse' }, { value: 'create', label: 'Create' }, { value: 'join', label: 'Join by code' }]}
        />

        {error && <div className="px-5 pt-5"><Alert>{error}</Alert></div>}

        {tab === 'browse' && (
          loading ? <Spinner label="Loading tournaments" /> : tournaments.length === 0 ? (
            <EmptyState icon={TrophyIcon} title="No tournaments yet" action={<Button variant="secondary" onClick={() => setTab('create')}>Create the first one</Button>}>
              Start one and share its code with other players.
            </EmptyState>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[14px]">
                <thead>
                  <tr className="border-b border-white/10 text-[12px] text-slate-500">
                    <th className="px-5 py-2.5 font-medium">Name</th>
                    <th className="px-3 py-2.5 font-medium">Status</th>
                    <th className="px-3 py-2.5 font-medium">Difficulty</th>
                    <th className="px-3 py-2.5 font-medium">Players</th>
                    <th className="px-3 py-2.5 font-medium">Code</th>
                    <th className="px-5 py-2.5" aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {tournaments.map(t => (
                    <tr key={t.id} className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 text-slate-400"><TrophyIcon className="h-4 w-4" aria-hidden="true" /></span>
                          <span className="font-medium text-white">{t.name}</span>
                        </div>
                      </td>
                      <td className="px-3 py-3"><Badge tone={STATUS[t.status]?.tone}>{STATUS[t.status]?.label || t.status}</Badge></td>
                      <td className="px-3 py-3"><Badge tone={DIFF[t.difficulty]}>{t.difficulty}</Badge></td>
                      <td className="px-3 py-3">
                        <div className="font-mono text-[13px] tabular-nums text-slate-300">{t.participant_count}/{t.max_participants}</div>
                        <div className="mt-1 h-1 w-20 overflow-hidden rounded-full bg-white/10">
                          <div className="h-full rounded-full bg-arc" style={{ width: `${Math.min(100, (t.participant_count / Math.max(1, t.max_participants)) * 100)}%` }} />
                        </div>
                      </td>
                      <td className="px-3 py-3 font-mono text-slate-300">{t.code}</td>
                      <td className="px-5 py-3">
                        <div className="flex justify-end gap-2">
                          {t.status === 'registration' && <Button size="sm" onClick={() => joinTournament(t.code)}>Join</Button>}
                          <Button size="sm" variant="secondary" onClick={() => nav(`/tournament/${t.code}`)}>View</Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {tab === 'create' && (
          <form onSubmit={createTournament} className="max-w-xl space-y-5 p-5">
            <div>
              <Label htmlFor="t-name">Name</Label>
              <Input id="t-name" placeholder={`${user?.username}'s Tournament`} value={name} onChange={e => setName(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <Label htmlFor="t-max">Players</Label>
                <Input id="t-max" type="number" min="2" max="128" value={maxParticipants} onChange={e => setMaxParticipants(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="t-rounds">Rounds</Label>
                <Input id="t-rounds" type="number" min="1" max="5" value={roundsPerMatch} onChange={e => setRoundsPerMatch(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="t-q">Questions</Label>
                <Input id="t-q" type="number" min="1" max="3" value={questionsPerRound} onChange={e => setQuestionsPerRound(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="t-time" hint="sec">Per question</Label>
                <Input id="t-time" type="number" min="60" max="3600" value={timePerQuestion} onChange={e => setTimePerQuestion(e.target.value)} />
              </div>
            </div>
            <div>
              <Label>Difficulty</Label>
              <Segmented
                value={difficulty}
                onChange={setDifficulty}
                options={[{ value: 'easy', label: 'Easy' }, { value: 'medium', label: 'Medium' }, { value: 'hard', label: 'Hard' }]}
              />
            </div>
            <div>
              <Label hint={selectedTopics.length ? `${selectedTopics.length} selected` : 'all topics'}>Topics</Label>
              <div className="flex flex-wrap gap-2">
                {TOPICS.map(t => {
                  const on = selectedTopics.includes(t)
                  return (
                    <button
                      key={t}
                      type="button"
                      aria-pressed={on}
                      onClick={() => toggleTopic(t)}
                      className={`rounded-md border px-2.5 py-1 text-[13px] transition-colors duration-150 ${on ? 'border-arc bg-arc/10 text-white' : 'border-white/15 text-slate-300 hover:border-white/30'}`}
                    >
                      {t}
                    </button>
                  )
                })}
              </div>
            </div>
            <Button type="submit" size="lg" loading={creating}>Create tournament</Button>
          </form>
        )}

        {tab === 'join' && (
          <form onSubmit={(e) => { e.preventDefault(); if (joinCode) joinTournament(joinCode) }} className="max-w-md space-y-5 p-5">
            <div>
              <Label htmlFor="t-code">Tournament code</Label>
              <Input id="t-code" placeholder="e.g. C42739" autoComplete="off" className="font-mono uppercase tracking-[0.2em]"
                value={joinCode} onChange={e => setJoinCode(e.target.value.toUpperCase())} />
            </div>
            <Button type="submit" size="lg" disabled={!joinCode}>Join tournament</Button>
          </form>
        )}
      </Panel>

      <Panel title="How tournaments work" bodyClassName="p-5">
        <ol className="space-y-5">
          {STEPS.map((st, i) => (
            <li key={st.title} className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 text-arc">
                <st.icon className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <div className="text-[14px] font-medium text-white">{i + 1}. {st.title}</div>
                <p className="mt-0.5 text-[13px] leading-relaxed text-slate-400">{st.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="mt-5 flex items-center gap-2 border-t border-white/10 pt-4 text-[13px] text-slate-400">
          <Hourglass className="h-4 w-4" aria-hidden="true" />A host needs at least 2 players to start.
        </div>
      </Panel>
      </div>
    </AppShell>
  )
}
