import React from 'react'
import { Link } from 'react-router-dom'
import { Check, AlertCircle, Loader2 } from 'lucide-react'
import Logo, { Wordmark } from './Logo'
import CoderScene from './CoderScene'

// The sign-in, register and password screens share one frame: the product on the left, the form on the right.

const FACTS = [
  'Problems drawn fresh for every match',
  'Python, C++, Java, JavaScript and C',
  'Hidden tests, graded on the server',
]

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen bg-black text-white lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <aside className="relative hidden flex-col overflow-hidden border-r border-white/10 bg-[#070707] px-12 pb-10 pt-10 lg:flex">
        <Link to="/" className="flex items-center gap-2.5" aria-label="CompileX home">
          <Logo size={36} />
          <Wordmark className="text-[22px]" />
        </Link>
        <div className="mt-12 max-w-md">
          <p className="font-display text-[34px] font-bold leading-tight tracking-tight">
            Live coding matches against real rivals.
          </p>
          <ul className="mt-6 space-y-3">
            {FACTS.map((f) => (
              <li key={f} className="flex items-center gap-3 text-[16px] text-slate-300">
                <Check className="h-4 w-4 shrink-0 text-arc" strokeWidth={2.5} aria-hidden="true" />
                {f}
              </li>
            ))}
          </ul>
        </div>
        <div className="relative -mx-12 -mb-10 mt-2 min-h-0 flex-1">
          <CoderScene className="absolute inset-0" />
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[#070707] to-transparent" aria-hidden="true" />
        <p className="absolute bottom-10 left-12 text-[13px] text-slate-500">&copy; 2026 CompileX</p>
      </aside>

      <main className="flex items-center justify-center px-5 py-12 sm:px-10">
        <div className="w-full max-w-[400px] animate-fade-in">
          <Link to="/" className="mb-10 flex items-center gap-2.5 lg:hidden" aria-label="CompileX home">
            <Logo size={32} />
            <Wordmark className="text-[20px]" />
          </Link>
          <h1 className="font-display text-[28px] font-bold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-[15px] text-slate-400">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-8 border-t border-white/10 pt-6 text-[14px] text-slate-400">{footer}</div>}
        </div>
      </main>
    </div>
  )
}

export function Field({ label, id, aside, ...input }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <label htmlFor={id} className="text-[14px] font-medium text-slate-200">{label}</label>
        {aside}
      </div>
      <input
        id={id}
        className="block w-full rounded-lg border border-white/15 bg-[#0A0A0A] px-3.5 py-2.5 text-[15px] text-white outline-none transition-colors duration-150 placeholder:text-slate-600 hover:border-white/25 focus:border-arc focus:ring-2 focus:ring-arc/20"
        {...input}
      />
    </div>
  )
}

export function FormError({ children }) {
  if (!children) return null
  return (
    <div role="alert" className="mb-6 flex items-start gap-2.5 rounded-lg border border-red-500/30 bg-red-500/[0.07] px-3.5 py-3 text-[14px] text-red-300">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}

export function SubmitButton({ loading, children, loadingText }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="flex w-full items-center justify-center gap-2 rounded-lg bg-arc px-4 py-2.5 text-[15px] font-semibold text-black transition-colors duration-150 hover:bg-[#7AEBFF] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {loading ? loadingText : children}
    </button>
  )
}

const GoogleMark = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
)

const GithubMark = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M12 2C6.48 2 2 6.48 2 12.02c0 4.42 2.87 8.17 6.84 9.5.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.95 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.02A9.6 9.6 0 0 1 12 6.82c.85 0 1.71.11 2.51.34 1.91-1.29 2.75-1.02 2.75-1.02.55 1.38.2 2.4.1 2.65.64.7 1.03 1.59 1.03 2.68 0 3.85-2.34 4.7-4.57 4.94.36.31.68.92.68 1.85v2.75c0 .27.18.58.69.48A10.02 10.02 0 0 0 22 12.02C22 6.48 17.52 2 12 2z" />
  </svg>
)

export function OAuthButtons({ onClick }) {
  return (
    <>
      <div className="my-6 flex items-center gap-3 text-[13px] text-slate-500">
        <span className="h-px flex-1 bg-white/10" />or<span className="h-px flex-1 bg-white/10" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[['google', 'Google', GoogleMark], ['github', 'GitHub', GithubMark]].map(([id, label, Mark]) => (
          <button
            key={id}
            type="button"
            onClick={() => onClick(id)}
            className="flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-[#0A0A0A] px-3 py-2.5 text-[14px] font-medium text-slate-200 transition-colors duration-150 hover:border-white/30 hover:bg-[#141414]"
          >
            <Mark />{label}
          </button>
        ))}
      </div>
    </>
  )
}
