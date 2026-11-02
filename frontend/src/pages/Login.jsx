import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import OAuthCallback from '../components/OAuthCallback'

import AuthLayout, { Field, FormError, SubmitButton, OAuthButtons } from '../components/AuthLayout'

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

  function handleOAuth(provider) {
    const base = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '')
    window.location.href = `${base}/api/v1/auth/${provider}`
  }

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Welcome back. Pick up where you left off."
      footer={<>New to CompileX? <Link to="/register" className="font-medium text-arc hover:text-white">Create an account</Link></>}
    >
      <FormError>{error}</FormError>
      <form onSubmit={handleSubmit} className="space-y-5">
        <Field id="username" label="Username" type="text" autoComplete="username" required
          value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
        <Field id="password" label="Password" type="password" autoComplete="current-password" required
          aside={<Link to="/forgot-password" className="text-[13px] text-slate-400 hover:text-white">Forgot password?</Link>}
          value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        <SubmitButton loading={loading} loadingText="Signing in">Sign in</SubmitButton>
      </form>
      <OAuthButtons onClick={handleOAuth} />
    </AuthLayout>
  )
}
