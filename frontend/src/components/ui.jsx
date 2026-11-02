import React from 'react'
import { Loader2 } from 'lucide-react'

// The small kit every signed-in screen is built from. One look: solid surfaces, 1px borders, 8px corners, one accent.

const cx = (...c) => c.filter(Boolean).join(' ')

export function PageHeader({ title, description, actions }) {
  return (
    <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-[28px] font-bold tracking-tight md:text-[32px]">{title}</h1>
        {description && <p className="mt-1.5 text-[15px] text-slate-400">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2.5">{actions}</div>}
    </header>
  )
}

export function Panel({ title, action, children, className = '', bodyClassName = 'p-5' }) {
  return (
    <section className={cx('rounded-xl border border-white/10 bg-[#0A0A0A]', className)}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-3.5">
          {title && <h2 className="text-[15px] font-semibold text-white">{title}</h2>}
          {action}
        </div>
      )}
      <div className={bodyClassName}>{children}</div>
    </section>
  )
}

const VARIANTS = {
  primary: 'bg-arc text-black hover:bg-[#7AEBFF]',
  secondary: 'border border-white/15 bg-[#0F0F0F] text-slate-100 hover:border-white/30 hover:bg-[#161616]',
  ghost: 'text-slate-300 hover:bg-white/[0.06] hover:text-white',
  danger: 'border border-red-500/40 text-red-300 hover:bg-red-500/10',
  success: 'bg-emerald-400 text-black hover:bg-emerald-300',
}
const SIZES = { sm: 'h-8 px-3 text-[13px]', md: 'h-10 px-4 text-[14px]', lg: 'h-11 px-5 text-[15px]' }

export function Button({ variant = 'primary', size = 'md', loading = false, icon: Icon, className = '', children, ...rest }) {
  return (
    <button
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant], SIZES[size], className,
      )}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : Icon && <Icon className="h-4 w-4" aria-hidden="true" />}
      {children}
    </button>
  )
}

export function Label({ htmlFor, children, hint }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 flex items-baseline justify-between text-[13px] font-medium text-slate-300">
      <span>{children}</span>
      {hint && <span className="font-normal text-slate-500">{hint}</span>}
    </label>
  )
}

export const inputClass =
  'block w-full rounded-lg border border-white/15 bg-black px-3 py-2 text-[14px] text-white outline-none transition-colors duration-150 placeholder:text-slate-600 hover:border-white/25 focus:border-arc focus:ring-2 focus:ring-arc/20'

export function Input({ className = '', ...rest }) {
  return <input className={cx(inputClass, className)} {...rest} />
}

export function Toggle({ checked, onChange, label, description, id }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <label htmlFor={id} className="text-[14px] font-medium text-white">{label}</label>
        {description && <p className="text-[13px] text-slate-500">{description}</p>}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cx('relative h-6 w-11 shrink-0 rounded-full transition-colors duration-200', checked ? 'bg-arc' : 'bg-[#262626]')}
      >
        <span className={cx('absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform duration-200', checked ? 'translate-x-[22px]' : 'translate-x-0.5')} />
      </button>
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div role="tablist" className="flex border-b border-white/10">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          type="button"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={cx(
            '-mb-px border-b-2 px-4 py-3 text-[14px] font-medium transition-colors duration-150',
            value === t.value ? 'border-arc text-white' : 'border-transparent text-slate-400 hover:text-white',
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

export function Segmented({ options, value, onChange }) {
  return (
    <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={cx(
            'rounded-lg border px-3 py-2.5 text-left transition-colors duration-150',
            value === o.value ? 'border-arc bg-arc/[0.08]' : 'border-white/15 bg-black hover:border-white/30',
          )}
        >
          <span className="block text-[14px] font-medium text-white">{o.label}</span>
          {o.description && <span className="block text-[12px] text-slate-400">{o.description}</span>}
        </button>
      ))}
    </div>
  )
}

const BADGE = {
  neutral: 'border-white/15 text-slate-300',
  accent: 'border-arc/40 text-arc',
  success: 'border-emerald-400/40 text-emerald-300',
  warning: 'border-amber-400/40 text-amber-300',
  danger: 'border-red-400/40 text-red-300',
  violet: 'border-violet-400/40 text-violet-300',
}
export function Badge({ tone = 'neutral', children, className = '' }) {
  return <span className={cx('inline-flex items-center rounded-md border px-2 py-0.5 text-[12px] font-medium', BADGE[tone], className)}>{children}</span>
}

export function Alert({ tone = 'danger', children }) {
  const t = tone === 'danger' ? 'border-red-500/30 bg-red-500/[0.07] text-red-300' : 'border-emerald-500/30 bg-emerald-500/[0.07] text-emerald-300'
  return <div role="alert" className={cx('rounded-lg border px-3.5 py-2.5 text-[14px]', t)}>{children}</div>
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      {Icon && <Icon className="mb-3 h-6 w-6 text-slate-500" aria-hidden="true" />}
      <p className="text-[15px] font-medium text-white">{title}</p>
      {children && <p className="mt-1 max-w-sm text-[14px] text-slate-400">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function Avatar({ name = '?', size = 32 }) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full border border-white/15 bg-[#161616] font-semibold text-slate-200"
      style={{ width: size, height: size, fontSize: size * 0.42 }}
      aria-hidden="true"
    >
      {String(name).charAt(0).toUpperCase()}
    </span>
  )
}

export function Spinner({ label = 'Loading' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-[14px] text-slate-400" role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />{label}
    </div>
  )
}
