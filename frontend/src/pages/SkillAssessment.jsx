import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useEditorTheme, ThemeToggle } from '../context/ThemeContext'
import api from '../services/api'
import Editor from '@monaco-editor/react'
import Logo from '../components/Logo'
import Icon from '../components/Icons'
import ProblemStatement from '../components/ProblemStatement'
import { Spinner } from '../components/Analysis'
import { registerEditorThemes, EDITOR_FONT } from '../utils/monacoTheme'
import { parseTestCases } from '../utils/problem'

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const TOTAL_QUESTIONS = 5

const SKILL_DIMENSIONS = [
  { key: 'logic', label: 'Logic', desc: 'Basic reasoning and conditionals' },
  { key: 'strings', label: 'Strings', desc: 'String manipulation and parsing' },
  { key: 'problem_solving', label: 'Problem solving', desc: 'Hash maps and frequency counting' },
  { key: 'algorithms', label: 'Algorithms', desc: 'Sorting, searching and two pointers' },
  { key: 'advanced', label: 'Advanced', desc: 'Dynamic programming, recursion and optimisation' },
]

const DIFF_COLOR = { easy: 'grass', medium: 'sun', hard: 'tomato' }
const DIFF_LABEL = { easy: 'Easy', medium: 'Medium', hard: 'Hard' }

const TIER_CONFIG = {
  Beginner: { color: 'sky', desc: 'You are at the start, and there is a solid foundation to build on.' },
  Intermediate: { color: 'grass', desc: 'Your fundamentals are solid and you are ready for real challenges.' },
  Advanced: { color: 'violet', desc: 'You solve problems well and are ready for complex algorithms.' },
  Expert: { color: 'tangerine', desc: 'You are comfortable with advanced data structures.' },
  Master: { color: 'tomato', desc: 'Top of the scale: you compete at a very high level.' },
}

