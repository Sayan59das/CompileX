import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import Logo from '../components/Logo'
import AnimatedBackgroundCSS from '../components/AnimatedBackgroundCSS'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts'

const TOPICS = ['Arrays', 'Strings', 'Trees', 'DP', 'Graphs', 'Sorting', 'Hashing', 'Greedy']

const RANK_COLORS = ['#f59e0b', '#94a3b8', '#cd7f32']
const RANK_LABELS = ['1st', '2nd', '3rd']

export default function Profile() {
  const { user, logout } = useAuth()
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

  useEffect(() => {
    Promise.all([fetchStats(), fetchAchievements(), seedAchievements(), fetchLeaderboard(), fetchProgress()])
      .finally(() => setLoading(false))
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

  const statCards = [
    { label: 'Matches', value: stats?.total_matches ?? '—', icon: '🎮', color: '#6366f1' },
    { label: 'Win Rate', value: stats?.win_rate ? `${stats.win_rate.toFixed(0)}%` : '—', icon: '📈', color: '#10b981' },
    { label: 'Solved', value: stats?.questions_solved ?? '—', icon: '✅', color: '#22d3ee' },
    { label: 'Rating', value: stats?.rating ?? 1000, icon: '⭐', color: '#f59e0b' },
  ]

  return (
    <div className="min-h-screen relative overflow-hidden flex flex-col">
      <AnimatedBackgroundCSS />

      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A10]/80 backdrop-blur-xl border-b border-white/[0.07]">
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 sm:gap-3 group cursor-pointer" onClick={() => nav('/')}>
            <Logo size={32} className="sm:w-10 sm:h-10 transition-all duration-300 " />
            <span className="text-base sm:text-xl font-bold text-white">CompileX</span>
          </div>
          
          <div className="hidden md:flex items-center gap-2">
            <button onClick={() => nav('/tournaments')} className="text-xs sm:text-sm text-slate-400 hover:text-white transition-colors px-2 sm:px-3 py-2">Tournaments</button>
            <button onClick={() => nav('/history')} className="text-xs sm:text-sm text-slate-400 hover:text-white transition-colors px-2 sm:px-3 py-2">History</button>
          </div>
          
          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center gap-2 px-2 sm:px-4 py-1.5 sm:py-2 bg-[#101018] rounded-lg sm:rounded-xl border border-white/[0.07]">
              <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm font-bold text-white bg-gradient-to-br from-blue-600 to-cyan-600 flex-shrink-0">
                {user?.username?.charAt(0).toUpperCase()}
              </div>
              <span className="hidden sm:inline text-sm text-white font-medium truncate max-w-[100px]">{user?.username}</span>
            </div>
            <button onClick={logout} className="text-xs sm:text-sm text-slate-400 hover:text-white transition-colors whitespace-nowrap">Sign out</button>
          </div>
        </div>
      </nav>

      <div className="flex-1 w-full max-w-[95rem] mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-12 flex flex-col gap-8">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row items-center justify-center sm:justify-between gap-6 text-center sm:text-left bg-[#0A0A10]/60 border border-white/[0.05] p-6 sm:p-8 rounded-3xl backdrop-blur-xl shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-transparent pointer-events-none" />
          <div className="relative z-10 w-full sm:w-auto">
            <p className="text-sm font-bold uppercase tracking-[0.2em] mb-2 text-blue-400">Dashboard</p>
            <h1 className="text-3xl sm:text-5xl font-black text-white">
              Hey, <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]">{user?.username}</span> 👋
            </h1>
          </div>
          <button onClick={() => nav('/practice')} className="relative z-10 px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-bold rounded-2xl transition-all duration-300 shadow-[0_0_30px_rgba(59,130,246,0.4)] whitespace-nowrap text-lg group">
            Practice Arena 
            <span className="inline-block transition-transform duration-300 ml-2">→</span>
          </button>
        </div>

        {/* Bento Grid Layout */}
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6 xl:gap-8 items-start">
          
          {/* Column 1: Stats Stack (Col-Span 3) */}
          <div className="lg:col-span-3 flex flex-col gap-4 sm:gap-6">
            {statCards.map((s, i) => (
              <div key={i} className="relative group " style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600/30 to-cyan-600/30 rounded-3xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative bg-[#0A0A10]/80 backdrop-blur-xl border border-white/[0.07] rounded-3xl p-6 transition-all duration-300 flex items-center justify-between shadow-xl">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-3xl filter drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">{s.icon}</span>
                      <span className="text-sm font-bold tracking-wide uppercase" style={{ color: s.color }}>{s.label}</span>
                    </div>
                    <div className="text-4xl font-black text-white ml-1">{s.value}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Column 2: Match Panel (Col-Span 6) */}
          <div className="lg:col-span-6 h-full flex flex-col" style={{ animationDelay: '0.2s' }}>
            <div className="relative group w-full h-full flex flex-col">
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-3xl blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="relative bg-[#0A0A10]/90 backdrop-blur-xl border border-white/[0.1] rounded-3xl overflow-hidden shadow-2xl h-full flex flex-col">
                
                {/* Tabs */}
                <div className="flex border-b border-white/[0.07] bg-white/[0.02]">
                  {['create', 'join', 'progress'].map(t => (
                    <button key={t} onClick={() => setTab(t)}
                      className={`flex-1 py-5 text-sm sm:text-base font-bold capitalize transition-all duration-300 ${
 tab === t ? 'text-white border-b-2 border-blue-500 bg-blue-500/10 shadow-[inset_0_-2px_10px_rgba(59,130,246,0.2)]' : 'text-slate-400 hover:text-white hover:bg-white/[0.05]'
                      }`}>
                      {t === 'create' ? 'Create Match' : t === 'join' ? 'Join Match' : 'Learning Progress'}
                    </button>
                  ))}
                </div>

                {/* Forms */}
                <div className="p-6 sm:p-8 flex-1 flex flex-col min-h-[400px] overflow-y-auto">
                  {tab === 'progress' ? (
                    <div className="flex flex-col gap-6 h-full w-full">
                      {progress && progress.learning_curve?.length > 0 ? (
                        <>
                          <div className="w-full h-64 bg-[#101018]/80 p-4 rounded-2xl border border-white/[0.07] flex flex-col">
                            <h4 className="text-xs font-bold uppercase tracking-wider mb-4 text-slate-400 text-center">Learning Curve (Questions Solved)</h4>
                            <div className="flex-1 min-h-[200px]">
                              <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={progress.learning_curve}>
                                  <defs>
                                    <linearGradient id="colorSolved" x1="0" y1="0" x2="0" y2="1">
                                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.5}/>
                                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                                    </linearGradient>
                                  </defs>
                                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickMargin={10} />
                                  <YAxis stroke="#94a3b8" fontSize={10} allowDecimals={false} width={30} />
                                  <RechartsTooltip contentStyle={{ backgroundColor: '#060a12', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', boxShadow: '0 4px 15px rgba(0,0,0,0.5)' }} itemStyle={{ color: '#fff', fontWeight: 'bold' }} />
                                  <Area type="monotone" dataKey="solved" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorSolved)" dot={{ fill: '#3b82f6', r: 4 }} activeDot={{ r: 6 }} />
                                </AreaChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                          
                          <div className="w-full h-72 bg-[#101018]/80 p-4 rounded-2xl border border-white/[0.07] flex flex-col">
                            <h4 className="text-xs font-bold uppercase tracking-wider mb-2 text-slate-400 text-center">Topic Strengths (Accuracy %)</h4>
                            <div className="flex-1 min-h-[200px]">
                              <ResponsiveContainer width="100%" height="100%">
                                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={progress.topic_stats}>
                                  <PolarGrid stroke="rgba(255,255,255,0.1)" />
                                  <PolarAngleAxis dataKey="topic" tick={{ fill: '#fff', fontSize: 10, fontWeight: 'bold' }} />
                                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} />
                                  <Radar name="Accuracy" dataKey="accuracy" stroke="#10b981" strokeWidth={3} fill="#10b981" fillOpacity={0.4} />
                                  <RechartsTooltip contentStyle={{ backgroundColor: '#060a12', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', boxShadow: '0 4px 15px rgba(0,0,0,0.5)' }} itemStyle={{ color: '#fff', fontWeight: 'bold' }} />
                                </RadarChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm h-40">
                          No progress data yet. Complete some offline practice questions to see your learning curve!
                        </div>
                      )}
                    </div>
                  ) : tab === 'create' ? (
                    <form onSubmit={createLobby} className="space-y-6 max-w-xl mx-auto w-full">
                      <div>
                        <label className="block text-xs sm:text-sm font-bold uppercase tracking-wider mb-2 text-slate-400 ml-1">Room Name</label>
                        <input className="w-full px-5 py-4 bg-[#101018]/80 border border-white/[0.07] rounded-2xl text-base text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50 focus:bg-[#101018] transition-colors" 
                          placeholder={`${user?.username}'s Arena`} value={lobbyName} onChange={e => setLobbyName(e.target.value)} />
                      </div>

                      <div>
                        <label className="block text-xs sm:text-sm font-bold uppercase tracking-wider mb-2 text-slate-400 ml-1">Game Mode</label>
                        <div className="grid grid-cols-2 gap-3 sm:gap-4">
                          {[{ v: 'multiplayer', label: 'Multiplayer', sub: 'Up to 20 players' }, { v: '1v1', label: '1v1 Duel', sub: 'Head-to-head' }].map(m => (
                            <button key={m.v} type="button" onClick={() => setGameMode(m.v)}
                              className={`p-4 rounded-2xl text-center transition-all duration-300 ${
 gameMode === m.v 
                                  ? 'bg-blue-500/20 border-blue-500/50 shadow-[inset_0_0_20px_rgba(59,130,246,0.15)]' 
                                  : 'bg-[#101018]/80 border-white/[0.07] hover:border-blue-500/30 hover:bg-[#101018]'
                              } border`}>
                              <div className="text-sm font-bold text-white">{m.label}</div>
                              <div className="text-xs mt-1 text-slate-500">{m.sub}</div>
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-3 sm:gap-4">
                        <div>
                          <label className="block text-xs sm:text-[10px] font-bold uppercase tracking-wider mb-2 text-slate-400 ml-1">Players</label>
                          <input className="w-full px-4 py-3 bg-[#101018]/80 border border-white/[0.07] rounded-2xl text-base text-white text-center focus:outline-none focus:border-blue-500/50 transition-colors" 
                            type="number" min="2" max="20" value={maxPlayers} onChange={e => setMaxPlayers(e.target.value)} />
                        </div>
                        <div>
                          <label className="block text-xs sm:text-[10px] font-bold uppercase tracking-wider mb-2 text-slate-400 ml-1">Time (s)</label>
                          <input className="w-full px-4 py-3 bg-[#101018]/80 border border-white/[0.07] rounded-2xl text-base text-white text-center focus:outline-none focus:border-blue-500/50 transition-colors" 
                            type="number" value={duration} onChange={e => setDuration(e.target.value)} />
                        </div>
                        <div>
                          <label className="block text-xs sm:text-[10px] font-bold uppercase tracking-wider mb-2 text-slate-400 ml-1">Questions</label>
                          <input className="w-full px-4 py-3 bg-[#101018]/80 border border-white/[0.07] rounded-2xl text-base text-white text-center focus:outline-none focus:border-blue-500/50 transition-colors" 
                            type="number" min="1" max="50" value={totalQuestions} onChange={e => setTotalQuestions(e.target.value)} />
                        </div>
                      </div>

                      <div className="flex items-center justify-between p-4 sm:p-5 rounded-2xl bg-[#101018]/80 border border-white/[0.07]">
                        <div className="flex-1">
                          <div className="text-sm font-bold text-white">Public Room</div>
                          <div className="text-xs mt-1 text-slate-500">Anyone can join with the code</div>
                        </div>
                        <button type="button" onClick={() => setIsPublic(!isPublic)} 
                          className={`relative w-14 h-7 rounded-full transition-colors duration-300 flex-shrink-0 ml-4 ${isPublic ? 'bg-blue-500' : 'bg-slate-800'}`}>
                          <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform duration-300 ${isPublic ? 'translate-x-8' : 'translate-x-1'}`} />
                        </button>
                      </div>

                      {error && <p className="text-sm text-red-400 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-center font-medium">{error}</p>}

                      <button type="submit" disabled={creating} 
                        className="w-full py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-base text-white font-black uppercase tracking-wider rounded-2xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(59,130,246,0.3)]">
                        {creating ? <><span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block mr-2 align-middle" />CREATING...</> : 'LAUNCH MATCH'}
                      </button>
                    </form>
                  ) : (
                    <form onSubmit={joinLobby} className="space-y-6 max-w-md mx-auto w-full">
                      <div>
                        <label className="block text-sm font-bold uppercase tracking-wider mb-4 text-slate-400 text-center">Enter Room Code</label>
                        <input className="w-full px-6 py-5 bg-[#101018]/80 border-2 border-white/[0.05] rounded-2xl text-white text-center text-3xl font-black uppercase tracking-[0.4em] placeholder-slate-700 focus:outline-none focus:border-blue-500/50 transition-colors"
                          placeholder="CODE" value={joinCode}
                          onChange={e => setJoinCode(e.target.value.toUpperCase())} maxLength={6} autoFocus />
                      </div>
                      {joinError && <p className="text-sm text-red-400 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-center font-medium">{joinError}</p>}
                      <button type="submit" disabled={joining || !joinCode.trim()} 
                        className="w-full py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-base text-white font-black uppercase tracking-wider rounded-2xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(59,130,246,0.3)]">
                        {joining ? 'JOINING...' : 'JOIN MATCH'}
                      </button>
                    </form>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Column 3: Leaderboard & Topics (Col-Span 3) */}
          <div className="lg:col-span-3 flex flex-col gap-4 sm:gap-6">
            
            {/* Leaderboard Card */}
            <div className="relative group w-full " style={{ animationDelay: '0.3s' }}>
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-3xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="relative bg-[#0A0A10]/80 backdrop-blur-xl border border-white/[0.07] rounded-3xl overflow-hidden shadow-2xl flex flex-col">
                <div className="px-6 py-5 border-b border-white/[0.07] bg-white/[0.02]">
                  <h3 className="text-sm font-bold text-white flex items-center justify-between">
                    <span>🏆 Top Players</span>
                    <span className="text-[10px] font-black uppercase px-2 py-1 rounded-md bg-blue-500/20 text-blue-300 border border-blue-500/30">Global</span>
                  </h3>
                </div>
                <div className="p-4 space-y-2">
                  {leaderboard.length > 0 ? leaderboard.map((p, i) => (
                    <div key={i} className="flex items-center gap-3 px-3 py-3 rounded-2xl transition-all duration-300 hover:bg-white/[0.05] cursor-pointer">
                      <span className="text-sm font-black w-6 text-center flex-shrink-0" style={{ color: RANK_COLORS[i] }}>{RANK_LABELS[i]}</span>
                      <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-black text-white shadow-lg flex-shrink-0"
                        style={{ background: `linear-gradient(135deg, ${RANK_COLORS[i]}40, ${RANK_COLORS[i]}20)`, border: `2px solid ${RANK_COLORS[i]}60` }}>
                        {(p.username || p.name || '?').charAt(0).toUpperCase()}
                      </div>
                      <span className="flex-1 text-sm text-white font-bold truncate">{p.username || p.name}</span>
                      <span className="text-xs font-mono font-bold px-2 py-1.5 rounded-lg bg-[#101018] text-blue-400 border border-white/[0.05]">{p.score || p.total_score || 0}</span>
                    </div>
                  )) : (
                    <p className="text-center py-8 text-xs font-medium text-slate-500">No players yet. Be the first! 🚀</p>
                  )}
                </div>
              </div>
            </div>

            {/* Practice Topics Card */}
            <div className="relative group w-full " style={{ animationDelay: '0.4s' }}>
              <div className="absolute -inset-1 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-3xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="relative bg-[#0A0A10]/80 backdrop-blur-xl border border-white/[0.07] rounded-3xl overflow-hidden shadow-2xl">
                <div className="px-6 py-5 border-b border-white/[0.07] bg-white/[0.02]">
                  <h3 className="text-sm font-bold text-white">📚 Practice Topics</h3>
                </div>
                <div className="p-5 flex flex-wrap gap-2">
                  {TOPICS.map(t => (
                    <button key={t} onClick={() => nav('/practice')} 
                      className="px-4 py-2 text-xs font-bold rounded-xl bg-[#101018] text-slate-300 border border-white/[0.07] hover:bg-blue-500/20 hover:text-blue-300 hover:border-blue-500/30 transition-all duration-300 shadow-sm">
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* Achievements Section */}
        {achievements.length > 0 && (
          <div className="mt-4 w-full" style={{ animationDelay: '0.5s' }}>
            <div className="flex flex-col sm:flex-row items-center justify-center sm:justify-between gap-3 sm:gap-0 mb-6 bg-[#0A0A10]/40 p-6 rounded-3xl border border-white/[0.05]">
              <h2 className="text-xl font-black text-white uppercase tracking-wider">🎖️ Achievements</h2>
              <span className="text-xs font-bold px-4 py-2 rounded-xl bg-blue-500/20 text-blue-300 border border-blue-500/30 whitespace-nowrap uppercase tracking-widest">
                {unlockedCount} / {achievements.length} unlocked
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6 justify-items-center">
              {achievements.map((a, i) => (
                <div key={a.id} 
                  className={`relative group transition-all duration-300 w-full max-w-sm ${a.unlocked ? 'opacity-100' : 'opacity-50 grayscale'}`}>
                  <div className={`absolute -inset-1 bg-gradient-to-r from-blue-600/30 to-cyan-600/30 rounded-3xl blur-xl transition-opacity duration-500 ${a.unlocked ? 'opacity-0 group-hover:opacity-100' : 'opacity-0'}`} />
                  <div className={`relative bg-[#0A0A10]/80 backdrop-blur-md border rounded-3xl p-6 sm:p-8 text-center transition-all duration-300 h-full flex flex-col items-center justify-center ${
 a.unlocked 
                      ? 'border-white/[0.07]  hover:shadow-[0_10px_30px_rgba(59,130,246,0.2)] cursor-pointer' 
                      : 'border-white/[0.04] cursor-not-allowed'
                  }`}>
                    <div className="text-4xl sm:text-5xl mb-4 transition-transform duration-500 filter drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">{a.icon || '🏅'}</div>
                    <div className="text-sm sm:text-base font-black text-white mb-2 uppercase tracking-wide">{a.name}</div>
                    <div className="text-xs sm:text-sm text-slate-400 leading-relaxed font-medium">{a.description}</div>
                    {a.unlocked && (
                      <div className="mt-4 pt-4 border-t border-white/[0.07] w-full">
                        <span className="text-xs font-black uppercase tracking-widest text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/20">✓ Unlocked</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
