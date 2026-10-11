import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

export default function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const { login } = useAuth()
  const nav = useNavigate()

  useEffect(() => {
    const handleOAuthCallback = async () => {
      const token = searchParams.get('token')
      const username = searchParams.get('username')
      const oauthSuccess = searchParams.get('oauth_success')
      const oauthError = searchParams.get('oauth_error')

      if (oauthError) {
        const errorMessages = {
          no_code: 'The provider did not send an authorization code. Try signing in again.',
          token_exchange_failed: 'We could not complete sign in with that provider. Try again.',
          no_email: 'The provider did not share an email address, which we need to create your account.',
          google_not_configured: 'Google sign in is not available right now. Use your username and password instead.',
          github_not_configured: 'GitHub sign in is not available right now. Use your username and password instead.',
          apple_not_configured: 'Apple sign in is not available right now. Use your username and password instead.',
        }

        const errorMsg = errorMessages[oauthError] || `Sign in failed (${oauthError}).`
        nav('/login', { state: { error: errorMsg } })
        return
      }

      if (oauthSuccess === 'true' && token && username) {
        try {
          localStorage.setItem('token', token)
          const { data: profile } = await api.get('/users/me')
          login({
            id: profile.id,
            username: profile.username,
            email: profile.email,
          }, token)
          nav('/home')
        } catch (err) {
          console.error('OAuth callback error:', err)
          nav('/login', { state: { error: 'We could not finish signing you in. Try again.' } })
        }
      }
    }

    handleOAuthCallback()
  }, [searchParams, login, nav])

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-5">
      <div role="status" className="flex items-center gap-4">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-line-strong border-t-ink" />
        <p className="text-lg font-semibold">Finishing sign in…</p>
      </div>
    </div>
  )
}
