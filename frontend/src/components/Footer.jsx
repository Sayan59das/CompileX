import React from 'react'
import { Link } from 'react-router-dom'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-5 py-12 sm:px-8 md:flex-row md:items-start md:justify-between">
        <div className="max-w-xs">
          <Logo size={28} />
          <p className="mt-3 text-sm text-ink-2">
            Live coding matches on problems nobody has seen before.
          </p>
        </div>

        <nav className="flex gap-10 text-sm" aria-label="Footer">
          <ul className="space-y-2.5">
            <li><Link to="/#how" className="text-ink-2 hover:text-ink">How a match works</Link></li>
            <li><Link to="/#modes" className="text-ink-2 hover:text-ink">Game modes</Link></li>
            <li><Link to="/#practice" className="text-ink-2 hover:text-ink">Practice</Link></li>
          </ul>
          <ul className="space-y-2.5">
            <li><Link to="/about" className="text-ink-2 hover:text-ink">About</Link></li>
            <li>
              <a
                href="https://github.com/Sayan59das/CompileX"
                target="_blank"
                rel="noreferrer"
                className="text-ink-2 hover:text-ink"
              >
                Source on GitHub
              </a>
            </li>
            <li><Link to="/login" className="text-ink-2 hover:text-ink">Log in</Link></li>
          </ul>
        </nav>
      </div>
      <div className="border-t border-line">
        <p className="mx-auto max-w-6xl px-5 py-5 text-sm text-ink-3 sm:px-8">
          © 2026 CompileX. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