const LANGUAGES = [
  { value: 'python', label: 'Python', monaco: 'python' },
  { value: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { value: 'cpp', label: 'C++', monaco: 'cpp' },
  { value: 'java', label: 'Java', monaco: 'java' },
]

const fill = (name) => `rgb(var(--${name}))`

// ─────────────────────────────────────────────────────────────────────────────
// Per-question countdown
// ─────────────────────────────────────────────────────────────────────────────
function QuestionTimer({ seconds, onExpire, paused }) {
  const [remaining, setRemaining] = useState(seconds)
  const ref = useRef(null)

  useEffect(() => { setRemaining(seconds) }, [seconds])

  useEffect(() => {
    if (paused) { clearInterval(ref.current); return }
    ref.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) { clearInterval(ref.current); onExpire(); return 0 }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(ref.current)
  }, [seconds, paused, onExpire])

  const pct = (remaining / seconds) * 100
  const urgent = remaining <= seconds * 0.25
  const mins = Math.floor(remaining / 60)
  const secs = remaining % 60

  return (
    <div className="flex items-center gap-3" role="timer" aria-label={`${mins} minutes ${secs} seconds left`}>
      <span className="block h-1.5 w-24 overflow-hidden rounded-full bg-line">
        <span className={`block h-full ${urgent ? 'bg-tomato' : 'bg-ink'}`} style={{ width: `${pct}%`, transition: 'width 1s linear' }} />
      </span>
      <span className={`numeral w-16 text-right text-2xl ${urgent ? 'text-tomato-ink' : ''}`}>
        {mins}:{String(secs).padStart(2, '0')}
      </span>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Skill radar (SVG)
// ─────────────────────────────────────────────────────────────────────────────
function SkillRadar({ scores }) {
  const dims = SKILL_DIMENSIONS
  const n = dims.length, cx = 150, cy = 140, r = 96

  const pts = dims.map((d, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2
    const val = Math.min(1, (scores[d.key] || 0) / 100)
    return {
      x: cx + r * val * Math.cos(angle), y: cy + r * val * Math.sin(angle),
      lx: cx + (r + 24) * Math.cos(angle), ly: cy + (r + 20) * Math.sin(angle),
    }
  })

  return (
    <svg viewBox="0 0 300 280" className="mx-auto block w-full max-w-xs" role="img" aria-label="Skill profile across five areas">
      {[0.25, 0.5, 0.75, 1].map((ring) => (
        <polygon
          key={ring}
          points={dims.map((_, i) => {
            const a = (2 * Math.PI * i) / n - Math.PI / 2
            return `${cx + r * ring * Math.cos(a)},${cy + r * ring * Math.sin(a)}`
          }).join(' ')}
          fill="none"
          stroke="rgb(var(--line-strong))"
          strokeWidth="1"
        />
      ))}
      {dims.map((_, i) => {
        const a = (2 * Math.PI * i) / n - Math.PI / 2
        return <line key={i} x1={cx} y1={cy} x2={cx + r * Math.cos(a)} y2={cy + r * Math.sin(a)} stroke="rgb(var(--line))" />
      })}
      <polygon points={pts.map((p) => `${p.x},${p.y}`).join(' ')} fill="rgb(var(--sky) / 0.25)" stroke="rgb(var(--ink))" strokeWidth="2" />
      {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="4" fill="rgb(var(--ink))" />)}
      {pts.map((p, i) => (
        <text key={i} x={p.lx} y={p.ly} textAnchor="middle" dominantBaseline="middle" fontSize="11" fontWeight="600" fill="rgb(var(--ink-2))">
          {dims[i].label}
        </text>
      ))}
    </svg>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Page chrome shared by the non-quiz screens
// ─────────────────────────────────────────────────────────────────────────────
function Shell({ children, wide = false }) {
  return (
    <div className="min-h-screen bg-paper">
      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
        <Logo size={28} />
        <ThemeToggle />
      </header>
      <main className={`mx-auto px-5 pb-20 sm:px-8 ${wide ? 'max-w-5xl' : 'max-w-3xl'}`}>{children}</main>
    </div>
  )
}

function LoadingQuestion({ slot }) {
  const dim = SKILL_DIMENSIONS[slot] || SKILL_DIMENSIONS[0]
  return (
    <Shell>
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center" role="status">
        <Spinner className="!h-8 !w-8" />
        <p className="mt-6 text-2xl font-bold">Writing question {slot + 1} of {TOTAL_QUESTIONS}</p>
        <p className="mt-2 text-ink-2">This one tests <span className="font-semibold text-ink">{dim.label.toLowerCase()}</span>. It is generated for you, so it takes a few seconds.</p>
        <div className="mt-6 flex gap-2">
          {Array.from({ length: TOTAL_QUESTIONS }).map((_, i) => (
            <span key={i} className={`h-2.5 w-2.5 rounded-full ${i < slot ? 'bg-ink' : i === slot ? 'ring-2 ring-ink ring-offset-2 ring-offset-paper bg-ink' : 'bg-line-strong'}`} />
          ))}
        </div>
      </div>
    </Shell>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Intro
// ─────────────────────────────────────────────────────────────────────────────
function IntroScreen({ onStart, onSkip }) {
  return (
    <Shell>
      <h1 className="display mt-8 text-[clamp(2.6rem,6vw,4.5rem)]">Find your starting rating</h1>
      <p className="measure mt-6 text-lg text-ink-2">
        Five questions, written for you, that get harder as you do well. Your code is actually run against tests, and the
        result sets your rating, so matchmaking starts from where you really are.
      </p>

      <dl className="mt-8 flex flex-wrap gap-x-10 gap-y-4">
        {[['5', 'questions'], ['About 15', 'minutes'], ['Real', 'code execution'], ['Adaptive', 'difficulty']].map(([v, l]) => (
          <div key={l}>
            <dd className="numeral text-3xl">{v}</dd>
            <dt className="text-sm text-ink-3">{l}</dt>
          </div>
        ))}
      </dl>

      <section className="mt-12">
        <h2 className="border-b border-line pb-3 text-xl font-bold">What the five questions cover</h2>
        <ol>
          {SKILL_DIMENSIONS.map((d, i) => (
            <li key={d.key} className="grid grid-cols-[2rem_9rem_1fr] items-baseline gap-3 border-b border-line py-3.5">
              <span className="numeral text-2xl text-ink-3">{i + 1}</span>
              <span className="font-semibold">{d.label}</span>
              <span className="text-ink-2">{d.desc}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-12">
        <h2 className="text-xl font-bold">Where you could land</h2>
        <ul className="mt-4 grid gap-2 sm:grid-cols-5">
          {Object.entries(TIER_CONFIG).map(([name, cfg]) => (
            <li key={name} className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2.5 text-sm font-semibold">
              <span className="dot" style={{ background: fill(cfg.color) }} />
              {name}
            </li>
          ))}
        </ul>
      </section>

      <div className="mt-12 flex flex-wrap items-center gap-4">
        <button onClick={onStart} className="btn btn-primary btn-lg">Start the assessment</button>
        <button onClick={onSkip} className="btn btn-quiet">Skip and use the default rating (1000, Intermediate)</button>
      </div>
    </Shell>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Result
// ─────────────────────────────────────────────────────────────────────────────
function ResultScreen({ rating, tier, questionResults, onContinue }) {
  const cfg = TIER_CONFIG[tier?.name] || TIER_CONFIG.Beginner

  const totalPts = questionResults.reduce((s, r) => s + (r.pointsEarned || 0), 0)
  const maxPts = questionResults.reduce((s, r) => s + (r.maxPoints || 300), 0)
  const accuracy = maxPts > 0 ? Math.round((totalPts / maxPts) * 100) : 0
  const solved = questionResults.filter((r) => r.passed).length

  const skillScores = {}
  questionResults.forEach((r) => {
    const dim = r.skillDimension || 'logic'
    const score = r.totalTests > 0 ? Math.round((r.passedTests / r.totalTests) * 100) : 0
    skillScores[dim] = Math.max(skillScores[dim] || 0, score)
  })

  return (
    <Shell wide>
      <p className="mt-6 text-ink-2">Assessment complete</p>
      <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2">
        <h1 className="display text-[clamp(3.5rem,10vw,7rem)]">{tier?.name}</h1>
        <span className="mt-2 h-10 w-10 rounded-full" style={{ background: fill(cfg.color) }} aria-hidden="true" />
      </div>
      <p className="measure mt-3 text-lg text-ink-2">{cfg.desc}</p>

      <dl className="panel mt-10 grid grid-cols-2 divide-x divide-y divide-line sm:grid-cols-4 sm:divide-y-0">
        {[
          ['Starting rating', rating],
          ['Questions solved', `${solved} of ${TOTAL_QUESTIONS}`],
          ['Points', `${totalPts} of ${maxPts}`],
          ['Accuracy', `${accuracy}%`],
        ].map(([k, v]) => (
          <div key={k} className="px-5 py-5">
            <dd className="numeral text-4xl">{v}</dd>
            <dt className="mt-2 text-sm text-ink-3">{k}</dt>
          </div>
        ))}
      </dl>

      <div className="mt-10 grid gap-8 lg:grid-cols-2">
        <section className="panel p-6">
          <h2 className="font-bold">Skill profile</h2>
          <p className="mb-2 text-sm text-ink-3">Based on the tests your code passed.</p>
          <SkillRadar scores={skillScores} />
        </section>

        <section className="panel">
          <h2 className="border-b border-line px-6 py-4 font-bold">Question by question</h2>
          <ul className="divide-y divide-line">
            {questionResults.map((r, i) => {
              const pct = r.totalTests > 0 ? Math.round((r.passedTests / r.totalTests) * 100) : 0
              const dim = SKILL_DIMENSIONS.find((d) => d.key === r.skillDimension) || SKILL_DIMENSIONS[0]
              const status = r.passed ? 'grass' : r.passedTests > 0 ? 'sun' : 'tomato'
              return (
                <li key={i} className="px-6 py-3.5">
                  <div className="flex items-center gap-3">
                    <span className="dot" style={{ background: fill(status) }} />
                    <span className="min-w-0 flex-1 truncate font-semibold">{r.title || `Question ${i + 1}`}</span>
                    <span className="chip">{DIFF_LABEL[r.difficulty] || 'Easy'}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-3 pl-5">
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: fill(DIFF_COLOR[r.difficulty] || 'grass') }} />
                    </div>
                    <span className="tnum text-xs text-ink-3">{r.passedTests}/{r.totalTests} tests, {r.pointsEarned} pts</span>
                  </div>
                  <div className="mt-1 pl-5 text-xs text-ink-3">{dim.label}{r.timeTaken ? `, ${r.timeTaken}s` : ''}</div>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      <section className="mt-10">
        <h2 className="border-b border-line pb-3 text-xl font-bold">What happens now</h2>
        <dl className="grid gap-x-10 sm:grid-cols-2">
          {[
            ['Practice that fits', 'Questions are matched to your level and your weaker topics.'],
            ['A rating that moves', 'Your rating changes after every practice session and match.'],
            ['Fair matchmaking', 'You are paired with players at a similar rating.'],
            ['Calibration over time', 'The system keeps learning how strong you are in each area.'],
          ].map(([k, v]) => (
            <div key={k} className="border-b border-line py-4">
              <dt className="font-semibold">{k}</dt>
              <dd className="text-ink-2">{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      <button onClick={onContinue} className="btn btn-primary btn-lg mt-10">Start coding as {tier?.name}</button>
    </Shell>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function SkillAssessment() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const editorTheme = useEditorTheme()

  // phase: intro | loading | quiz | running | submitting | result
  const [phase, setPhase] = useState('intro')
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState('')

  // Current question state
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [currentSlot, setCurrentSlot] = useState(0)
  const [currentDiff, setCurrentDiff] = useState('easy')
  const [timerKey, setTimerKey] = useState(0)
  const [startTime, setStartTime] = useState(null)
  const [timeExpired, setTimeExpired] = useState(false)

  // Execution state
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)
  const [execError, setExecError] = useState('')

  // Results accumulation
  const [questionResults, setQuestionResults] = useState([])
  const [usedTitles, setUsedTitles] = useState([])

  // Final results
  const [finalRating, setFinalRating] = useState(null)
  const [finalTier, setFinalTier] = useState(null)
  const [finalTopicScores, setFinalTopicScores] = useState({})

  const editorRef = useRef(null)

  useEffect(() => {
    if (user?.skill_quiz_completed) navigate('/home')
  }, [user, navigate])

  // When language changes, reset to starter code for current question
  useEffect(() => {
    if (currentQuestion?.starter_code) {
      try {
        const sc = typeof currentQuestion.starter_code === 'string'
          ? JSON.parse(currentQuestion.starter_code)
          : currentQuestion.starter_code
        setCode(sc[language] || sc.python || '')
      } catch { setCode('') }
    }
  }, [language, currentQuestion])

  // ── Load a question from the AI ──────────────────────────────────────────
  async function loadQuestion(slot, diffOverride, prevResults) {
    setPhase('loading')
    setRunResult(null)
    setExecError('')
    setTimeExpired(false)

    try {
      const { data } = await api.post('/skill-assessment/generate-question', {
        slot,
        difficulty_override: diffOverride || null,
        exclude_titles: [...usedTitles, ...(prevResults || []).map((r) => r.title).filter(Boolean)],
      })

      setCurrentQuestion(data)
      setCurrentDiff(data.difficulty || diffOverride || 'easy')

      try {
        const sc = typeof data.starter_code === 'string'
          ? JSON.parse(data.starter_code)
          : (data.starter_code || {})
        setCode(sc[language] || sc.python || `# Write your solution here\n`)
      } catch { setCode(`# Write your solution here\n`) }

      setUsedTitles((prev) => [...prev, data.title].filter(Boolean))
      setStartTime(Date.now())
      setTimerKey((k) => k + 1)
      setPhase('quiz')
    } catch (err) {
      setExecError(err.response?.data?.detail || 'Could not generate the question. Try again.')
      setPhase('quiz')
    }
  }

  function startAssessment() {
    setCurrentSlot(0)
    setQuestionResults([])
    setUsedTitles([])
    loadQuestion(0, 'easy', [])
  }

  // ── Timer expired ────────────────────────────────────────────────────────
  const handleTimerExpire = useCallback(() => {
    setTimeExpired(true)
    setTimeout(() => submitQuestion(true), 2500)
  }, [currentQuestion, code, language, currentSlot, currentDiff, questionResults])

  // ── Run tests (preview: first 2 test cases) ──────────────────────────────
  async function runPreview() {
    if (!currentQuestion || running) return
    setRunning(true)
    setRunResult(null)
    setExecError('')
    try {
      const tcs = parseTestCases(currentQuestion.test_cases).slice(0, 2)
      const results = []
      for (const tc of tcs) {
        const { data } = await api.post('/execute', {
          code, language,
          inputs: [tc.input ?? tc.stdin ?? ''],
        })
        const out = (data.results?.[0]?.output || '').trim()
        const exp = (tc.expected_output ?? tc.output ?? '').trim()
        results.push({ input: tc.input ?? tc.stdin ?? '', expected: exp, output: out, passed: out === exp })
      }
      setRunResult({ preview: true, results, passedTests: results.filter((r) => r.passed).length, totalTests: results.length })
    } catch (err) {
      setExecError(err.response?.data?.detail || 'Execution failed')
    } finally { setRunning(false) }
  }

  // ── Submit question (run all test cases) ─────────────────────────────────
  async function submitQuestion(fromTimer = false) {
    if (!currentQuestion || running) return
    setRunning(true)
    setExecError('')
    try {
      const tcs = parseTestCases(currentQuestion.test_cases)
      const results = []
      for (const tc of tcs) {
        const { data } = await api.post('/execute', {
          code, language,
          inputs: [tc.input ?? tc.stdin ?? ''],
        })
        const out = (data.results?.[0]?.output || '').trim()
        const exp = (tc.expected_output ?? tc.output ?? '').trim()
        results.push({ input: tc.input ?? tc.stdin ?? '', expected: exp, output: out, passed: out === exp })
      }

      const passedTests = results.filter((r) => r.passed).length
      const totalTests = results.length
      const passed = passedTests === totalTests
      const partial = passedTests > 0 && !passed
      const maxPoints = currentSlot === 4 ? 500 : currentSlot === 3 ? 400 : currentSlot === 2 ? 300 : 200
      const pointsEarned = passed ? maxPoints : partial ? Math.round(maxPoints * (passedTests / totalTests) * 0.7) : 0
      const timeTaken = fromTimer ? null : Math.round((Date.now() - startTime) / 1000)

      const result = {
        slot: currentSlot,
        title: currentQuestion.title,
        difficulty: currentDiff,
        skillDimension: currentQuestion.skill_dimension || SKILL_DIMENSIONS[currentSlot]?.key || 'logic',
        passed, partial, passedTests, totalTests,
        pointsEarned, maxPoints, timeTaken,
        timedOut: fromTimer,
      }

      const newResults = [...questionResults, result]
      setQuestionResults(newResults)
      setRunResult({ preview: false, results, passed, passedTests, totalTests })

      // Adaptive difficulty for next question
      let nextDiff = currentDiff
      if (passed && currentDiff === 'easy') nextDiff = 'medium'
      else if (passed && currentDiff === 'medium') nextDiff = 'hard'
      else if (!passed && !partial && currentDiff === 'hard') nextDiff = 'medium'
      else if (!passed && !partial && currentDiff === 'medium') nextDiff = 'easy'

      // Move to next question after 2.5s
      setTimeout(() => {
        const nextSlot = currentSlot + 1
        if (nextSlot >= TOTAL_QUESTIONS) {
          finishAssessment(newResults)
        } else {
          setCurrentSlot(nextSlot)
          loadQuestion(nextSlot, nextDiff, newResults)
        }
      }, 2500)
    } catch (err) {
      setExecError(err.response?.data?.detail || 'Submission failed')
    } finally { setRunning(false) }
  }

  // ── Finish and submit to backend ─────────────────────────────────────────
  async function finishAssessment(results) {
    setPhase('submitting')
    try {
      const payload = results.map((r) => ({
        difficulty: r.difficulty,
        solved: r.passed,
        time_taken_seconds: r.timeTaken || 9999,
        points_earned: r.pointsEarned,
        topic: r.skillDimension,
        passed_tests: r.passedTests,
        total_tests: r.totalTests,
      }))
      const { data } = await api.post('/skill-assessment', { results: payload })
      setFinalRating(data.rating)
      setFinalTier(data.tier)
      setFinalTopicScores(data.topic_scores || {})
      const meRes = await api.get('/users/me')
      login(meRes.data, localStorage.getItem('token'))
      setPhase('result')
    } catch (err) {
      setExecError('Could not save your results. Try again.')
      setPhase('quiz')
    }
  }

  async function handleSkip() {
    setPhase('submitting')
    try {
      const { data } = await api.post('/skill-assessment', { results: [] })
      setFinalRating(data.rating)
      setFinalTier(data.tier)
      const meRes = await api.get('/users/me')
      login(meRes.data, localStorage.getItem('token'))
      setPhase('result')
    } catch { navigate('/home') }
  }

  // ── Render phases ─────────────────────────────────────────────────────────
  if (phase === 'intro') return <IntroScreen onStart={startAssessment} onSkip={handleSkip} />

  if (phase === 'loading') return <LoadingQuestion slot={currentSlot} />

  if (phase === 'submitting') return (
    <Shell>
      <div className="flex min-h-[60vh] flex-col items-center justify-center text-center" role="status">
        <Spinner className="!h-8 !w-8" />
        <p className="mt-6 text-2xl font-bold">Working out your rating</p>
        <p className="mt-2 text-ink-2">Scoring your answers across all five areas.</p>
      </div>
    </Shell>
  )

  if (phase === 'result') return (
    <ResultScreen rating={finalRating} tier={finalTier} topicScores={finalTopicScores}
      questionResults={questionResults} onContinue={() => navigate('/home')} />
  )

  if (!currentQuestion && phase === 'quiz') return (
    <Shell>
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
        {execError && <p role="alert" className="font-medium text-tomato-ink">{execError}</p>}
        <button onClick={() => loadQuestion(currentSlot, currentDiff, questionResults)} className="btn btn-primary">Try again</button>
      </div>
    </Shell>
  )

  // ── Quiz screen ───────────────────────────────────────────────────────────
  const dim = SKILL_DIMENSIONS[currentSlot] || SKILL_DIMENSIONS[0]
  const timeLimit = currentDiff === 'hard' ? 600 : currentDiff === 'medium' ? 420 : 300
  const maxPoints = currentSlot === 4 ? 500 : currentSlot === 3 ? 400 : currentSlot === 2 ? 300 : 200

  return (
    <div className="flex h-screen flex-col bg-paper">
      <header className="flex h-14 shrink-0 items-center gap-4 border-b border-line px-4">
        <Logo size={24} />
        <span className="hidden text-sm text-ink-2 md:inline">Skill assessment, {dim.label.toLowerCase()}</span>

        <ol className="mx-auto flex items-center gap-2" aria-label={`Question ${currentSlot + 1} of ${TOTAL_QUESTIONS}`}>
          {Array.from({ length: TOTAL_QUESTIONS }).map((_, i) => {
            const r = questionResults[i]
            const done = i < questionResults.length
            const color = done ? (r?.passed ? 'grass' : r?.partial ? 'sun' : 'tomato') : null
            return (
              <li
                key={i}
                className={`h-3.5 w-3.5 rounded-full border-2 ${i === currentSlot && !done ? 'border-ink bg-panel' : done ? 'border-transparent' : 'border-line-strong'}`}
                style={done ? { background: fill(color) } : undefined}
              />
            )
          })}
        </ol>

        <div className="seg" role="group" aria-label="Language">
          {LANGUAGES.map((l) => (
            <button key={l.value} aria-pressed={language === l.value} onClick={() => setLanguage(l.value)}>{l.label}</button>
          ))}
        </div>
        <ThemeToggle />
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Problem */}
        <aside className="w-[420px] shrink-0 overflow-y-auto border-r border-line p-6">
          <div className="mb-5 flex items-center justify-between">
            <span className="chip">Question {currentSlot + 1} of {TOTAL_QUESTIONS}, {maxPoints} points</span>
            <QuestionTimer key={timerKey} seconds={timeLimit} onExpire={handleTimerExpire} paused={running} />
          </div>

          {timeExpired && (
            <p role="alert" className="mb-4 flex items-start gap-2 rounded-md border border-tomato-ink/40 bg-tomato/10 p-3 text-sm font-medium">
              <Icon name="clock" size={16} className="mt-0.5 text-tomato-ink" />
              Time is up. Submitting the code you have.
            </p>
          )}

          <ProblemStatement question={{ ...currentQuestion, difficulty: currentDiff }} exampleCount={2} />

          {currentQuestion?.constraints && (
            <section className="mt-6">
              <h3 className="mb-2 text-sm font-bold">Constraints</h3>
              <p className="whitespace-pre-line text-sm leading-6 text-ink-2">{currentQuestion.constraints}</p>
            </section>
          )}

          {questionResults.length > 0 && (
            <section className="mt-8 border-t border-line pt-5">
              <h3 className="mb-2 text-sm font-bold">Earlier questions</h3>
              <ul className="space-y-1.5">
                {questionResults.map((r, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <span className="dot" style={{ background: fill(r.passed ? 'grass' : r.partial ? 'sun' : 'tomato') }} />
                    <span className="flex-1 truncate text-ink-2">{r.title}</span>
                    <span className="tnum text-ink-3">{r.pointsEarned} pts</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>

        {/* Editor and output */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1">
            <Editor
              height="100%"
              language={LANGUAGES.find((l) => l.value === language)?.monaco || 'python'}
              value={code}
              onChange={(v) => setCode(v || '')}
              beforeMount={registerEditorThemes}
              onMount={(e) => { editorRef.current = e }}
              theme={editorTheme}
              options={{
                fontSize: 14, minimap: { enabled: false },
                scrollBeyondLastLine: false, padding: { top: 16 },
                fontFamily: EDITOR_FONT,
                lineNumbers: 'on', renderLineHighlight: 'line',
              }}
            />
          </div>

          <div className="flex h-60 shrink-0 flex-col border-t border-line bg-panel">
            <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
              <div className="min-w-0 text-sm font-semibold">
                {execError && <span className="text-tomato-ink">{execError}</span>}
                {runResult && !running && (
                  <span className={runResult.passed ? 'text-grass-ink' : runResult.passedTests > 0 ? 'text-sun-ink' : 'text-tomato-ink'}>
                    {runResult.passed ? 'All tests passed' : `${runResult.passedTests} of ${runResult.totalTests} tests passed`}
                    {runResult.preview && <span className="ml-1.5 font-normal text-ink-3">(first two examples)</span>}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <button onClick={runPreview} disabled={running} className="btn btn-secondary btn-sm">
                  {running && !runResult ? <Spinner /> : <Icon name="play" size={12} />}
                  Run examples
                </button>
                <button onClick={() => submitQuestion(false)} disabled={running} className="btn btn-primary btn-sm">
                  {running ? <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-paper/30 border-t-paper" /> : <Icon name="check" size={14} strokeWidth={2.4} />}
                  Submit answer
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-4">
              {!runResult && !running && (
                <p className="py-6 text-center text-sm text-ink-3">Run examples to try your code on the first two cases, or submit to run every case.</p>
              )}
              {running && (
                <div className="flex items-center justify-center gap-3 py-6 text-sm text-ink-2" role="status">
                  <Spinner /> Running your code…
                </div>
              )}
              {runResult && !running && (
                <ul className="space-y-2">
                  {runResult.results.map((r, i) => (
                    <li key={i} className={`rounded-md border p-3 font-mono text-xs ${r.passed ? 'border-grass-ink/30 bg-grass/5' : 'border-tomato-ink/30 bg-tomato/5'}`}>
                      <div className="flex items-center gap-2 font-sans text-sm font-semibold">
                        <Icon name={r.passed ? 'check-circle' : 'x-circle'} size={16} className={r.passed ? 'text-grass-ink' : 'text-tomato-ink'} />
                        Test {i + 1}
                      </div>
                      {!r.passed && (
                        <div className="mt-2 space-y-0.5 pl-6 text-ink-2">
                          <div>Expected <span className="text-grass-ink">{r.expected}</span></div>
                          <div>Got <span className="text-tomato-ink">{r.output || '(no output)'}</span></div>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
