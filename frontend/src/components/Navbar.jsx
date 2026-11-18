import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Logo, { Wordmark } from './Logo'

const LINKS = [
  { id: 'match', label: 'A match' },
  { id: 'modes', label: 'Modes' },
]

const linkClass = 'text-[16px] font-medium text-slate-300 transition-colors duration-200 hover:text-white'

function Item({ l, onHome, close }) {
  return onHome
    ? <a href={`#${l.id}`} onClick={close} className={linkClass}>{l.label}</a>
    : <Link to={`/#${l.id}`} className={linkClass}>{l.label}</Link>
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const onHome = pathname === '/' || pathname === '/home'
  const [solid, setSolid] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => { setOpen(false) }, [pathname])

  const close = () => setOpen(false)

  return (
    <header className={`fixed inset-x-0 top-0 z-50 transition-[background-color,border-color] duration-300 ${solid || open ? 'border-b border-white/10 bg-ink/95' : 'border-b border-transparent'}`}>
      <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-3 px-5 py-4 md:px-8">
        <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="CompileX home">
          <Logo size={40} className="h-9 w-9 sm:h-10 sm:w-10" />
          <Wordmark className="text-[22px] sm:text-[25px]" />
        </Link>

        <nav className="hidden items-center gap-8 lg:flex" aria-label="Sections">
          {LINKS.map(l => <Item key={l.id} l={l} onHome={onHome} close={close} />)}
          <Link to="/about" className={linkClass}>About</Link>
        </nav>

        <div className="flex shrink-0 items-center gap-2.5 sm:gap-3">
          {user ? (
            <>
              <span className="hidden items-center gap-2 text-[16px] font-medium text-slate-200 sm:flex">
                <span className="h-2 w-2 rounded-full bg-pass" />{user.username}
              </span>
              <Link to="/dashboard" className="btn btn-secondary nav-cta">Dashboard</Link>
              <button onClick={() => { logout(); navigate('/login') }} className="hidden text-[16px] font-medium text-slate-400 hover:text-white sm:block">Sign out</button>
            </>
          ) : (
            <>
              <Link to="/login" className="hidden text-[16px] font-medium text-slate-300 hover:text-white sm:block">Log in</Link>
              <Link to="/register" className="btn btn-primary nav-cta">Get started</Link>
            </>
          )}
          <button
            type="button"
            className="flex h-9 w-9 flex-col items-center justify-center gap-[5px] rounded-lg border border-white/15 lg:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen(o => !o)}
          >
            <span className={`h-[2px] w-4 bg-white transition-transform duration-300 ${open ? 'translate-y-[7px] rotate-45' : ''}`} />
            <span className={`h-[2px] w-4 bg-white transition-opacity duration-200 ${open ? 'opacity-0' : ''}`} />
            <span className={`h-[2px] w-4 bg-white transition-transform duration-300 ${open ? '-translate-y-[7px] -rotate-45' : ''}`} />
          </button>
        </div>
      </div>

      {open && (
        <nav className="border-t border-white/10 bg-ink px-5 pb-6 pt-2 lg:hidden" aria-label="Menu">
          {LINKS.map(l => (
            <div key={l.id} className="border-b border-white/5 py-3.5 text-[20px]"><Item l={l} onHome={onHome} close={close} /></div>
          ))}
          <div className="border-b border-white/5 py-3.5 text-[20px]"><Link to="/about" className={linkClass}>About</Link></div>
          {!user && <div className="py-3.5 text-[20px]"><Link to="/login" className={linkClass}>Log in</Link></div>}
          {user && <button onClick={() => { logout(); navigate('/login') }} className="py-3.5 text-left text-[20px] text-slate-300">Sign out</button>}
        </nav>
      )}
    </header>
  )
}
