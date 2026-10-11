import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Logo from './Logo'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-[#05050A]/80 backdrop-blur-md border-b border-white/[0.05]' : 'bg-transparent border-b border-transparent'}`}>
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group cursor-pointer">
          <Logo size={40} className="transition-transform duration-300 group-hover:scale-105 text-blue-500" />
          <span className="text-xl font-mono font-bold text-white tracking-widest transition-all duration-300 group-hover:tracking-[0.15em] group-hover:text-blue-100">COMPILE.X</span>
        </Link>
        <nav className="hidden md:flex items-center gap-6 bg-[#101018]/60 backdrop-blur-md px-6 py-2 rounded-full border border-white/[0.05] shadow-lg">
          <Link to="/#features" className="text-sm font-mono text-slate-400 hover:text-white transition-colors duration-200">Features</Link>
          <Link to="/#modes" className="text-sm font-mono text-slate-400 hover:text-white transition-colors duration-200">Game Modes</Link>
          <Link to="/about" className="text-sm font-mono text-slate-400 hover:text-white transition-colors duration-200">About</Link>
        </nav>
        <div className="flex items-center gap-4">
          {user ? (
            <>
              <div className="hidden sm:flex items-center gap-2 px-4 py-1.5 bg-[#101018]/60 backdrop-blur-md border border-white/[0.05] rounded-full">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-sm text-white font-medium">{user.username}</span>
              </div>
              <Link to="/dashboard" className="text-sm font-medium text-slate-400 hover:text-white transition-colors duration-200">Dashboard</Link>
              <button onClick={() => { logout(); navigate('/login') }} className="text-sm font-medium text-slate-400 hover:text-white transition-colors duration-200">Sign out</button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-mono text-slate-400 hover:text-white transition-colors duration-200">Log In</Link>
              <Link to="/register" className="btn btn-primary rounded-full px-6 shadow-[0_0_15px_rgba(59,130,246,0.3)] hover:shadow-[0_0_25px_rgba(59,130,246,0.5)]">Get Started</Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
