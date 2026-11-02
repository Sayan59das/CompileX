import React from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import SmoothScroll from './components/SmoothScroll'
import { SceneBackdrop } from './components/CoderScene'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login    from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Landing  from './pages/Landing'
import HomeDashboard from './pages/HomeDashboard'
import About    from './pages/About'
import Lobby    from './pages/Lobby'
import Game     from './pages/Game'
import OfflinePractice from './pages/OfflinePractice'
import Profile from './pages/Profile'
import Tournaments from './pages/Tournaments'
import TournamentDetail from './pages/TournamentDetail'
import MatchHistory from './pages/MatchHistory'
import SkillAssessment from './pages/SkillAssessment'

function Protected({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  // Redirect to skill assessment if not yet completed
  if (!user.skill_quiz_completed && window.location.pathname !== '/skill-assessment') {
    return <Navigate to="/skill-assessment" replace />
  }
  return children
}

// The coder backdrop lives here, above the routes, so moving between these pages keeps the one WebGL scene running
// instead of building a new one every time.
const BACKDROP = /^\/(dashboard|profile|tournaments|tournament\/|history|lobby\/|about)/
// The landing page smooths its own scroll, and these are full-screen editors with their own scrolling panes.
const OWN_SCROLL = /^\/($|home$|game\/|practice|skill-assessment)/

function Chrome({ pathname }) {
  return (
    <>
      <SmoothScroll enabled={!OWN_SCROLL.test(pathname)} pathname={pathname} />
      {BACKDROP.test(pathname) && <SceneBackdrop />}
    </>
  )
}

export default function App() {
  const { pathname } = useLocation()
  return (
    <AuthProvider>
      <Chrome pathname={pathname} />
      <div key={pathname} className={pathname === '/' || pathname === '/home' ? undefined : 'route-fade'}>
      <Routes>
        <Route path="/login"    element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/" element={<Landing />} />
        <Route path="/home" element={<Landing />} />
        <Route path="/about" element={<About />} />
        <Route path="/skill-assessment" element={<SkillAssessment />} />
        <Route path="/dashboard" element={<Protected><Profile /></Protected>} />
        <Route path="/lobby/:code" element={<Protected><Lobby /></Protected>} />
        <Route path="/game/:code"  element={<Protected><Game /></Protected>} />
        <Route path="/practice"  element={<Protected><OfflinePractice /></Protected>} />
        <Route path="/profile"   element={<Protected><Profile /></Protected>} />
        <Route path="/history"   element={<Protected><MatchHistory /></Protected>} />
        <Route path="/tournaments" element={<Protected><Tournaments /></Protected>} />
        <Route path="/tournament/:code" element={<Protected><TournamentDetail /></Protected>} />
      </Routes>
      </div>
    </AuthProvider>
  )
}