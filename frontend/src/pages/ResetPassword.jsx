import React, { useState, useEffect } from 'react'
import Logo from '../components/Logo'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import AnimatedBackgroundCSS from '../components/AnimatedBackgroundCSS'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const [form, setForm] = useState({ newPassword: '', confirmPassword: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [tokenValid, setTokenValid] = useState(true)
  const nav = useNavigate()
  
  const token = searchParams.get('token')

  useEffect(() => {
    if (!token) {
      setTokenValid(false)
      setError('Invalid or missing reset token. Please request a new password reset.')
    }
  }, [token])

  async function handlePasswordReset(e) {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (form.newPassword !== form.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (form.newPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/reset-password', {
        reset_token: token,
        new_password: form.newPassword,
      })
      setSuccess('Password reset successful! Redirecting to login...')
      setTimeout(() => nav('/login'), 2000)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to reset password'
      setError(errorMsg)
      
      // If token is invalid/expired, mark as invalid
      if (errorMsg.includes('Invalid') || errorMsg.includes('expired')) {
        setTokenValid(false)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full bg-[#050505] flex items-center justify-center px-4 relative overflow-hidden transition-colors duration-500">
      <AnimatedBackgroundCSS />

      <div className="w-full max-w-sm relative z-10 ">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4 shadow-2xl shadow-blue-500/50">
            <Logo size={48} />
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent tracking-tight">Set New Password</h1>
          <p className="text-sm mt-1 text-slate-400">
            Enter your new password below
          </p>
        </div>

        <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
          {error && (
            <div className="flex items-center gap-3 p-3 rounded-lg mb-6 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 ">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          )}

          {success && (
            <div className="flex items-center gap-3 p-3 rounded-lg mb-6 text-sm bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {success}
            </div>
          )}

          {!tokenValid ? (
            <div className="text-center">
              <div className="mb-6 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20">
                <svg className="w-12 h-12 mx-auto mb-3 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <h3 className="text-lg font-semibold mb-2 text-rose-400">Link Expired</h3>
                <p className="text-sm text-slate-400">
                  This reset link is invalid or has expired.
                </p>
              </div>
              <Link to="/forgot-password" className="w-full px-4 py-3 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300 inline-block text-center">
                Request New Reset Link
              </Link>
            </div>
          ) : (
            <form onSubmit={handlePasswordReset} className="space-y-4">
              <div>
                <label className="block text-xs font-medium mb-1.5 text-slate-300">New Password</label>
                <div className="relative">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <input
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
                    type="password"
                    placeholder="min. 6 characters"
                    value={form.newPassword}
                    onChange={e => setForm(f => ({ ...f, newPassword: e.target.value }))}
                    required
                    minLength={6}
                    autoFocus
                    disabled={!tokenValid}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1.5 text-slate-300">Confirm Password</label>
                <div className="relative">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                  <input
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-300"
                    type="password"
                    placeholder="re-enter password"
                    value={form.confirmPassword}
                    onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))}
                    required
                    minLength={6}
                    disabled={!tokenValid}
                  />
                </div>
              </div>

              <button 
                type="submit" 
                disabled={loading || !tokenValid} 
                className="w-full py-3 rounded-lg bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Resetting...
                  </>
                ) : (
                  <>
                    Reset Password
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </>
                )}
              </button>
            </form>
          )}

          <p className="text-center text-sm mt-6 text-slate-400">
            Remember your password?{' '}
            <Link to="/login" className="font-medium text-blue-400 hover:text-blue-300 transition-colors duration-300">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
