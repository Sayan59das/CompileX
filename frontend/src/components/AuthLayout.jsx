import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import Logo from './Logo'
import Icon from './Icons'
import Scoreboard from './Scoreboard'
import { ThemeToggle } from '../context/ThemeContext'

/**
 * Two-panel layout for sign in, sign up and password reset. The left panel is
 * always dark and carries the scoreboard; the form sits on the page theme.
 */
export default function AuthLayout({ title, subtitle, pitch, children, footer }) {
  return (
    <div className="grid min-h-screen bg-paper lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <aside
        data-theme="dark"
        className="hidden flex-col justify-between bg-paper p-12 text-ink lg:flex xl:p-16"
      >
        <Link to="/" aria-label="CompileX home">
          <Logo size={32} />
        </Link>

        <div>
          <h2 className="display max-w-md text-5xl xl:text-6xl">{pitch.title}</h2>
          <p className="mt-5 max-w-sm text-lg text-ink-2">{pitch.body}</p>
          <Scoreboard autoplay={false} className="mt-10 max-w-md" />
        </div>

        <p className="text-sm text-ink-3">© 2026 CompileX. All rights reserved.</p>
      </aside>

      <main className="relative flex flex-col px-5 py-8 sm:px-10">
        <div className="flex items-center justify-between lg:justify-end">
          <Link to="/" aria-label="CompileX home" className="lg:hidden">
            <Logo size={28} />
          </Link>
          <ThemeToggle />
        </div>

        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <h1 className="stretch-narrow text-4xl font-extrabold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-ink-2">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <p className="mt-8 text-sm text-ink-2">{footer}</p>}
        </div>
      </main>
    </div>
  )
}

/** Text input with a persistent label. Password fields get a show/hide toggle. */
export function Field({ id, label, type = 'text', hint, aside, optional, ...rest }) {
  const [shown, setShown] = useState(false)
  const isPassword = type === 'password'
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-medium">
          {label}
          {optional && <span className="ml-1.5 font-normal text-ink-3">optional</span>}
        </label>
        {aside}
      </div>
      <div className="relative">
        <input
          id={id}
          type={isPassword && shown ? 'text' : type}
          className={`field ${isPassword ? 'pr-11' : ''}`}
          {...rest}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShown((s) => !s)}
            className="absolute right-1 top-1 flex h-9 w-9 items-center justify-center rounded text-ink-3 hover:text-ink"
            aria-label={shown ? 'Hide password' : 'Show password'}
          >
            <Icon name={shown ? 'eye-off' : 'eye'} size={18} />
          </button>
        )}
      </div>
      {hint && <p className="hint">{hint}</p>}
    </div>
  )
}

export function FormAlert({ children, tone = 'error' }) {
  if (!children) return null
  const tones = {
    error: { box: 'border-tomato-ink/40 bg-tomato/10', icon: 'alert', color: 'text-tomato-ink' },
    success: { box: 'border-grass-ink/40 bg-grass/10', icon: 'check-circle', color: 'text-grass-ink' },
    info: { box: 'border-sky-ink/40 bg-sky/10', icon: 'info', color: 'text-sky-ink' },
  }
  const t = tones[tone]
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`mb-6 flex items-start gap-3 rounded-md border p-3.5 text-sm ${t.box}`}>
      <Icon name={t.icon} size={18} className={`mt-px ${t.color}`} />
      <div className="text-ink">{children}</div>
    </div>
  )
}

export function Divider({ children }) {
  return (
    <div className="my-6 flex items-center gap-4 text-sm text-ink-3">
      <span className="h-px flex-1 bg-line" />
      {children}
      <span className="h-px flex-1 bg-line" />
    </div>
  )
}
