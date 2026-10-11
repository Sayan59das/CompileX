import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import AuthLayout, { Field, FormAlert } from '../components/AuthLayout'
import Icon from '../components/Icons'

export default function ForgotPassword() {
  const [step, setStep] = useState(1) // 1: enter username, 2: enter code and new password
  const [username, setUsername] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [attemptsRemaining, setAttemptsRemaining] = useState(5)
  const navigate = useNavigate()

  async function handleRequestOTP(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await api.post('/auth/forgot-password-otp', { username })
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send the code')
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifyOTP(e) {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('The two passwords do not match.')
      return
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/verify-otp-reset-password', {
        username,
        otp,
        new_password: newPassword,
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to reset password'
      setError(errorMsg)

      const match = errorMsg.match(/(\d+) attempts remaining/)
      if (match) setAttemptsRemaining(parseInt(match[1]))
    } finally {
      setLoading(false)
    }
  }

  const spinner = <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />

  return (
    <AuthLayout
      title={success ? 'Password updated' : step === 1 ? 'Reset your password' : 'Enter the code we emailed you'}
      subtitle={
        success
          ? 'Taking you back to the log in page.'
          : step === 1
            ? 'Enter your username and we will email a 6-digit code to the address on your account.'
            : 'The code expires in 10 minutes. Check your spam folder if it has not arrived.'
      }
      pitch={{
        title: 'Locked out? It happens.',
        body: 'Your rating and match history are tied to your username, so nothing is lost while you reset.',
      }}
      footer={
        <>
          Remembered it?{' '}
          <Link to="/login" className="font-semibold text-ink underline underline-offset-4">Log in</Link>
        </>
      }
    >
      <FormAlert>{error}</FormAlert>

      {success ? (
        <FormAlert tone="success">Your password has been changed.</FormAlert>
      ) : step === 1 ? (
        <form onSubmit={handleRequestOTP} className="space-y-5">
          <Field
            id="username"
            label="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            autoFocus
          />
          <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full">
            {loading ? <>{spinner} Sending code…</> : 'Email me a code'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleVerifyOTP} className="space-y-5">
          <div>
            <label htmlFor="otp" className="mb-1.5 block text-sm font-medium">6-digit code</label>
            <input
              id="otp"
              className="field numeral h-14 text-center text-3xl tracking-[0.35em]"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="000000"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              required
              maxLength={6}
              autoFocus
            />
            {attemptsRemaining < 5 && (
              <p className="mt-1.5 text-sm font-medium text-tangerine-ink">{attemptsRemaining} attempts remaining</p>
            )}
          </div>
          <Field
            id="new-password"
            label="New password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={6}
            hint="At least 6 characters."
          />
          <Field
            id="confirm-password"
            label="Confirm new password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={6}
          />
          <button type="submit" disabled={loading} className="btn btn-primary btn-lg w-full">
            {loading ? <>{spinner} Resetting…</> : 'Reset password'}
          </button>
          <button
            type="button"
            onClick={() => { setStep(1); setOtp(''); setError('') }}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-2 hover:text-ink"
          >
            <Icon name="arrow-left" size={14} />
            Use a different username
          </button>
        </form>
      )}
    </AuthLayout>
  )
}
