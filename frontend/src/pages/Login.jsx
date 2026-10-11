import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import OAuthCallback from '../components/OAuthCallback'
import AuthLayout, { Field, FormAlert, Divider } from '../components/AuthLayout'
import { GoogleMark, GithubMark } from '../components/Icons'

export function OAuthButtons() {
  function handleOAuth(provider) {
    const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '')
    window.location.href = `${base}/api/v1/auth/${provider}`
  }
  return (
    <div className="grid grid-cols-2 gap-3">
      <button type="button" onClick={() => handleOAuth('google')} className="btn btn-secondary h-11">
        <GoogleMark /> Google
      </button>
      <button type="button" onClick={() => handleOAuth('github')} className="btn btn-secondary h-11">
        <GithubMark /> GitHub
      </button>
    </div>
  )
}

export default function Login() {
  const [form, setForm] = useState({ username: '', password: '' })
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
      const { data } = await api.post('/auth/login', form)
      localStorage.setItem('token', data.access_token)
      const { data: profile } = await api.get('/users/me')
      login({ id: profile.id, username: profile.username, email: profile.email, rating: profile.rating, skill_quiz_completed: profile.skill_quiz_completed }, data.access_token)
      nav('/home')
    } catch (err) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail[0]?.msg || 'Validation error')
      } else {
        setError(detail || 'Invalid credentials')
      }
    } finally { setLoading(false) }
  }

  return (
    <AuthLayout
      title="Log in"
      subtitle="Pick up where you left off: your rooms, your rating and your practice history."
      pitch={{
        title: 'Your next match is a few minutes away.',
        body: 'Join a room with a code, or start one and send the code to whoever you want to beat.',
      }}
      footer={
        <>
          New to CompileX?{' '}
          <Link to="/register" className="font-semibold text-ink underline underline-offset-4">Create an account</Link>
        </>
      }
    >
      <FormAlert>{error}</FormAlert>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Field
          id="username"
          label="Username"
          value={form.username}
          onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
          autoComplete="username"
          required
          autoFocus
        />
        <Field
          id="password"
          label="Password"
          type="password"
          value={form.password}
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          autoComplete="current-password"
          required
          aside={
            <Link to="/forgot-password" className="text-sm font-medium text-ink-2 underline underline-offset-4 hover:text-ink">
              Forgot password?
            </Link>
          }
        />
        <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full">
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />
              Logging in…
            </>
          ) : (
            'Log in'
          )}
        </button>
      </form>

      <Divider>or continue with</Divider>
      <OAuthButtons />
    </AuthLayout>
  )
}
