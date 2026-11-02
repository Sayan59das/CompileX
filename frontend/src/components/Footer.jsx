import React from 'react'
import { Link } from 'react-router-dom'
import Logo, { Wordmark } from './Logo'

export default function Footer() {
  return (
    <footer className="relative z-10 border-t border-white/10 bg-ink">
      <div className="mx-auto max-w-[1280px] px-5 py-12 md:px-8">
        <div className="grid gap-10 md:grid-cols-12">
          <div className="md:col-span-5">
            <div className="flex items-center gap-3">
              <Logo size={42} />
              <Wordmark className="text-[28px]" />
            </div>
            <p className="mt-5 max-w-sm text-[18px] leading-relaxed text-slate-400">
              Live coding matches on problems nobody has seen. Python, C++, Java, JavaScript and C.
            </p>
          </div>
          <nav className="grid grid-cols-2 gap-8 text-[17px] md:col-span-7 md:grid-cols-3" aria-label="Footer">
            <div className="flex flex-col gap-3">
              <span className="text-[13px] font-semibold uppercase tracking-[0.12em] text-slate-500">Play</span>
              <Link to="/register" className="text-slate-300 hover:text-white">Create account</Link>
              <Link to="/login" className="text-slate-300 hover:text-white">Log in</Link>
              <Link to="/practice" className="text-slate-300 hover:text-white">Practice</Link>
            </div>
            <div className="flex flex-col gap-3">
              <span className="text-[13px] font-semibold uppercase tracking-[0.12em] text-slate-500">Project</span>
              <Link to="/about" className="text-slate-300 hover:text-white">About</Link>
              <a href="#" className="text-slate-300 hover:text-white">Privacy</a>
              <a href="#" className="text-slate-300 hover:text-white">Terms</a>
            </div>
          </nav>
        </div>
        <div className="mt-8 flex flex-col gap-2 border-t border-white/10 pt-6 text-[15px] text-slate-500 sm:flex-row sm:justify-between">
          <p>&copy; 2026 CompileX. All rights reserved.</p>
          <p>Built by Kabir &amp; Sayan</p>
        </div>
      </div>
    </footer>
  )
}
