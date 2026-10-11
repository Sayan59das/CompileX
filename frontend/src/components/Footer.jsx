import React from 'react'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="py-12 border-t border-white/[0.05] bg-[#05050A]">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <Logo size={32} className="text-blue-500" />
          <span className="text-lg font-mono font-bold text-white tracking-widest">
            COMPILE.<span className="text-cyan-400">X</span>
          </span>
        </div>
        <div className="flex items-center gap-8 text-sm font-medium text-slate-500">
          <a href="/about" className="hover:text-cyan-400 transition-colors">About</a>
          <a href="https://github.com/Sayan59das/CompileX" target="_blank" rel="noreferrer" className="hover:text-cyan-400 transition-colors">GitHub</a>
          <a href="/login" className="hover:text-cyan-400 transition-colors">Log in</a>
        </div>
        <p className="text-sm font-medium text-slate-500">&copy; 2026 CompileX. All rights reserved.</p>
      </div>
    </footer>
  )
}
