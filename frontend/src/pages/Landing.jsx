import React, { useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import Scoreboard from '../components/Scoreboard'
import LearnMore from '../components/LearnMore'
import Icon from '../components/Icons'

const STEPS = [
  {
    title: 'Make a room or join one',
    body: 'The host picks the difficulty, topics, time limit and number of questions. Everyone else joins with the room code.',
  },
  {
    title: 'A new problem is written for the room',
    body: 'The generator writes a problem with hidden test cases and checks it against questions already used, so you do not get a repeat.',
  },
  {
    title: 'Everyone codes on the same clock',
    body: 'Write your solution in Python, C++, Java, JavaScript or C. Run it on the visible example, or on input of your own, as often as you like.',
  },
  {
    title: 'Submit and watch the standings move',
    body: 'Your code runs in a sandbox against every test case. Passing earns points, and the room sees the new standings straight away.',
  },
]

const MODES = [
  {
    icon: 'users',
    name: 'Arena match',
    body: 'One room, one set of problems, everyone on the same clock.',
    spec: '2 to 20 players',
    to: '/dashboard',
  },
  {
    icon: 'duel',
    name: '1v1 duel',
    body: 'Two players, the same problem, and whoever passes first leads.',
    spec: '2 players',
    to: '/dashboard',
  },
  {
    icon: 'bracket',
    name: 'Tournament',
    body: 'A bracket that knocks players out round by round. Each pairing plays its own match.',
    spec: 'Up to 128 players',
    to: '/tournaments',
  },
  {
    icon: 'target',
    name: 'Practice arena',
    body: 'Work alone on any topic and get feedback from an AI coach after each run.',
    spec: 'Solo',
    to: '/practice',
  },
]

const PRACTICE_POINTS = [
  {
    title: 'Problems on any topic',
    body: 'Type a topic, or upload a syllabus as a PDF, text file or image, and get questions drawn from it.',
  },
  {
    title: 'A coach that reads your code',
    body: 'After a run it scores your logic, points at what is failing, and answers follow-up questions about your solution.',
  },
  {
    title: 'Complexity, explained',
    body: 'See the best, average and worst case for time and space, and how your solution compares with common growth curves.',
  },
  {
    title: 'A starting rating that fits',
    body: 'Five adaptive questions set your rating, from Beginner to Master, so matchmaking starts from where you really are.',
  },
]

function EditorMock() {
  const kw = 'text-[#B79CFF]'
  const fn = 'text-[#8CC4FF]'
  const results = [
    { label: 'Case 1', note: '4 ms', pass: true },
    { label: 'Case 2', note: '3 ms', pass: true },
    { label: 'Case 3', note: 'hidden, 5 ms', pass: true },
    { label: 'Case 4', note: 'hidden', pass: false },
  ]
  return (
    <div className="slab overflow-hidden" data-theme="dark">
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
        <span className="font-mono text-sm text-ink-2">solution.py</span>
        <span className="chip">Python</span>
      </div>
      <pre className="overflow-x-auto px-4 py-4 font-mono text-[13.5px] leading-7 text-ink">
        <code>
          <span className={kw}>def</span> <span className={fn}>pair_with_sum</span>(nums, target):{'\n'}
          {'    '}seen = {'{}'}{'\n'}
          {'    '}<span className={kw}>for</span> i, x <span className={kw}>in</span> <span className={fn}>enumerate</span>(nums):{'\n'}
          {'        '}<span className={kw}>if</span> target - x <span className={kw}>in</span> seen:{'\n'}
          {'            '}<span className={kw}>return</span> [seen[target - x], i]{'\n'}
          {'        '}seen[x] = i{'\n'}
          {'    '}<span className={kw}>return</span> []{'\n'}
          {'\n'}
          <span className="text-ink-3"># pair_with_sum([2, 7, 11], 9) returns [0, 1]</span>
        </code>
      </pre>
      <ul className="border-t border-line">
        {results.map((r) => (
          <li key={r.label} className="flex items-center gap-3 border-b border-line px-4 py-2.5 text-sm last:border-b-0">
            <Icon
              name={r.pass ? 'check-circle' : 'x-circle'}
              size={16}
              className={r.pass ? 'text-grass-ink' : 'text-tomato-ink'}
            />
            <span className="font-semibold text-ink">{r.label}</span>
            <span className="text-ink-3">{r.note}</span>
            <span className={`ml-auto font-semibold ${r.pass ? 'text-grass-ink' : 'text-tomato-ink'}`}>
              {r.pass ? 'Passed' : 'Failed'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function ComplexityMock() {
  const rows = [
    ['Best', 'O(1)', 'O(1)'],
    ['Average', 'O(n)', 'O(n)'],
    ['Worst', 'O(n)', 'O(n)'],
  ]
  return (
    <div className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <span className="font-semibold">Complexity report</span>
        <span className="chip">Sample</span>
      </div>
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-line text-sm text-ink-3">
            <th className="px-5 py-2.5 font-medium">Case</th>
            <th className="px-5 py-2.5 font-medium">Time</th>
            <th className="px-5 py-2.5 font-medium">Space</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([c, t, s]) => (
            <tr key={c} className="border-b border-line last:border-b-0">
              <td className="px-5 py-3 text-ink-2">{c}</td>
              <td className="numeral px-5 py-3 text-2xl">{t}</td>
              <td className="numeral px-5 py-3 text-2xl">{s}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-start gap-3 border-t border-line bg-sunken px-5 py-4">
        <span className="dot mt-2" style={{ background: 'rgb(var(--grass))' }} />
        <p className="text-sm text-ink-2">
          <span className="font-semibold text-ink">Optimal for this problem.</span> One pass with a hash map avoids the
          nested loop, so time grows linearly with the input.
        </p>
      </div>
    </div>
  )
}

export default function Landing() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const { hash } = useLocation()

  // OAuth providers redirect back here with the session in the query string.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    const username = params.get('username')
    const oauthSuccess = params.get('oauth_success')
    const oauthError = params.get('oauth_error')

    if (oauthError) {
      console.error('OAuth error:', oauthError)
      window.history.replaceState({}, document.title, window.location.pathname)
      return
    }

    if (oauthSuccess === 'true' && token && username) {
      localStorage.setItem('token', token)
      login({ username }, token)
      window.history.replaceState({}, document.title, window.location.pathname)
      navigate('/home')
    }
  }, [login, navigate])

  // In-page links (/#how) are router links, so scroll to the target ourselves.
  useEffect(() => {
    if (!hash) return
    const el = document.getElementById(hash.slice(1))
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [hash])

  const primaryTo = user ? '/dashboard' : '/register'

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <main>
        {/* Hero */}
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-12 sm:px-8 lg:grid-cols-[1.02fr_0.98fr] lg:gap-14 lg:pb-28 lg:pt-20">
          <div className="min-w-0">
            <h1 className="display text-[clamp(2.9rem,6.4vw,5.5rem)]">
              Same problem for everyone.
              <br />
              Fastest correct code wins.
            </h1>
            <p className="measure mt-7 text-lg text-ink-2 sm:text-xl">
              CompileX writes a problem nobody in the room has seen, starts the clock for all of you, and runs your code
              against hidden tests. The standings change the moment someone passes.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link to={primaryTo} className="btn btn-primary btn-lg">
                {user ? 'Open dashboard' : 'Create a free account'}
              </Link>
              <Link to="/#how" className="btn btn-secondary btn-lg">
                See how a match works
              </Link>
            </div>
            <p className="mt-6 text-sm text-ink-3">
              Write in Python, C++, Java, JavaScript or C. Rooms hold up to 20 players.
            </p>
          </div>

          <Scoreboard />
        </section>

        {/* How a match runs */}
        <section id="how" className="scroll-mt-16 border-t border-line">
          <div className="mx-auto grid max-w-6xl gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1fr_1fr] lg:gap-16 lg:py-28">
            <div className="min-w-0">
              <h2 className="display text-[clamp(2.2rem,4.4vw,3.5rem)]">How a match runs</h2>
              <ol className="mt-10 space-y-8">
                {STEPS.map((s, i) => (
                  <li key={s.title} className="grid grid-cols-[3.25rem_1fr] gap-4">
                    <span className="numeral text-5xl text-ink-3">{i + 1}</span>
                    <div>
                      <h3 className="text-xl font-bold">{s.title}</h3>
                      <p className="measure mt-1.5 text-ink-2">{s.body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
            <div className="min-w-0 lg:sticky lg:top-24 lg:self-start">
              <EditorMock />
              <p className="mt-3 text-sm text-ink-3">
                Visible cases show their input and output. Hidden cases only tell you whether you passed.
              </p>
            </div>
          </div>
        </section>

        {/* Game modes */}
        <section id="modes" className="scroll-mt-16 border-t border-line">
          <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 lg:py-28">
            <h2 className="display max-w-3xl text-[clamp(2.2rem,4.4vw,3.5rem)]">Pick how you want to compete</h2>
            <ul className="mt-12 border-t border-line">
              {MODES.map((m) => (
                <li key={m.name} className="border-b border-line">
                  <Link
                    to={m.to}
                    className="grid grid-cols-[2.75rem_1fr_auto] items-center gap-x-5 gap-y-1 py-6 transition-colors hover:bg-sunken sm:grid-cols-[2.75rem_14rem_1fr_9rem_1.5rem] sm:px-3"
                  >
                    <span className="flex h-11 w-11 items-center justify-center rounded-md border border-line-strong bg-panel">
                      <Icon name={m.icon} size={20} />
                    </span>
                    <span className="stretch-narrow text-2xl font-extrabold tracking-tight">{m.name}</span>
                    <span className="col-start-2 text-ink-2 sm:col-start-auto">{m.body}</span>
                    <span className="col-start-2 text-sm font-semibold text-ink sm:col-start-auto sm:text-right">
                      {m.spec}
                    </span>
                    <Icon name="chevron-right" size={18} className="hidden text-ink-3 sm:block" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Practice */}
        <section id="practice" className="scroll-mt-16 border-t border-line">
          <div className="mx-auto grid max-w-6xl items-start gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1fr_0.9fr] lg:gap-16 lg:py-28">
            <div className="min-w-0">
              <h2 className="display text-[clamp(2.2rem,4.4vw,3.5rem)]">Practice with feedback that reads your code</h2>
              <dl className="mt-10 space-y-7">
                {PRACTICE_POINTS.map((p) => (
                  <div key={p.title}>
                    <dt className="text-lg font-bold">{p.title}</dt>
                    <dd className="measure mt-1 text-ink-2">{p.body}</dd>
                  </div>
                ))}
              </dl>
              <Link to={user ? '/practice' : '/register'} className="btn btn-secondary mt-10">
                {user ? 'Open the practice arena' : 'Create an account to practice'}
              </Link>
            </div>
            <div className="min-w-0"><ComplexityMock /></div>
          </div>
        </section>

        {/* Explainer videos */}
        <section id="learn" className="scroll-mt-16 border-t border-line">
          <div className="mx-auto max-w-6xl px-5 py-20 sm:px-8 lg:py-28">
            <LearnMore />
          </div>
        </section>

        {/* Closing call to action */}
        <section className="bg-ink text-paper">
          <div className="mx-auto flex max-w-6xl flex-col items-start gap-8 px-5 py-16 sm:px-8 lg:flex-row lg:items-end lg:justify-between lg:py-20">
            <h2 className="display max-w-2xl text-[clamp(2.2rem,4.8vw,3.75rem)]">
              Your first match takes a minute to set up.
            </h2>
            <div className="flex flex-wrap gap-3">
              <Link to={primaryTo} className="btn btn-lg bg-paper text-ink hover:bg-paper/90">
                {user ? 'Open dashboard' : 'Create an account'}
              </Link>
              <Link
                to={user ? '/practice' : '/login'}
                className="btn btn-lg border border-paper/40 text-paper hover:bg-paper/10"
              >
                {user ? 'Practice first' : 'Log in'}
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
