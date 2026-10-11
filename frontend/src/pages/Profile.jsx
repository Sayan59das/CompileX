import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import AppHeader from '../components/AppHeader'
import Avatar from '../components/Avatar'
import Icon from '../components/Icons'
import { balloonFill, onBalloon, BALLOON_NAMES } from '../utils/balloons'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts'

const TOPICS = ['Arrays', 'Strings', 'Trees', 'DP', 'Graphs', 'Sorting', 'Hashing', 'Greedy']

const tooltipStyle = {
  background: 'rgb(var(--panel))',
  border: '1px solid rgb(var(--line-strong))',
  borderRadius: 8,
  color: 'rgb(var(--ink))',
  fontSize: 13,
}

function Switch({ checked, onChange, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${checked ? 'bg-ink' : 'bg-line-strong'}`}
    >
      <span
        className={`absolute left-0 top-0.5 h-5 w-5 rounded-full bg-paper transition-transform ${checked ? 'translate-x-[22px]' : 'translate-x-0.5'}`}
      />
    </button>
  )
}

function NumberField({ id, label, hint, ...rest }) {
  return (
    <div>
      <label htmlFor={id} className="label">{label}</label>
      <input id={id} type="number" className="field tnum" {...rest} />
      {hint && <p className="hint">{hint}</p>}
    </div>
  )
}

export default function Profile() {
  const { user } = useAuth()
  const nav = useNavigate()

  const [stats, setStats] = useState(null)
  const [progress, setProgress] = useState(null)
  const [achievements, setAchievements] = useState([])
  const [leaderboard, setLeaderboard] = useState([])
  const [error, setError] = useState('')

  const [lobbyName, setLobbyName] = useState('')
  const [gameMode, setGameMode] = useState('multiplayer')
  const [maxPlayers, setMaxPlayers] = useState(10)
  const [duration, setDuration] = useState(1800)
  const [totalQuestions, setTotalQuestions] = useState(3)
  const [isPublic, setIsPublic] = useState(true)
  const [tab, setTab] = useState('create')
  const [creating, setCreating] = useState(false)
  const [joinCode, setJoinCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [joinError, setJoinError] = useState('')

  useEffect(() => {
    Promise.all([fetchStats(), fetchAchievements(), seedAchievements(), fetchLeaderboard(), fetchProgress()])
  }, [])

  async function fetchProgress() {
    try { const { data } = await api.get('/users/me/progress'); setProgress(data) } catch {}
  }
  async function fetchStats() {
    try { const { data } = await api.get('/users/me/stats'); setStats(data) } catch {}
  }
  async function fetchAchievements() {
    try { const { data } = await api.get('/achievements'); setAchievements(data) } catch {}
  }
  async function seedAchievements() {
    try { await api.post('/achievements/seed') } catch {}
  }
  async function fetchLeaderboard() {
    try {
      const { data } = await api.get('/leaderboard')
      setLeaderboard(data.map((p, i) => ({ ...p, rank: i + 1 })).slice(0, 3))
    } catch { setLeaderboard([]) }
  }

  async function createLobby(e) {
    e.preventDefault()
    setCreating(true); setError('')
    try {
      const { data: lobby } = await api.post('/lobbies', {
        name: lobbyName || `${user.username}'s Room`,
        max_players: Number(maxPlayers),
        time_limit: Number(duration),
        game_mode: gameMode,
        is_public: isPublic,
        match_config: {
          num_rounds: 1,
          questions_per_round: Number(totalQuestions),
          difficulty: 'medium',
          time_per_question: Math.max(30, Math.floor(Number(duration) / Number(totalQuestions))),
        },
      })
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      nav(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create the room.')
    } finally { setCreating(false) }
  }

  async function joinLobby(e) {
    e.preventDefault()
    if (!joinCode.trim()) return
    setJoining(true); setJoinError('')
    try {
      const { data: lobby } = await api.get(`/lobbies/${joinCode.trim().toUpperCase()}`)
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      nav(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setJoinError(err.response?.data?.detail || 'No room found with that code.')
    } finally { setJoining(false) }
  }

  const unlockedCount = achievements.filter((a) => a.unlocked).length

  const scoreline = [
    { label: 'Rating', value: Math.round(stats?.rating ?? user?.rating ?? 1000) },
    { label: 'Matches played', value: stats?.total_matches ?? '—' },
    { label: 'Win rate', value: stats?.win_rate ? `${stats.win_rate.toFixed(0)}%` : '—' },
    { label: 'Questions solved', value: stats?.questions_solved ?? '—' },
  ]

  const spinner = <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />

  return (
    <div className="min-h-screen bg-paper">
      <AppHeader />

      <main className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-ink-3">Welcome back</p>
            <h1 className="display mt-1 text-[clamp(2.4rem,5vw,3.75rem)]">{user?.username}</h1>
          </div>
          <button onClick={() => nav('/practice')} className="btn btn-secondary">
            <Icon name="target" size={18} />
            Open the practice arena
          </button>
        </div>

        <dl className="panel mt-8 grid grid-cols-2 divide-x divide-y divide-line sm:grid-cols-4 sm:divide-y-0">
          {scoreline.map((s) => (
            <div key={s.label} className="px-5 py-5">
              <dd className="numeral text-5xl">{s.value}</dd>
              <dt className="mt-2 text-sm text-ink-3">{s.label}</dt>
            </div>
          ))}
        </dl>

        <div className="mt-8 grid items-start gap-8 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
          {/* Start a match */}
          <section className="panel">
            <div className="tabs px-3" role="tablist" aria-label="Match options">
              {[
                ['create', 'Create a room'],
                ['join', 'Join with a code'],
                ['progress', 'Your progress'],
              ].map(([key, label]) => (
                <button
                  key={key}
                  role="tab"
                  aria-selected={tab === key}
                  onClick={() => setTab(key)}
                  className="tab"
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="p-6 sm:p-8">
              {tab === 'create' && (
                <form onSubmit={createLobby} className="space-y-6">
                  <div>
                    <label htmlFor="room-name" className="label">Room name</label>
                    <input
                      id="room-name"
                      className="field"
                      placeholder={`${user?.username}'s room`}
                      value={lobbyName}
                      onChange={(e) => setLobbyName(e.target.value)}
                    />
                  </div>

                  <fieldset>
                    <legend className="label">Format</legend>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {[
                        { v: 'multiplayer', label: 'Arena match', sub: 'Up to 20 players in one room', icon: 'users' },
                        { v: '1v1', label: '1v1 duel', sub: 'Two players, head to head', icon: 'duel' },
                      ].map((m) => (
                        <button
                          key={m.v}
                          type="button"
                          aria-pressed={gameMode === m.v}
                          onClick={() => setGameMode(m.v)}
                          className={`flex items-start gap-3 rounded-md border p-4 text-left transition-colors ${
                            gameMode === m.v ? 'border-ink bg-panel ring-1 ring-ink' : 'border-line-strong bg-panel hover:border-ink-3'
                          }`}
                        >
                          <Icon name={m.icon} size={20} className="mt-0.5" />
                          <span>
                            <span className="block font-semibold">{m.label}</span>
                            <span className="block text-sm text-ink-3">{m.sub}</span>
                          </span>
                        </button>
                      ))}
                    </div>
                  </fieldset>

                  <div className="grid gap-4 sm:grid-cols-3">
                    <NumberField id="players" label="Max players" min="2" max="20" value={maxPlayers} onChange={(e) => setMaxPlayers(e.target.value)} />
                    <NumberField
                      id="minutes"
                      label="Time limit (minutes)"
                      min="1"
                      value={Math.round(duration / 60)}
                      onChange={(e) => setDuration(Math.max(1, Number(e.target.value) || 1) * 60)}
                    />
                    <NumberField id="questions" label="Questions" min="1" max="50" value={totalQuestions} onChange={(e) => setTotalQuestions(e.target.value)} />
                  </div>

                  <div className="flex items-center justify-between gap-4 rounded-md border border-line bg-sunken px-4 py-3.5">
                    <div>
                      <div className="font-semibold">Public room</div>
                      <div className="text-sm text-ink-3">Anyone who has the code can join.</div>
                    </div>
                    <Switch checked={isPublic} onChange={setIsPublic} label="Public room" />
                  </div>

                  {error && (
                    <p role="alert" className="flex items-start gap-2 text-sm font-medium text-tomato-ink">
                      <Icon name="alert" size={16} className="mt-0.5" />
                      {error}
                    </p>
                  )}

                  <button type="submit" disabled={creating} className="btn btn-primary btn-lg w-full">
                    {creating ? <>{spinner} Creating room…</> : 'Create room'}
                  </button>
                </form>
              )}

              {tab === 'join' && (
                <form onSubmit={joinLobby} className="mx-auto max-w-sm space-y-5 py-4">
                  <div>
                    <label htmlFor="join-code" className="label">Room code</label>
                    <input
                      id="join-code"
                      className="field numeral h-16 text-center text-4xl uppercase tracking-[0.3em]"
                      placeholder="ABC123"
                      value={joinCode}
                      onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                      maxLength={6}
                      autoFocus
                      autoComplete="off"
                    />
                    <p className="hint">The host can see the code at the top of the waiting room.</p>
                  </div>
                  {joinError && (
                    <p role="alert" className="flex items-start gap-2 text-sm font-medium text-tomato-ink">
                      <Icon name="alert" size={16} className="mt-0.5" />
                      {joinError}
                    </p>
                  )}
                  <button type="submit" disabled={joining || !joinCode.trim()} className="btn btn-primary btn-lg w-full">
                    {joining ? <>{spinner} Joining…</> : 'Join room'}
                  </button>
                </form>
              )}

              {tab === 'progress' &&
                (progress && progress.learning_curve?.length > 0 ? (
                  <div className="space-y-8">
                    <div>
                      <h3 className="font-semibold">Questions solved over time</h3>
                      <div className="mt-4 h-60">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={progress.learning_curve}>
                            <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
                            <XAxis dataKey="date" stroke="rgb(var(--ink-3))" fontSize={12} tickMargin={8} tickLine={false} axisLine={false} />
                            <YAxis stroke="rgb(var(--ink-3))" fontSize={12} allowDecimals={false} width={28} tickLine={false} axisLine={false} />
                            <RechartsTooltip contentStyle={tooltipStyle} cursor={{ stroke: 'rgb(var(--line-strong))' }} />
                            <Area isAnimationActive={false} type="monotone" dataKey="solved" stroke="rgb(var(--ink))" strokeWidth={2} fill="rgb(var(--sky))" fillOpacity={0.18} dot={{ r: 3, fill: 'rgb(var(--ink))', strokeWidth: 0 }} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                    <div>
                      <h3 className="font-semibold">Accuracy by topic</h3>
                      <div className="mt-2 h-72">
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart cx="50%" cy="50%" outerRadius="72%" data={progress.topic_stats}>
                            <PolarGrid stroke="rgb(var(--line-strong))" />
                            <PolarAngleAxis dataKey="topic" tick={{ fill: 'rgb(var(--ink-2))', fontSize: 12 }} />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'rgb(var(--ink-3))', fontSize: 10 }} axisLine={false} />
                            <Radar isAnimationActive={false} name="Accuracy" dataKey="accuracy" stroke="rgb(var(--grass-ink))" strokeWidth={2} fill="rgb(var(--grass))" fillOpacity={0.3} />
                            <RechartsTooltip contentStyle={tooltipStyle} />
                          </RadarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="py-14 text-center">
                    <p className="font-semibold">No progress to chart yet</p>
                    <p className="mx-auto mt-1.5 max-w-sm text-ink-2">
                      Solve a few questions in the practice arena and your learning curve will show up here.
                    </p>
                    <button onClick={() => nav('/practice')} className="btn btn-secondary mt-6">Go to the practice arena</button>
                  </div>
                ))}
            </div>
          </section>

          {/* Side column */}
          <div className="space-y-8">
            <section className="panel">
              <div className="flex items-center justify-between border-b border-line px-5 py-4">
                <h2 className="font-bold">Top players</h2>
                <span className="text-sm text-ink-3">All time</span>
              </div>
              {leaderboard.length > 0 ? (
                <ol>
                  {leaderboard.map((p) => (
                    <li key={p.rank} className="flex items-center gap-3 border-b border-line px-5 py-3.5 last:border-b-0">
                      <span className={`numeral w-6 text-2xl ${p.rank === 1 ? 'text-sun-ink' : 'text-ink-3'}`}>{p.rank}</span>
                      <Avatar name={p.username || p.name || '?'} size={32} />
                      <span className="flex-1 truncate font-semibold">{p.username || p.name}</span>
                      <span className="numeral text-xl">{p.score || p.total_score || 0}</span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="px-5 py-8 text-sm text-ink-2">No ranked players yet. Finish a match and you will be first.</p>
              )}
            </section>

            <section className="panel">
              <div className="border-b border-line px-5 py-4">
                <h2 className="font-bold">Practice a topic</h2>
              </div>
              <div className="flex flex-wrap gap-2 p-5">
                {TOPICS.map((t) => (
                  <button
                    key={t}
                    onClick={() => nav('/practice')}
                    className="chip h-8 px-3.5 text-sm transition-colors hover:border-ink hover:text-ink"
                  >
                    {t}
                  </button>
                ))}
              </div>
            </section>
          </div>
        </div>

        {achievements.length > 0 && (
          <section className="mt-12">
            <div className="flex items-baseline justify-between border-b border-line pb-3">
              <h2 className="stretch-narrow text-3xl font-extrabold tracking-tight">Achievements</h2>
              <span className="text-sm text-ink-3">{unlockedCount} of {achievements.length} unlocked</span>
            </div>
            <ul className="grid gap-x-10 lg:grid-cols-2">
              {achievements.map((a, i) => {
                const color = BALLOON_NAMES[i % BALLOON_NAMES.length]
                return (
                  <li key={a.id} className={`flex items-start gap-4 border-b border-line py-4 ${a.unlocked ? '' : 'opacity-60'}`}>
                    <span
                      className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                      style={a.unlocked ? { background: balloonFill(color), color: onBalloon(color) } : { background: 'rgb(var(--sunken))', color: 'rgb(var(--ink-3))' }}
                    >
                      <Icon name={a.unlocked ? 'check' : 'lock'} size={16} strokeWidth={2.4} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold">{a.name}</div>
                      <div className="text-sm text-ink-2">{a.description}</div>
                    </div>
                    <span className={`text-sm font-medium ${a.unlocked ? 'text-grass-ink' : 'text-ink-3'}`}>
                      {a.unlocked ? 'Unlocked' : 'Locked'}
                    </span>
                  </li>
                )
              })}
            </ul>
          </section>
        )}
      </main>
    </div>
  )
}
