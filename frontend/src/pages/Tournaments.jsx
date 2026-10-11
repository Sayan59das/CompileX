import React, { useState, useEffect } from 'react'
import Logo from '../components/Logo'
import AnimatedBackgroundCSS from '../components/AnimatedBackgroundCSS'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

const TOPICS = ['Arrays', 'Strings', 'Recursion', 'DP', 'Graphs', 'Trees', 'Sorting', 'Searching', 'Math', 'Greedy']
const diffColor = {
  easy: 'text-emerald bg-emerald/10 border-emerald/20',
  medium: 'text-amber bg-amber/10 border-amber/20',
  hard: 'text-rose bg-rose/10 border-rose/20',
}

export default function Tournaments() {
  const { user, logout } = useAuth()
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

  const statusColor = {
    registration: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    in_progress: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    completed: 'text-slate-400 bg-white/5 border-white/10',
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-[#0a0f1c]">
      <AnimatedBackgroundCSS />

      {/* Navbar */}
      <nav className="relative border-b border-white/10 backdrop-blur-xl bg-slate-900/50 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => nav('/home')} className="text-slate-400 hover:text-white transition-colors duration-300 flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Home
            </button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/50">
                <Logo size={32} />
              </div>
              <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">Tournaments</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 backdrop-blur-sm border border-white/10">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm text-slate-300">{user?.username}</span>
            </div>
            <button onClick={logout} className="text-sm text-slate-400 hover:text-white transition-colors duration-300">Sign out</button>
          </div>
        </div>
      </nav>

      <div className="relative max-w-4xl mx-auto px-6 py-10">
        <div className="text-center mb-10 animate-fade-in">
          <h1 className="text-4xl font-extrabold text-white mb-2 bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent">Tournament Arena</h1>
          <p className="text-slate-400">Compete in bracket-style tournaments against the best coders</p>
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl p-3 mb-4 text-sm max-w-xl mx-auto backdrop-blur-sm">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex justify-center gap-2 mb-8">
          {[['browse', 'Browse Tournaments'], ['create', 'Create Tournament'], ['join', 'Join by Code']].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${
                tab === key 
                  ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg shadow-blue-500/50' 
                  : 'bg-white/5 backdrop-blur-sm border border-white/10 text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Browse */}
        {tab === 'browse' && (
          <div className="space-y-3 animate-fade-in">
            {loading ? (
              <div className="text-center py-12 text-slate-500 animate-pulse">Loading tournaments...</div>
            ) : tournaments.length === 0 ? (
              <div className="relative overflow-hidden rounded-3xl bg-[#0a0f1c]/60 backdrop-blur-xl border border-white/[0.05] p-12 sm:p-16 text-center shadow-2xl">
                {/* Glowing background effects inside the card */}
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[200px] bg-gradient-to-b from-amber-500/10 to-transparent pointer-events-none" />
                <div className="absolute -bottom-[50px] -right-[50px] w-[200px] h-[200px] bg-yellow-500/10 blur-[80px] pointer-events-none rounded-full" />
                <div className="absolute -top-[50px] -left-[50px] w-[200px] h-[200px] bg-amber-600/10 blur-[80px] pointer-events-none rounded-full" />
                
                <div className="relative z-10 flex flex-col items-center">
                  {/* Animated Trophy Icon */}
                  <div className="relative flex items-center justify-center w-24 h-24 mb-6">
                    <div className="absolute inset-0 rounded-full border border-amber-500/30 animate-ping" style={{ animationDuration: '3s' }} />
                    <div className="absolute inset-2 rounded-full border border-yellow-400/20 animate-ping" style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
                    <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-400 flex items-center justify-center shadow-[0_0_30px_rgba(245,158,11,0.5)]">
                      <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M19 3v4M5 3a2 2 0 002 2h10a2 2 0 002-2M5 3h14M7 21h10M9 17v4M15 17v4M9 7h6M12 7v10" />
                      </svg>
                    </div>
                  </div>
                  
                  <h2 className="text-2xl font-black text-white mb-3 tracking-tight">No Active Tournaments</h2>
                  <p className="text-slate-400 max-w-md mx-auto mb-8 leading-relaxed">
                    The arena is quiet. There are currently no tournaments running. Step up and be the first to host an epic coding battle!
                  </p>
                  
                  <button 
                    onClick={() => setTab('create')} 
                    className="group relative px-8 py-3.5 rounded-xl bg-amber-500 text-white font-bold tracking-wide overflow-hidden transition-all hover:scale-105 active:scale-95 shadow-[0_0_20px_rgba(245,158,11,0.4)]"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-amber-600 via-yellow-500 to-amber-600 bg-[length:200%_auto] animate-[shine_3s_linear_infinite]" />
                    <div className="absolute inset-0 bg-white/0 group-hover:bg-white/20 transition-colors" />
                    <span className="relative z-10 flex items-center gap-2">
                      Create Tournament
                      <svg className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                      </svg>
                    </span>
                  </button>
                </div>
              </div>
            ) : (
              tournaments.map(t => (
                <div key={t.id} className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-5 flex items-center gap-4 hover:bg-white/10 hover:border-blue-500/30 transition-all duration-300 group">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-white group-hover:text-blue-300 transition-colors duration-300">{t.name}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${statusColor[t.status]}`}>
                        {t.status.replace('_', ' ')}
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${diffColor[t.difficulty]}`}>
                        {t.difficulty}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">
                      {t.participant_count}/{t.max_participants} participants &middot; Code: <span className="font-mono text-blue-400">{t.code}</span>
                    </div>
                  </div>
                  {t.status === 'registration' && (
                    <button onClick={() => joinTournament(t.code)} className="px-5 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-xs font-medium hover:shadow-lg hover:shadow-emerald-500/50 transition-all duration-300">
                      Join
                    </button>
                  )}
                  <button onClick={() => nav(`/tournament/${t.code}`)} className="text-xs text-blue-400 hover:text-white transition-colors duration-300 px-3 py-2">
                    View
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {/* Create */}
        {tab === 'create' && (
          <form onSubmit={createTournament} className="max-w-lg mx-auto bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 space-y-4 shadow-2xl shadow-blue-500/10 animate-slide-up">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Tournament Name</label>
              <input 
                className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300" 
                placeholder="Epic Tournament" 
                value={name} 
                onChange={e => setName(e.target.value)} 
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Max Participants</label>
                <input 
                  type="number" 
                  min="2" 
                  max="128" 
                  className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300" 
                  value={maxParticipants} 
                  onChange={e => setMaxParticipants(e.target.value)} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Rounds per Match</label>
                <input 
                  type="number" 
                  min="1" 
                  max="5" 
                  className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300" 
                  value={roundsPerMatch} 
                  onChange={e => setRoundsPerMatch(e.target.value)} 
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Q / Round</label>
                <input 
                  type="number" 
                  min="1" 
                  max="3" 
                  className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300" 
                  value={questionsPerRound} 
                  onChange={e => setQuestionsPerRound(e.target.value)} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Sec / Question</label>
                <input 
                  type="number" 
                  min="60" 
                  max="3600" 
                  step="60" 
                  className="w-full px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300" 
                  value={timePerQuestion} 
                  onChange={e => setTimePerQuestion(e.target.value)} 
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Difficulty</label>
              <div className="flex gap-2">
                {['easy', 'medium', 'hard'].map(d => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDifficulty(d)}
                    className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium border transition-all duration-300 ${
                      difficulty === d ? diffColor[d] + ' shadow-lg' : 'text-slate-500 border-white/10 bg-white/5 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    {d.charAt(0).toUpperCase() + d.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Topics</label>
              <div className="flex flex-wrap gap-1.5">
                {TOPICS.map(t => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleTopic(t)}
                    className={`px-2.5 py-1 rounded-lg text-xs transition-all duration-300 border ${
                      selectedTopics.includes(t) 
                        ? 'bg-blue-500/20 border-blue-500/40 text-blue-300 shadow-lg shadow-blue-500/20' 
                        : 'border-white/10 bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <button 
              type="submit" 
              disabled={creating} 
              className="w-full py-3 text-base font-medium rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? 'Creating...' : 'Create Tournament'}
            </button>
          </form>
        )}

        {/* Join by Code */}
        {tab === 'join' && (
          <div className="max-w-md mx-auto bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 shadow-2xl shadow-blue-500/10 animate-slide-up">
            <label className="block text-sm font-medium text-slate-300 mb-2">Tournament Code</label>
            <input
              className="w-full px-4 text-center text-2xl font-mono font-bold tracking-[0.3em] uppercase py-4 mb-4 rounded-lg bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
              placeholder="ABC123"
              maxLength={6}
              value={joinCode}
              onChange={e => setJoinCode(e.target.value.toUpperCase())}
            />
            <button 
              onClick={() => joinTournament(joinCode)} 
              disabled={!joinCode} 
              className="w-full py-3 text-base font-medium rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:shadow-lg hover:shadow-emerald-500/50 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Join Tournament
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
