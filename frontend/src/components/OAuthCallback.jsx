import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import { oauthErrorMessage } from '../utils/oauthErrors'

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
        // Handle OAuth error
        const errorMsg = oauthErrorMessage(oauthError)
        nav('/login', { state: { error: errorMsg } })
        return
      }

      if (oauthSuccess === 'true' && token && username) {
        try {
          // Store token
          localStorage.setItem('token', token)
          
          // Get full user profile
          const { data: profile } = await api.get('/users/me')
          
          // Login user
          login({
            id: profile.id,
            username: profile.username,
            email: profile.email
          }, token)
          
          // Redirect to home
          nav('/home')
        } catch (err) {
          console.error('OAuth callback error:', err)
          nav('/login', { state: { error: 'Failed to complete OAuth login' } })
        }
      }
    }

    handleOAuthCallback()
  }, [searchParams, login, nav])

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-white text-lg">Completing sign in...</p>
      </div>
    </div>
  )
}
