import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import OAuthCallback from '../components/OAuthCallback'

import AnimatedBackgroundCSS from '../components/AnimatedBackgroundCSS'

export default function Register() {
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const nav = useNavigate()
  const location = useLocation()

  const searchParams = new URLSearchParams(location.search)
  const isOAuthCallback = searchParams.has('oauth_success') || searchParams.has('oauth_error')

  useEffect(() => {
    if (location.state?.error) {
      setError(location.state.error)
      window.history.replaceState({}, document.title)
    }
  }, [location])

  if (isOAuthCallback) return <OAuthCallback />

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const payload = {
        username: form.username,
        password: form.password,
        ...(form.email ? { email: form.email } : {}),
      }
      await api.post('/auth/register', payload)
      const { data } = await api.post('/auth/login', { username: form.username, password: form.password })
      localStorage.setItem('token', data.access_token)
      const { data: profile } = await api.get('/users/me')
      login({ id: profile.id, username: profile.username, email: profile.email, rating: profile.rating, skill_quiz_completed: profile.skill_quiz_completed }, data.access_token)
      nav('/home')
    } catch (err) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail[0]?.msg || 'Validation error')
      } else {
        setError(detail || 'Registration failed')
      }
    } finally {
      setLoading(false)
    }
  }

  function handleOAuth(provider) {
    const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '')
    window.location.href = `${base}/api/v1/auth/${provider}`
  }

  return (
    <>
      <style>{`
        /* Floating label specific for auth */
        .auth-input-group { position: relative; }
        .auth-input-group input { 
          width: 100%; 
          background: transparent; 
          border: none;
          border-bottom: 2px solid rgba(255,255,255,0.1); 
          padding: 24px 0 8px 0;
          color: white; 
          font-size: 16px; 
          transition: border-color 0.3s; 
          outline: none;
        }
        .auth-input-group label {
          position: absolute; 
          left: 0; 
          top: 16px; 
          color: #64748b; 
          font-size: 16px; 
          pointer-events: none; 
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .auth-input-group input:focus, .auth-input-group input:not(:placeholder-shown) {
          border-bottom-color: #06b6d4;
        }
        .auth-input-group input:focus ~ label, .auth-input-group input:not(:placeholder-shown) ~ label {
          top: 0px; 
          font-size: 12px; 
          color: #06b6d4; 
          font-weight: 600;
        }
        .auth-input-group .line {
          position: absolute; bottom: 0; left: 50%; width: 0; height: 2px;
          background: #3b82f6; transition: all 0.4s ease; transform: translateX(-50%);
        }
        .auth-input-group input:focus ~ .line { width: 100%; }

        /* Liquid Button */
        .btn-liquid {
          position: relative;
          background: linear-gradient(90deg, #3b82f6, #06b6d4, #3b82f6);
          background-size: 200% auto;
          color: white;
          border: none;
          overflow: hidden;
          transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-liquid:hover {
          animation: shine 2s linear infinite;
          box-shadow: 0 0 20px rgba(6, 182, 212, 0.4);
          transform: translateY(-2px);
        }
        @keyframes shine { to { background-position: 200% center; } }
      `}</style>

      <div className="min-h-screen w-full flex items-center justify-center p-4 relative">
        {/* 3D Background now spans the entire screen */}
        <AnimatedBackgroundCSS />
        
        {/* Completely Transparent Container */}
        <div className="w-full max-w-6xl flex relative z-10">
          
          {/* LEFT PANE: Text Content */}
          <div className="hidden lg:flex w-1/2 flex-col justify-between p-16 relative">
            
            <div className="relative z-10 ">
              <Link to="/" className="flex items-center gap-3 cursor-pointer group">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center rounded-xl shadow-lg shadow-blue-500/20 transition-transform duration-300 ">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                  </svg>
                </div>
                <span className="text-2xl font-bold font-mono text-white tracking-widest group-hover:text-cyan-400 transition-colors">COMPILE.X</span>
              </Link>
            </div>

            <div className="relative z-10 max-w-xl ">
              <h1 className="text-6xl font-black text-white leading-[1.1] tracking-tight mb-6 " style={{animationDelay: '0.1s'}}>
                Join the elite.<br/>
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">Master your craft.</span>
              </h1>
              <p className="text-xl text-slate-400 font-medium " style={{animationDelay: '0.2s'}}>
                Create an account to track your progress, climb the global leaderboards, and prove your programming prowess.
              </p>
            </div>

            <div className="relative z-10 " style={{animationDelay: '0.3s'}}>
              <p className="text-sm text-slate-600 font-medium tracking-wide uppercase">© 2026 CompileX Platform</p>
            </div>
          </div>

          {/* RIGHT PANE: Register Form */}
          <div className="w-full lg:w-1/2 flex items-center justify-center p-8 sm:p-12 lg:p-16 relative">
            
            <Link to="/" className="absolute top-8 left-8 lg:hidden flex items-center gap-3 cursor-pointer ">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center rounded-lg shadow-lg">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                </svg>
              </div>
            </Link>

          <div className="w-full max-w-md " style={{animationDelay: '0.2s'}}>
            <div className="mb-12">
              <h2 className="text-4xl font-bold text-white mb-3">Create an Account</h2>
              <p className="text-slate-400 text-lg">Join thousands of competitive coders.</p>
            </div>

            {error && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-lg mb-8 text-sm bg-red-500/10 border border-red-500/20 text-red-400 ">
                <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="12" cy="12" r="10"/><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01"/></svg>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Animated Floating Label Input - Username */}
              <div className="auth-input-group group">
                <input
                  type="text"
                  placeholder=" "
                  value={form.username}
                  onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                  required
                />
                <label>Username</label>
                <div className="line"></div>
              </div>

              {/* Animated Floating Label Input - Email */}
              <div className="auth-input-group group">
                <input
                  type="email"
                  placeholder=" "
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                />
                <label>Email <span className="text-xs opacity-60">(Optional)</span></label>
                <div className="line"></div>
              </div>

              {/* Animated Floating Label Input - Password */}
              <div className="auth-input-group group">
                <input
                  type="password" 
                  placeholder=" "
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                  minLength={6}
                />
                <label>Password</label>
                <div className="line"></div>
              </div>

              <button type="submit" disabled={loading}
                className="btn-liquid w-full py-4 font-bold rounded-xl text-lg flex items-center justify-center gap-2 mt-4 disabled:opacity-50 disabled:cursor-not-allowed">
                {loading
                  ? <><span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Creating Account…</>
                  : 'Create Account'
                }
              </button>
            </form>

            <div className="flex items-center gap-4 my-10 opacity-60">
              <div className="flex-1 h-px bg-white/[0.1]" />
              <span className="text-xs text-slate-400 font-medium uppercase tracking-widest">Or connect via</span>
              <div className="flex-1 h-px bg-white/[0.1]" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              {[
                { id: 'google', label: 'Google', icon: (
                  <svg width="20" height="20" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                )},
                { id: 'github', label: 'GitHub', icon: (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
                  </svg>
                )},
              ].map(p => (
                <button key={p.id} onClick={() => handleOAuth(p.id)}
                  className="flex items-center justify-center gap-3 py-3.5 rounded-xl border border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.06] text-slate-300 font-semibold transition-all duration-300 hover:border-cyan-500/30 hover:shadow-[0_0_15px_rgba(6,182,212,0.15)] ">
                  {p.icon}
                  {p.label}
                </button>
              ))}
            </div>

            <p className="text-center text-slate-400 mt-10">
              Already have an account?{' '}
              <Link to="/login" className="text-cyan-400 hover:text-cyan-300 font-bold transition-colors">Sign in</Link>
            </p>
          </div>
        </div>
      </div>
      </div>
    </>
  )
}
