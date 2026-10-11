import React, { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ThemeToggle } from '../context/ThemeContext'
import Logo from './Logo'
import Avatar from './Avatar'
import Icon from './Icons'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', match: ['/dashboard', '/profile'] },
  { to: '/practice', label: 'Practice', match: ['/practice'] },
  { to: '/tournaments', label: 'Tournaments', match: ['/tournaments', '/tournament'] },
  { to: '/history', label: 'History', match: ['/history'] },
]

function AccountMenu() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!user) return null

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex h-9 items-center gap-2 rounded-md pl-1 pr-2 transition-colors hover:bg-sunken"
      >
        <Avatar name={user.username} size={28} />
        <span className="hidden max-w-[120px] truncate text-sm font-semibold sm:block">{user.username}</span>
        <Icon name="chevron-down" size={14} className="text-ink-3" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-11 z-50 w-56 animate-fade-in rounded-lg border border-line bg-panel p-1.5 shadow-float"
        >
          <div className="px-3 py-2">
            <div className="truncate text-sm font-semibold">{user.username}</div>
            {user.email && <div className="truncate text-xs text-ink-3">{user.email}</div>}
          </div>
          <div className="my-1 h-px bg-line" />
          <button
            role="menuitem"
            type="button"
            onClick={() => { setOpen(false); logout(); nav('/login') }}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-ink-2 transition-colors hover:bg-sunken hover:text-ink"
          >
            <Icon name="logout" size={16} />
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

/** Header for signed-in pages: dashboard, practice, tournaments, history. */
export default function AppHeader({ children }) {
  const { user } = useAuth()
  const { pathname } = useLocation()

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-5 sm:px-8">
        <Link to="/" aria-label="CompileX home" className="shrink-0">
          <Logo size={28} />
        </Link>

        <nav className="no-scrollbar ml-2 flex items-center gap-0.5 overflow-x-auto" aria-label="Main">
          {NAV.map((item) => {
            const active = item.match.some((m) => pathname === m || pathname.startsWith(m + '/'))
            return (
              <Link
                key={item.to}
                to={item.to}
                aria-current={active ? 'page' : undefined}
                className={`relative whitespace-nowrap rounded-md px-3 py-2 text-sm font-semibold transition-colors ${
                  active
                    ? 'text-ink after:absolute after:inset-x-3 after:-bottom-[17px] after:h-0.5 after:bg-ink'
                    : 'text-ink-3 hover:text-ink'
                }`}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          {children}
          {user?.rating != null && (
            <div className="mr-1 hidden items-baseline gap-1.5 px-2 sm:flex" title="Your rating">
              <span className="numeral text-xl">{Math.round(user.rating)}</span>
              <span className="text-xs font-medium text-ink-3">rating</span>
            </div>
          )}
          <ThemeToggle />
          <AccountMenu />
        </div>
      </div>
    </header>
  )
}
