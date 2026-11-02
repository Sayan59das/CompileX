import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import { ArrowRight, CheckCircle2, Code2, Gauge, History as HistoryIcon, LineChart, Lock, Swords, Trophy } from 'lucide-react'
import AppShell from '../components/AppShell'
import { Panel, Button, Label, Input, Toggle, Tabs, Segmented, Alert, EmptyState, Avatar, Badge } from '../components/ui'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts'

const TOPICS = ['Arrays', 'Strings', 'Trees', 'DP', 'Graphs', 'Sorting', 'Hashing', 'Greedy']


export default function Profile() {
  const { user } = useAuth()
  const nav = useNavigate()

  const [stats, setStats] = useState(null)
  const [progress, setProgress] = useState(null)
  const [achievements, setAchievements] = useState([])
  const [leaderboard, setLeaderboard] = useState([])
  const [loading, setLoading] = useState(true)
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
  const [recent, setRecent] = useState([])

  useEffect(() => {
    Promise.all([fetchStats(), fetchAchievements(), seedAchievements(), fetchLeaderboard(), fetchProgress(), fetchRecent()])
      .finally(() => setLoading(false))
  }, [])

  async function fetchRecent() {
    try { const { data } = await api.get('/users/me/history?limit=5&offset=0'); setRecent(data.matches || []) } catch {}
  }
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
      setError(err.response?.data?.detail || 'Failed to create')
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
      setJoinError(err.response?.data?.detail || 'Lobby not found')
    } finally { setJoining(false) }
  }

  const unlockedCount = achievements.filter(a => a.unlocked).length
  const winRate = stats?.win_rate != null ? Number(stats.win_rate) : 0
  const stats4 = [
    { label: 'Rating', value: stats?.rating ?? user?.rating ?? 1000, icon: Gauge, color: '#3DE0FF' },
    { label: 'Matches played', value: stats?.total_matches ?? 0, icon: Swords, color: '#9B7BFF' },
    { label: 'Win rate', value: `${winRate.toFixed(0)}%`, icon: Trophy, color: '#FFC857', bar: winRate },
    { label: 'Problems solved', value: stats?.questions_solved ?? 0, icon: CheckCircle2, color: '#35F2A0' },
  ]
  const myRank = (leaderboard.findIndex(p => (p.username || p.name) === user?.username) + 1) || 0
  const chartTooltip = { backgroundColor: '#0A0A0A', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, color: '#fff', fontSize: 12 }

  return (
    <AppShell>
      {/* player card */}
      <section className="relative mb-6 overflow-hidden rounded-xl border border-white/10 bg-[#0A0A0A]">
        <div className="pointer-events-none absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(ellipse_at_top_right,rgba(61,224,255,0.10),transparent_60%)]" aria-hidden="true" />
        <div className="relative flex flex-col gap-6 p-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <Avatar name={user?.username} size={56} />
            <div>
              <h1 className="font-display text-[26px] font-bold tracking-tight">{user?.username}</h1>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[14px] text-slate-400">
                <span className="font-mono text-white">{stats?.rating ?? user?.rating ?? 1000}</span> rating
                {myRank > 0 && <Badge tone="accent">#{myRank} on the leaderboard</Badge>}
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-4 md:items-end">
            <div className="flex gap-2.5">
              <Button icon={Code2} onClick={() => nav('/practice')}>Practice</Button>
              <Button variant="secondary" icon={Trophy} onClick={() => nav('/tournaments')}>Tournaments</Button>
            </div>
            {achievements.length > 0 && (
              <div className="w-full md:w-64">
                <div className="mb-1.5 flex justify-between text-[12px] text-slate-400">
                  <span>Achievements</span><span className="font-mono">{unlockedCount}/{achievements.length}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full rounded-full bg-arc transition-[width] duration-700" style={{ width: `${(unlockedCount / achievements.length) * 100}%` }} />
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* numbers that matter */}
      <section className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4" aria-label="Your stats">
        {stats4.map((s) => (
          <div key={s.label} className="rounded-xl border border-white/10 bg-[#0A0A0A] p-4 transition-colors duration-200 hover:border-white/20">
            <div className="flex items-center justify-between">
              <span className="text-[13px] text-slate-400">{s.label}</span>
              <span className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ background: `${s.color}14`, color: s.color }}>
                <s.icon className="h-4 w-4" aria-hidden="true" />
              </span>
            </div>
            <div className="mt-2 font-mono text-[26px] font-semibold tabular-nums text-white">{loading ? '–' : s.value}</div>
            {s.bar != null && (
              <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full" style={{ width: `${Math.min(100, s.bar)}%`, background: s.color }} />
              </div>
            )}
          </div>
        ))}
      </section>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* play */}
        <Panel bodyClassName="">
          <Tabs
            value={tab}
            onChange={setTab}
            tabs={[{ value: 'create', label: 'Create match' }, { value: 'join', label: 'Join match' }, { value: 'progress', label: 'Progress' }]}
          />
          <div className="p-5">
            {tab === 'create' && (
              <form onSubmit={createLobby} className="space-y-5">
                <div>
                  <Label htmlFor="room">Room name</Label>
                  <Input id="room" placeholder={`${user?.username}'s Room`} value={lobbyName} onChange={e => setLobbyName(e.target.value)} />
                </div>
                <div>
                  <Label>Mode</Label>
                  <Segmented
                    value={gameMode}
                    onChange={setGameMode}
                    options={[{ value: 'multiplayer', label: 'Multiplayer', description: 'Up to 20 players' }, { value: '1v1', label: '1v1 duel', description: 'Head to head' }]}
                  />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label htmlFor="players">Players</Label>
                    <Input id="players" type="number" min="2" max="20" value={maxPlayers} onChange={e => setMaxPlayers(e.target.value)} />
                  </div>
                  <div>
                    <Label htmlFor="duration" hint="seconds">Time limit</Label>
                    <Input id="duration" type="number" value={duration} onChange={e => setDuration(e.target.value)} />
                  </div>
                  <div>
                    <Label htmlFor="questions">Questions</Label>
                    <Input id="questions" type="number" min="1" max="50" value={totalQuestions} onChange={e => setTotalQuestions(e.target.value)} />
                  </div>
                </div>
                <Toggle id="public" checked={isPublic} onChange={setIsPublic} label="Public room" description="Anyone with the code can join." />
                {error && <Alert>{error}</Alert>}
                <Button type="submit" size="lg" className="w-full" loading={creating}>Create match</Button>
              </form>
            )}

            {tab === 'join' && (
              <form onSubmit={joinLobby} className="space-y-5">
                <div>
                  <Label htmlFor="code">Room code</Label>
                  <Input
                    id="code"
                    placeholder="e.g. 4KX9QZ"
                    autoComplete="off"
                    className="font-mono uppercase tracking-[0.2em]"
                    value={joinCode}
                    onChange={e => setJoinCode(e.target.value.toUpperCase())}
                  />
                </div>
                {joinError && <Alert>{joinError}</Alert>}
                <Button type="submit" size="lg" className="w-full" loading={joining} disabled={!joinCode.trim()}>Join match</Button>
              </form>
            )}

            {tab === 'progress' && (
              progress && progress.learning_curve?.length > 0 ? (
                <div className="space-y-6">
                  <div>
                    <h3 className="mb-3 text-[14px] font-medium text-slate-300">Problems solved over time</h3>
                    <div className="h-56">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={progress.learning_curve} margin={{ left: -12, right: 8, top: 4 }}>
                          <defs>
                            <linearGradient id="solvedFill" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#3DE0FF" stopOpacity={0.25} />
                              <stop offset="100%" stopColor="#3DE0FF" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                          <XAxis dataKey="date" stroke="#737373" fontSize={11} tickLine={false} axisLine={false} />
                          <YAxis stroke="#737373" fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} width={36} />
                          <RechartsTooltip contentStyle={chartTooltip} />
                          <Area type="monotone" dataKey="solved" stroke="#3DE0FF" strokeWidth={2} fill="url(#solvedFill)" dot={false} activeDot={{ r: 4 }} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                  <div>
                    <h3 className="mb-3 text-[14px] font-medium text-slate-300">Accuracy by topic</h3>
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="72%" data={progress.topic_stats}>
                          <PolarGrid stroke="rgba(255,255,255,0.1)" />
                          <PolarAngleAxis dataKey="topic" tick={{ fill: '#B0B0B0', fontSize: 11 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#737373', fontSize: 10 }} />
                          <Radar name="Accuracy" dataKey="accuracy" stroke="#8B6CFF" strokeWidth={2} fill="#8B6CFF" fillOpacity={0.25} />
                          <RechartsTooltip contentStyle={chartTooltip} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState icon={LineChart} title="No progress yet" action={<Button variant="secondary" onClick={() => nav('/practice')}>Start practising</Button>}>
                  Solve a few practice problems and your progress shows up here.
                </EmptyState>
              )
            )}
          </div>
        </Panel>

        <div className="space-y-6">
          <Panel
            title="Recent matches"
            action={<Link to="/history" className="inline-flex items-center gap-1 text-[13px] text-slate-400 hover:text-white">All<ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>}
            bodyClassName="py-1"
          >
            {recent.length > 0 ? (
              <ul>
                {recent.map((m, i) => {
                  const won = m.player_rank === 1 && m.total_players > 1
                  return (
                    <li key={i} className="flex items-center gap-3 px-5 py-2.5">
                      <span className={`h-2 w-2 shrink-0 rounded-full ${won ? 'bg-emerald-400' : 'bg-slate-600'}`} aria-hidden="true" />
                      <span className="min-w-0 flex-1 truncate text-[14px] text-white">{m.lobby_name}</span>
                      <span className="font-mono text-[12px] tabular-nums text-slate-400">#{m.player_rank}/{m.total_players}</span>
                      <span className="w-12 text-right font-mono text-[13px] tabular-nums text-slate-200">{m.player_score}</span>
                    </li>
                  )
                })}
              </ul>
            ) : (
              <p className="flex items-center gap-2 px-5 py-6 text-[14px] text-slate-400"><HistoryIcon className="h-4 w-4" aria-hidden="true" />No matches played yet.</p>
            )}
          </Panel>

          <Panel title="Top players" action={<span className="text-[12px] text-slate-500">Global</span>} bodyClassName="py-1">
            {leaderboard.length > 0 ? (
              <ol>
                {leaderboard.map((p, i) => (
                  <li key={i} className="flex items-center gap-3 px-5 py-2.5">
                    <span className="w-5 font-mono text-[13px] text-slate-500">{i + 1}</span>
                    <Avatar name={p.username || p.name} size={28} />
                    <span className="min-w-0 flex-1 truncate text-[14px] text-white">{p.username || p.name}</span>
                    <span className="font-mono text-[13px] tabular-nums text-slate-300">{p.score || p.total_score || 0}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="px-5 py-6 text-[14px] text-slate-400">No ranked players yet.</p>
            )}
          </Panel>

          <Panel title="Practice a topic">
            <div className="flex flex-wrap gap-2">
              {TOPICS.map(t => (
                <button
                  key={t}
                  onClick={() => nav('/practice')}
                  className="rounded-md border border-white/15 px-2.5 py-1 text-[13px] text-slate-300 transition-colors duration-150 hover:border-arc/60 hover:text-white"
                >
                  {t}
                </button>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      {achievements.length > 0 && (
        <Panel
          className="mt-6"
          title="Achievements"
          action={<span className="text-[13px] text-slate-400">{unlockedCount} of {achievements.length} unlocked</span>}
          bodyClassName=""
        >
          <ul className="grid sm:grid-cols-2 lg:grid-cols-3">
            {achievements.map(a => (
              <li key={a.id} className={`flex gap-3 border-b border-white/5 px-5 py-4 ${a.unlocked ? '' : 'opacity-55'}`}>
                <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border ${a.unlocked ? 'border-arc/40 text-arc' : 'border-white/10 text-slate-500'}`}>
                  {a.unlocked ? <Trophy className="h-4 w-4" aria-hidden="true" /> : <Lock className="h-4 w-4" aria-hidden="true" />}
                </span>
                <div className="min-w-0">
                  <div className="text-[14px] font-medium text-white">{a.name}</div>
                  <div className="text-[13px] text-slate-400">{a.description}</div>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </AppShell>
  )
}
