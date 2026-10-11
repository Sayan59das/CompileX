import React from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import Avatar from '../components/Avatar'

const FEATURES = [
  { title: 'Live matches', desc: 'Rooms synchronise over WebSockets, so everyone sees the same problem, the same clock and the same standings.' },
  { title: 'Problems written for the room', desc: 'A custom transformer model trained on more than 2,000 LeetCode problems writes each question, with test cases.' },
  { title: 'Sandboxed execution', desc: 'Every submission runs in a Docker container with memory, CPU and time limits.' },
  { title: 'Three ways to compete', desc: 'Arena matches for up to 20 players, 1v1 duels, and bracket tournaments.' },
  { title: 'Feedback on your code', desc: 'The AI coach scores your logic, explains time and space complexity, and answers questions about your solution.' },
  { title: 'Sign in your way', desc: 'Username and password with email reset codes, or Google and GitHub.' },
]

const STACK = [
  { group: 'Frontend', items: [['React', 'UI library'], ['Vite', 'Build tool'], ['Socket.IO', 'Real-time communication'], ['Tailwind CSS', 'Styling']] },
  { group: 'Backend', items: [['FastAPI', 'Python web framework'], ['PostgreSQL', 'Database'], ['SQLAlchemy', 'ORM'], ['Redis', 'Caching']] },
  { group: 'AI', items: [['PyTorch', 'Deep learning'], ['Transformers', 'Language models'], ['Python', 'Language']] },
  { group: 'Infrastructure', items: [['Docker', 'Containers'], ['Vercel', 'Frontend hosting'], ['Render', 'Backend hosting'], ['GitHub', 'Version control']] },
]

const CREATORS = [
  {
    name: 'Kabir',
    role: 'Co-creator and full-stack developer',
    work: ['Backend architecture', 'AI model integration', 'Database design', 'API development'],
  },
  {
    name: 'Sayan',
    role: 'Co-creator and full-stack developer',
    work: ['Frontend development', 'Real-time features', 'UI and UX design', 'DevOps and deployment'],
  },
]

export default function About() {
  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <main>
        <section className="mx-auto max-w-6xl px-5 pb-16 pt-14 sm:px-8 lg:pb-24 lg:pt-20">
          <h1 className="display max-w-4xl text-[clamp(2.9rem,6.4vw,5.5rem)]">
            A coding platform built around the race.
          </h1>
          <p className="measure mt-7 text-lg text-ink-2 sm:text-xl">
            CompileX is a multiplayer coding platform. Players race on problems generated for the room, and an AI coach
            explains where a solution is wrong or slow.
          </p>
        </section>

        <section className="border-t border-line">
          <div className="mx-auto grid max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:py-24">
            <h2 className="display text-[clamp(2.2rem,4.4vw,3.5rem)]">What it does</h2>
            <dl className="grid gap-x-10 gap-y-8 sm:grid-cols-2">
              {FEATURES.map((f) => (
                <div key={f.title} className="border-t border-line pt-4">
                  <dt className="text-lg font-bold">{f.title}</dt>
                  <dd className="mt-1.5 text-ink-2">{f.desc}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="border-t border-line">
          <div className="mx-auto grid max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:py-24">
            <h2 className="display text-[clamp(2.2rem,4.4vw,3.5rem)]">What it is built with</h2>
            <div className="border-t border-line">
              {STACK.map((s) => (
                <div key={s.group} className="grid gap-3 border-b border-line py-5 sm:grid-cols-[9rem_1fr]">
                  <h3 className="font-bold">{s.group}</h3>
                  <ul className="grid grid-cols-2 gap-x-6 gap-y-3">
                    {s.items.map(([name, desc]) => (
                      <li key={name}>
                        <div className="font-semibold">{name}</div>
                        <div className="text-sm text-ink-3">{desc}</div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-t border-line">
          <div className="mx-auto grid max-w-6xl gap-10 px-5 py-16 sm:px-8 lg:grid-cols-[0.8fr_1.2fr] lg:py-24">
            <h2 className="display text-[clamp(2.2rem,4.4vw,3.5rem)]">Who made it</h2>
            <ul className="border-t border-line">
              {CREATORS.map((c) => (
                <li key={c.name} className="grid gap-4 border-b border-line py-6 sm:grid-cols-[auto_1fr_1fr] sm:items-start sm:gap-6">
                  <Avatar name={c.name} size={48} />
                  <div>
                    <h3 className="text-xl font-bold">{c.name}</h3>
                    <p className="text-ink-2">{c.role}</p>
                  </div>
                  <ul className="text-ink-2">
                    {c.work.map((w) => (
                      <li key={w} className="py-0.5">{w}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="bg-ink text-paper">
          <div className="mx-auto flex max-w-6xl flex-col items-start gap-8 px-5 py-16 sm:px-8 lg:flex-row lg:items-end lg:justify-between">
            <h2 className="display max-w-2xl text-[clamp(2.2rem,4.8vw,3.75rem)]">Ready for a match?</h2>
            <Link to="/register" className="btn btn-lg bg-paper text-ink hover:bg-paper/90">Create an account</Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
