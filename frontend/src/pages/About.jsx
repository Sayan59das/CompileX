import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { Avatar } from '../components/ui'

const HOW = [
  { title: 'Problems from a reviewed pool', text: 'Every question is generated offline, checked against a reference and a brute-force solution, and reviewed before it is served. You are not given a problem you have already seen while an unseen one exists.' },
  { title: 'You write only the logic', text: 'Each problem comes with typed starter code in Python, C++, Java, JavaScript and C. The function signature and the input/output harness are locked.' },
  { title: 'Graded on the server', text: 'Hidden tests never reach the browser. Submissions run in isolated Docker containers with time and memory limits.' },
  { title: 'Your complexity, read from your code', text: 'A cost analysis reads your solution and reports its time and space complexity, with a confidence level and a reason for each loop.' },
]

const STACK = [
  ['Frontend', 'React, Vite, Tailwind CSS, Three.js, Monaco editor, Socket.IO client'],
  ['Backend', 'FastAPI, SQLAlchemy, PostgreSQL, Redis, Socket.IO'],
  ['Code execution', 'Docker sandboxes per language'],
  ['Question pipeline', 'Python, run offline and reviewed by a person'],
  ['Hosting', 'Vercel and Render'],
]

const PEOPLE = [
  { name: 'Kabir', role: 'Co-creator, full-stack developer' },
  { name: 'Sayan', role: 'Co-creator, full-stack developer' },
]

export default function About() {
  const { user } = useAuth()
  return (
    <div className="app-shell relative z-10 min-h-screen text-white">
      <Navbar />
      <main className="relative mx-auto max-w-[1000px] px-5 pb-20 pt-32 md:px-8">
        <h1 className="font-display text-[clamp(2.4rem,5vw,3.6rem)] font-bold leading-tight tracking-tight">About CompileX</h1>
        <p className="mt-5 max-w-2xl text-[19px] leading-relaxed text-slate-300">
          CompileX is a competitive coding platform. You practise alone, take a short skill check to get a rating, then race other
          players live on the same problem, in a lobby, a 1v1 duel or a tournament.
        </p>

        <section className="mt-16" aria-labelledby="how">
          <h2 id="how" className="font-display text-[26px] font-bold tracking-tight">How it works</h2>
          <dl className="mt-6 grid gap-x-10 gap-y-8 md:grid-cols-2">
            {HOW.map((h) => (
              <div key={h.title} className="border-t border-white/10 pt-5">
                <dt className="text-[17px] font-semibold">{h.title}</dt>
                <dd className="mt-2 text-[15px] leading-relaxed text-slate-400">{h.text}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="mt-16" aria-labelledby="stack">
          <h2 id="stack" className="font-display text-[26px] font-bold tracking-tight">Built with</h2>
          <dl className="mt-6 divide-y divide-white/10 border-y border-white/10">
            {STACK.map(([k, v]) => (
              <div key={k} className="grid gap-1 py-4 sm:grid-cols-[200px_1fr]">
                <dt className="text-[15px] font-medium text-white">{k}</dt>
                <dd className="text-[15px] text-slate-400">{v}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="mt-16" aria-labelledby="people">
          <h2 id="people" className="font-display text-[26px] font-bold tracking-tight">Made by</h2>
          <ul className="mt-6 grid gap-4 sm:grid-cols-2">
            {PEOPLE.map((p) => (
              <li key={p.name} className="flex items-center gap-4 rounded-xl border border-white/10 bg-[#0A0A0A] px-5 py-4">
                <Avatar name={p.name} size={44} />
                <div>
                  <div className="text-[16px] font-semibold">{p.name}</div>
                  <div className="text-[14px] text-slate-400">{p.role}</div>
                </div>
              </li>
            ))}
          </ul>
        </section>

        <div className="mt-16 flex flex-col items-start gap-4 border-t border-white/10 pt-10 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-[18px] text-slate-300">Ready for your first match?</p>
          <Link to={user ? '/dashboard' : '/register'} className="btn btn-primary btn-lg">
            {user ? 'Go to dashboard' : 'Create account'}<ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  )
}
