import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import AuthLayout, { Field, FormAlert } from '../components/AuthLayout'

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
      setError('This reset link is missing its token. Request a new one to continue.')
    }
  }, [token])

  async function handlePasswordReset(e) {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (form.newPassword !== form.confirmPassword) {
      setError('The two passwords do not match.')
      return
    }

    if (form.newPassword.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/reset-password', {
        reset_token: token,
        new_password: form.newPassword,
      })
      setSuccess('Password updated. Taking you to the log in page…')
      setTimeout(() => nav('/login'), 2000)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to reset password'
      setError(errorMsg)

      // An invalid or expired token cannot be retried; send them for a new one.
      if (errorMsg.includes('Invalid') || errorMsg.includes('expired')) {
        setTokenValid(false)
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title={tokenValid ? 'Choose a new password' : 'This link no longer works'}
      subtitle={tokenValid ? 'Pick something you have not used on CompileX before.' : 'Reset links expire, and each one works once.'}
      pitch={{
        title: 'Almost back in.',
        body: 'Set a new password and your rooms, rating and practice history are right where you left them.',
      }}
      footer={
        <>
          Remembered it?{' '}
          <Link to="/login" className="font-semibold text-ink underline underline-offset-4">Log in</Link>
        </>
      }
    >
      <FormAlert>{error}</FormAlert>
      <FormAlert tone="success">{success}</FormAlert>

      {!tokenValid ? (
        <Link to="/forgot-password" className="btn btn-primary btn-lg w-full">
          Request a new reset link
        </Link>
      ) : (
        <form onSubmit={handlePasswordReset} className="space-y-5">
          <Field
            id="new-password"
            label="New password"
            type="password"
            value={form.newPassword}
            onChange={(e) => setForm((f) => ({ ...f, newPassword: e.target.value }))}
            autoComplete="new-password"
            required
            minLength={6}
            autoFocus
            hint="At least 6 characters."
          />
          <Field
            id="confirm-password"
            label="Confirm new password"
            type="password"
            value={form.confirmPassword}
            onChange={(e) => setForm((f) => ({ ...f, confirmPassword: e.target.value }))}
            autoComplete="new-password"
            required
            minLength={6}
          />
          <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full">
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />
                Resetting…
              </>
            ) : (
              'Reset password'
            )}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}
