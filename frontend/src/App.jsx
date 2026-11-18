import React, { Suspense, lazy, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import SmoothScroll from './components/SmoothScroll'
import { SceneBackdrop } from './components/CoderScene'
import { AuthProvider, useAuth } from './context/AuthContext'

// Each page is its own file that the browser downloads only when the page is opened, so the first visit loads a small
// start-up bundle instead of every page and library at once. The loaders are named so they can also be started early (see PREFETCH).
const loaders = {
  Login:             () => import('./pages/Login'),
  Register:          () => import('./pages/Register'),
  ForgotPassword:    () => import('./pages/ForgotPassword'),
  ResetPassword:     () => import('./pages/ResetPassword'),
  Landing:           () => import('./pages/Landing'),
  About:             () => import('./pages/About'),
  Lobby:             () => import('./pages/Lobby'),
  Game:              () => import('./pages/Game'),
  OfflinePractice:   () => import('./pages/OfflinePractice'),
  Profile:           () => import('./pages/Profile'),
  Tournaments:       () => import('./pages/Tournaments'),
  TournamentDetail:  () => import('./pages/TournamentDetail'),
  MatchHistory:      () => import('./pages/MatchHistory'),
  SkillAssessment:   () => import('./pages/SkillAssessment'),
}
const Login = lazy(loaders.Login)
const Register = lazy(loaders.Register)
const ForgotPassword = lazy(loaders.ForgotPassword)
const ResetPassword = lazy(loaders.ResetPassword)
const Landing = lazy(loaders.Landing)
const About = lazy(loaders.About)
const Lobby = lazy(loaders.Lobby)
const Game = lazy(loaders.Game)
const OfflinePractice = lazy(loaders.OfflinePractice)
const Profile = lazy(loaders.Profile)
const Tournaments = lazy(loaders.Tournaments)
const TournamentDetail = lazy(loaders.TournamentDetail)
const MatchHistory = lazy(loaders.MatchHistory)
const SkillAssessment = lazy(loaders.SkillAssessment)

// Pages a visitor is most likely to open next, fetched quietly once the current page has settled (never on a slow or
// data-saving connection), so clicking through feels instant.
const PREFETCH = {
  '/':          ['Login', 'Register', 'OfflinePractice', 'Profile'],
  '/home':      ['Login', 'Register', 'OfflinePractice', 'Profile'],
  '/login':     ['Register', 'Profile', 'SkillAssessment', 'OfflinePractice'],
  '/register':  ['Login', 'SkillAssessment'],
  '/skill-assessment': ['Profile', 'OfflinePractice'],
  '/dashboard': ['OfflinePractice', 'Tournaments', 'MatchHistory', 'Lobby'],
  '/profile':   ['OfflinePractice', 'Tournaments', 'MatchHistory', 'Lobby'],
  '/practice':  ['Profile', 'Lobby'],
}

function usePrefetch(pathname) {
  useEffect(() => {
    const names = PREFETCH[pathname]
    const net = navigator.connection
    if (!names || net?.saveData || /(^|-)2g$/.test(net?.effectiveType || '')) return undefined
    const run = () => names.forEach((n) => loaders[n]().catch(() => {}))
    if (typeof requestIdleCallback === 'function') {
      const id = requestIdleCallback(run, { timeout: 4000 })
      return () => cancelIdleCallback(id)
    }
    const id = setTimeout(run, 1500)
    return () => clearTimeout(id)
  }, [pathname])
}

// Shown for the instant a page's file is still arriving: the same black as the page, so nothing flashes.
const PageWait = <div style={{ minHeight: '100vh', background: 'var(--bg, #000)' }} aria-busy="true" />

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
  usePrefetch(pathname)
  return (
    <AuthProvider>
      <Chrome pathname={pathname} />
      <div key={pathname} className={pathname === '/' || pathname === '/home' ? undefined : 'route-fade'}>
      <Suspense fallback={PageWait}>
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
      </Suspense>
      </div>
    </AuthProvider>
  )
}