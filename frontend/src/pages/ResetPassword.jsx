import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../services/api'
import { CheckCircle2 } from 'lucide-react'
import AuthLayout, { Field, FormError, SubmitButton } from '../components/AuthLayout'

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
    <AuthLayout
      title="Choose a new password"
      subtitle="Use at least 6 characters."
      footer={<>Back to <Link to="/login" className="font-medium text-arc hover:text-white">sign in</Link></>}
    >
      <FormError>{error}</FormError>
      {success && (
        <div role="status" className="flex items-start gap-2.5 rounded-lg border border-emerald-500/30 bg-emerald-500/[0.07] px-3.5 py-3 text-[14px] text-emerald-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{success}</span>
        </div>
      )}
      {tokenValid && !success && (
        <form onSubmit={handlePasswordReset} className="space-y-5">
          <Field id="new-password" label="New password" type="password" autoComplete="new-password" required
            value={form.newPassword} onChange={e => setForm(f => ({ ...f, newPassword: e.target.value }))} />
          <Field id="confirm-password" label="Confirm new password" type="password" autoComplete="new-password" required
            value={form.confirmPassword} onChange={e => setForm(f => ({ ...f, confirmPassword: e.target.value }))} />
          <SubmitButton loading={loading} loadingText="Saving">Save new password</SubmitButton>
        </form>
      )}
      {!tokenValid && (
        <Link to="/forgot-password" className="inline-flex rounded-lg border border-white/15 px-4 py-2.5 text-[14px] font-medium text-slate-200 transition-colors hover:border-white/30 hover:bg-[#141414]">
          Request a new reset code
        </Link>
      )}
    </AuthLayout>
  )
}
