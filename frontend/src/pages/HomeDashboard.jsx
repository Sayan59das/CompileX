import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import Logo from '../components/Logo'

export default function HomeDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  
  const [joinCode, setJoinCode] = useState('')
  const [lobbyName, setLobbyName] = useState('')
  const [maxPlayers, setMaxPlayers] = useState(10)
  const [timeLimit, setTimeLimit] = useState(1800)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState('create')

  const [gameMode, setGameMode] = useState('multiplayer')
  const [isPublic, setIsPublic] = useState(false)
  const [publicLobbies, setPublicLobbies] = useState([])
  const [loadingPublic, setLoadingPublic] = useState(false)
  const [difficulty, setDifficulty] = useState('medium')

  useEffect(() => {
    if (tab === 'browse') fetchPublicLobbies()
  }, [tab])

  async function fetchPublicLobbies() {
    setLoadingPublic(true)
    try {
      const { data } = await api.get('/lobbies/public')
      setPublicLobbies(data)
    } catch { }
    finally { setLoadingPublic(false) }
  }

  async function createLobby(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data: lobby } = await api.post('/lobbies', {
        name: lobbyName || `${user.username}'s Arena`,
        max_players: Number(maxPlayers),
        time_limit: Number(timeLimit),
        game_mode: gameMode,
        is_public: isPublic,
        match_config: {
          num_rounds: 1,
          questions_per_round: 1,
          difficulty,
          time_per_question: Number(timeLimit),
        },
      })
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      navigate(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create')
    } finally {
      setLoading(false)
    }
  }

  async function joinLobby(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data: lobby } = await api.get(`/lobbies/${joinCode.toUpperCase()}`)
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      navigate(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Arena not found')
    } finally {
      setLoading(false)
    }
  }

  async function joinPublicLobby(lobby) {
    setError('')
    setLoading(true)
    try {
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      navigate(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Join failed')
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { key: 'create', label: 'Create Arena', icon: '🎮' },
    { key: 'join', label: 'Join Arena', icon: '🚪' },
    { key: 'browse', label: 'Browse Public', icon: '🌐' },
    { key: 'practice', label: 'Practice', icon: '💪' },
  ]

  return (
    <div className="min-h-screen bg-[#05050A] relative overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-blue-500/20 rounded-full blur-[120px] animate-float-slow" />
        <div className="absolute bottom-0 right-1/4 w-[700px] h-[700px] bg-cyan-500/15 rounded-full blur-[130px] animate-float-slower" style={{ animationDelay: '3s' }} />
        <div className="absolute inset-0 opacity-[0.08]" style={{ 
          backgroundImage: 'linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px)', 
          backgroundSize: '50px 50px' 
        }} />
      </div>

      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A10]/80 backdrop-blur-xl border-b border-white/[0.07]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 group cursor-pointer" onClick={() => navigate('/home')}>
            <Logo size={40} className="transition-all duration-300 group-hover:scale-110 group-hover:rotate-6" />
            <span className="text-xl font-bold text-white">CompileX</span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-[#101018] rounded-xl border border-white/[0.07]">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm text-white font-medium">{user?.username}</span>
            </div>
            <button onClick={() => navigate('/profile')} className="text-sm text-slate-400 hover:text-white transition-colors">
              Profile
            </button>
            <button onClick={logout} className="text-sm text-slate-400 hover:text-white transition-colors">
              Sign out
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="pt-24 pb-12 px-6">
        <div className="max-w-4xl mx-auto">
          {/* Welcome Header */}
          <div className="text-center mb-12 animate-fade-in">
            <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
              Welcome back, <span className="text-blue-400">{user?.username}</span>!
            </h1>
            <p className="text-slate-400 text-lg">Ready to code, compete, and conquer?</p>
          </div>

          {/* Tabs */}
          <div className="flex items-center justify-center gap-2 mb-8">
            {tabs.map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-6 py-3 rounded-xl font-medium transition-all duration-300 ${
                  tab === t.key
                    ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-500/50'
                    : 'bg-[#101018] text-slate-400 hover:text-white hover:bg-[#1f2937] border border-white/[0.07]'
                }`}
              >
                <span className="mr-2">{t.icon}</span>
                {t.label}
              </button>
            ))}
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm flex items-center gap-3 animate-shake">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}

          {/* Tab Content */}
          <div className="bg-[#0A0A10] border border-white/[0.07] rounded-2xl p-8 shadow-2xl">
            {tab === 'create' && (
              <form onSubmit={createLobby} className="space-y-6">
                <h2 className="text-2xl font-bold text-white mb-6">Create New Arena</h2>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Arena Name</label>
                  <input
                    className="w-full px-4 py-3 bg-[#101018] border border-white/[0.07] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    placeholder={`${user?.username}'s Arena`}
                    value={lobbyName}
                    onChange={e => setLobbyName(e.target.value)}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Max Players</label>
                    <input
                      type="number"
                      className="w-full px-4 py-3 bg-[#101018] border border-white/[0.07] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                      value={maxPlayers}
                      onChange={e => setMaxPlayers(e.target.value)}
                      min="2"
                      max="50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">Time Limit (seconds)</label>
                    <input
                      type="number"
                      className="w-full px-4 py-3 bg-[#101018] border border-white/[0.07] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                      value={timeLimit}
                      onChange={e => setTimeLimit(e.target.value)}
                      min="60"
                      max="7200"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Difficulty</label>
                  <select
                    className="w-full px-4 py-3 bg-[#101018] border border-white/[0.07] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                    value={difficulty}
                    onChange={e => setDifficulty(e.target.value)}
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="public"
                    checked={isPublic}
                    onChange={e => setIsPublic(e.target.checked)}
                    className="w-5 h-5 rounded bg-[#101018] border-white/[0.07] text-blue-600 focus:ring-2 focus:ring-blue-500/50"
                  />
                  <label htmlFor="public" className="text-sm text-slate-300">Make arena public</label>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-xl hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Creating...' : 'Create Arena'}
                </button>
              </form>
            )}

            {tab === 'join' && (
              <form onSubmit={joinLobby} className="space-y-6">
                <h2 className="text-2xl font-bold text-white mb-6">Join Arena</h2>
                
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Arena Code</label>
                  <input
                    className="w-full px-4 py-3 bg-[#101018] border border-white/[0.07] rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 uppercase"
                    placeholder="Enter 6-character code"
                    value={joinCode}
                    onChange={e => setJoinCode(e.target.value.toUpperCase())}
                    maxLength={6}
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || joinCode.length !== 6}
                  className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-xl hover:scale-[1.02] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Joining...' : 'Join Arena'}
                </button>
              </form>
            )}

            {tab === 'browse' && (
              <div>
                <h2 className="text-2xl font-bold text-white mb-6">Public Arenas</h2>
                
                {loadingPublic ? (
                  <div className="text-center py-12 text-slate-400">Loading...</div>
                ) : publicLobbies.length === 0 ? (
                  <div className="text-center py-12 text-slate-400">No public arenas available</div>
                ) : (
                  <div className="space-y-4">
                    {publicLobbies.map(lobby => (
                      <div key={lobby.id} className="p-4 bg-[#101018] border border-white/[0.07] rounded-xl hover:border-blue-500/30 transition-all">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="text-white font-semibold">{lobby.name}</h3>
                            <p className="text-sm text-slate-400">
                              {lobby.current_players}/{lobby.max_players} players • {lobby.difficulty}
                            </p>
                          </div>
                          <button
                            onClick={() => joinPublicLobby(lobby)}
                            disabled={loading}
                            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
                          >
                            Join
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {tab === 'practice' && (
              <div className="text-center py-12">
                <h2 className="text-2xl font-bold text-white mb-4">Practice Mode</h2>
                <p className="text-slate-400 mb-8">Sharpen your skills with solo challenges</p>
                <button
                  onClick={() => navigate('/practice')}
                  className="px-8 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold rounded-xl hover:scale-105 transition-all"
                >
                  Start Practice
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
