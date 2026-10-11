import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import OAuthCallback from '../components/OAuthCallback'
import AuthLayout, { Field, FormAlert, Divider } from '../components/AuthLayout'
import { OAuthButtons } from './Login'

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

  return (
    <AuthLayout
      title="Create your account"
      subtitle="It takes a minute, and the first thing you do is a short skill check that sets your starting rating."
      pitch={{
        title: 'Get a rating, then go and earn a better one.',
        body: 'Every match and practice session moves your rating, and matchmaking uses it to find people at your level.',
      }}
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-ink underline underline-offset-4">Log in</Link>
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
          id="email"
          label="Email"
          type="email"
          optional
          value={form.email}
          onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
          autoComplete="email"
          hint="Used only to send a password reset code."
        />
        <Field
          id="password"
          label="Password"
          type="password"
          value={form.password}
          onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          autoComplete="new-password"
          required
          minLength={6}
          hint="At least 6 characters."
        />
        <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full">
          {loading ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />
              Creating account…
            </>
          ) : (
            'Create account'
          )}
        </button>
      </form>

      <Divider>or sign up with</Divider>
      <OAuthButtons />
    </AuthLayout>
  )
}
