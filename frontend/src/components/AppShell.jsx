import React from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Logo, { Wordmark } from './Logo'
import { Avatar } from './ui'

// The frame of every signed-in screen: one top bar with the same links everywhere, and a centred content column.

const LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/practice', label: 'Practice' },
  { to: '/tournaments', label: 'Tournaments' },
  { to: '/history', label: 'History' },
]

function NavItem({ to, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative whitespace-nowrap px-1 py-4 text-[14px] font-medium transition-colors duration-150 ${isActive ? 'text-white' : 'text-slate-400 hover:text-white'}`
      }
    >
      {({ isActive }) => (
        <>
          {label}
          {isActive && <span className="absolute inset-x-0 -bottom-px h-0.5 bg-arc" aria-hidden="true" />}
        </>
      )}
    </NavLink>
  )
}

export default function AppShell({ children, width = 'max-w-[1200px]' }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="app-shell relative z-10 min-h-screen text-white">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-black/95">
        <div className="mx-auto flex max-w-[1200px] items-center gap-8 px-5 md:px-8">
          <Link to="/dashboard" className="flex items-center gap-2 py-3" aria-label="CompileX dashboard">
            <Logo size={28} />
            <Wordmark className="hidden text-[18px] sm:inline-flex" />
          </Link>
          <nav className="hidden items-center gap-6 md:flex" aria-label="Main">
            {LINKS.map((l) => <NavItem key={l.to} {...l} />)}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {user?.rating != null && (
              <span className="hidden rounded-md border border-white/10 px-2 py-1 font-mono text-[12px] text-slate-300 sm:inline" title="Your rating">
                {user.rating}
              </span>
            )}
            <span className="flex items-center gap-2 text-[14px] text-slate-200">
              <Avatar name={user?.username} size={28} />
              <span className="hidden max-w-[140px] truncate sm:inline">{user?.username}</span>
            </span>
            <button
              type="button"
              onClick={() => { logout(); navigate('/login') }}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
        <nav className="no-scrollbar flex gap-5 overflow-x-auto border-t border-white/10 px-5 md:hidden" aria-label="Main">
          {LINKS.map((l) => <NavItem key={l.to} {...l} />)}
        </nav>
      </header>
      <main className={`relative mx-auto ${width} px-5 py-8 md:px-8 md:py-10`}>{children}</main>
    </div>
  )
}
