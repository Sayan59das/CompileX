import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { CheckCircle2 } from 'lucide-react'
import AuthLayout, { Field, FormError, SubmitButton } from '../components/AuthLayout'

export default function ForgotPassword() {
  const [step, setStep] = useState(1) // 1: Enter username, 2: Enter OTP and new password
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
      setError(err.response?.data?.detail || 'Failed to send OTP')
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifyOTP(e) {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/verify-otp-reset-password', {
        username,
        otp,
        new_password: newPassword
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to reset password'
      setError(errorMsg)
      
      // Extract remaining attempts from error message
      const match = errorMsg.match(/(\d+) attempts remaining/)
      if (match) {
        setAttemptsRemaining(parseInt(match[1]))
      }
    } finally {
      setLoading(false)
    }
  }

  const footer = <>Remember your password? <Link to="/login" className="font-medium text-arc hover:text-white">Sign in</Link></>

  if (success) {
    return (
      <AuthLayout title="Password changed" subtitle="Taking you to sign in." footer={footer}>
        <div role="status" className="flex items-start gap-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/[0.07] px-3.5 py-3 text-[14px] text-emerald-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>Your password has been reset. You can sign in with it now.</span>
        </div>
      </AuthLayout>
    )
  }

  if (step === 1) {
    return (
      <AuthLayout title="Reset your password" subtitle="Enter your username and we will email you a 6-digit code." footer={footer}>
        <FormError>{error}</FormError>
        <form onSubmit={handleRequestOTP} className="space-y-5">
          <Field id="username" label="Username" type="text" autoComplete="username" required
            value={username} onChange={e => setUsername(e.target.value)} />
          <SubmitButton loading={loading} loadingText="Sending code">Send code</SubmitButton>
        </form>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Enter your code" subtitle="Check the email on your account for the 6-digit code." footer={footer}>
      <FormError>{error}</FormError>
      <form onSubmit={handleVerifyOTP} className="space-y-5">
        <Field id="otp" label="6-digit code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} required
          aside={attemptsRemaining < 5 ? <span className="text-[13px] text-amber-300">{attemptsRemaining} attempts left</span> : null}
          value={otp} onChange={e => setOtp(e.target.value.replace(/\D/g, ''))} />
        <Field id="new-password" label="New password" type="password" autoComplete="new-password" required placeholder="At least 6 characters"
          value={newPassword} onChange={e => setNewPassword(e.target.value)} />
        <Field id="confirm-password" label="Confirm new password" type="password" autoComplete="new-password" required
          value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />
        <SubmitButton loading={loading} loadingText="Resetting password">Reset password</SubmitButton>
      </form>
      <button type="button" onClick={() => { setStep(1); setOtp(''); setError('') }} className="mt-4 text-[14px] text-slate-400 transition-colors hover:text-white">
        Use a different username
      </button>
    </AuthLayout>
  )
}
