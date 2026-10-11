import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ThemeToggle } from '../context/ThemeContext'
import Logo from './Logo'
import Icon from './Icons'

const LINKS = [
  { to: '/#how', label: 'How a match works' },
  { to: '/#modes', label: 'Game modes' },
  { to: '/#practice', label: 'Practice' },
  { to: '/about', label: 'About' },
]

/** Header for the public pages (landing, about). */
export default function Navbar() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-5 sm:px-8">
        <Link to="/" aria-label="CompileX home" onClick={() => setOpen(false)}>
          <Logo size={30} />
        </Link>

        <nav className="ml-4 hidden items-center gap-1 md:flex" aria-label="Main">
          {LINKS.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="rounded-md px-3 py-2 text-sm font-medium text-ink-2 transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          <ThemeToggle />
          {user ? (
            <Link to="/dashboard" className="btn btn-primary btn-sm">
              Open dashboard
            </Link>
          ) : (
            <>
              <Link to="/login" className="btn btn-quiet btn-sm hidden sm:inline-flex">
                Log in
              </Link>
              <Link to="/register" className="btn btn-primary btn-sm">
                Create account
              </Link>
            </>
          )}
          <button
            type="button"
            className="btn btn-quiet btn-icon md:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            <Icon name={open ? 'x' : 'menu'} />
          </button>
        </div>
      </div>

      {open && (
        <nav className="border-t border-line bg-paper px-5 py-3 md:hidden" aria-label="Mobile">
          {LINKS.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              onClick={() => setOpen(false)}
              className="block rounded-md px-2 py-3 text-base font-medium text-ink"
            >
              {l.label}
            </Link>
          ))}
          {!user && (
            <Link
              to="/login"
              onClick={() => setOpen(false)}
              className="block rounded-md px-2 py-3 text-base font-medium text-ink"
            >
              Log in
            </Link>
          )}
        </nav>
      )}
    </header>
  )
}
