import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import Editor from '@monaco-editor/react'
import { attachProtectedRegion } from '../utils/protectedRegion'
import { Bot, Brain, Crown, Flame, Gem, Laptop, Leaf, Lightbulb, Puzzle, RefreshCw, Settings2, Sprout, Target, TrendingUp, Trophy, Type, Zap } from 'lucide-react'

// Renders an icon component, or plain text, at the size of the surrounding text.
const Ico = ({ of, className = 'inline-block h-[1em] w-[1em] align-[-0.125em]' }) =>
  of == null ? null : typeof of === 'string' ? of : React.createElement(of, { className, 'aria-hidden': true })


// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const TOTAL_QUESTIONS = 5

const SKILL_DIMENSIONS = [
  { key: 'logic',           label: 'Logic',           icon: Puzzle, desc: 'Basic reasoning & conditionals' },
  { key: 'strings',         label: 'Strings',         icon: Type, desc: 'String manipulation & parsing' },
  { key: 'problem_solving', label: 'Problem Solving', icon: Lightbulb, desc: 'Hash maps, frequency counting' },
  { key: 'algorithms',      label: 'Algorithms',      icon: Settings2,  desc: 'Sorting, searching, two-pointers' },
  { key: 'advanced',        label: 'Advanced',        icon: Brain, desc: 'DP, recursion, optimization' },
]

const DIFF_STYLE = {
  easy:   { label: 'Easy',   bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', bar: '#10b981', dot: 'bg-emerald-400' },
  medium: { label: 'Medium', bg: 'bg-amber-500/10',   border: 'border-amber-500/30',   text: 'text-amber-400',   bar: '#f59e0b', dot: 'bg-amber-400'   },
  hard:   { label: 'Hard',   bg: 'bg-rose-500/10',    border: 'border-rose-500/30',    text: 'text-rose-400',    bar: '#ef4444', dot: 'bg-rose-400'    },
}

const TIER_CONFIG = {
  Beginner:     { icon: Sprout, color: '#6b7280', glow: '#6b728040', grad: 'from-gray-700 to-gray-800',       desc: 'Just getting started — great foundation ahead!' },
  Intermediate: { icon: Leaf, color: '#10b981', glow: '#10b98140', grad: 'from-emerald-600 to-teal-700',    desc: 'Solid fundamentals — ready for real challenges!' },
  Advanced:     { icon: Flame, color: '#3B8CFF', glow: '#3b82f640', grad: 'from-blue-600 to-indigo-700',     desc: 'Strong problem-solver — tackling complex algorithms!' },
  Expert:       { icon: Gem, color: '#3B8CFF', glow: '#3b82f640', grad: 'from-blue-600 to-purple-700',   desc: 'Elite coder — mastering advanced data structures!' },
  Master:       { icon: Crown, color: '#f59e0b', glow: '#f59e0b40', grad: 'from-amber-500 to-orange-600',    desc: 'Top-tier competitive programmer — legendary!' },
}

// The starter code a question comes with for one language (what the editor is loaded with, and what it locks against)
function starterFor(question, language) {
  if (!question?.starter_code) return ''
  try {
    const sc = typeof question.starter_code === 'string' ? JSON.parse(question.starter_code) : question.starter_code
    return sc[language] || sc.python || ''
  } catch { return '' }
}

// A graded answer from the server, in the shape the page renders
function fromServerResult(r) {
  return {
    slot: r.slot, title: r.title, difficulty: r.difficulty, skillDimension: r.skill_dimension,
    passed: r.passed, partial: r.partial, passedTests: r.passed_tests, totalTests: r.total_tests,
    pointsEarned: r.points_earned, maxPoints: r.max_points, timeTaken: r.time_taken_seconds, timedOut: r.timed_out,
  }
}

// Per-test results from the server (the Run and Submit panels)
function fromServerTests(tests) {
  return (tests || []).map(t => ({
    input: t.input, expected: t.expected, output: t.output || t.error || '', passed: t.passed,
  }))
}

const LANGUAGES = [
  { value: 'python',     label: 'Python',     monaco: 'python'     },
  { value: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { value: 'cpp',        label: 'C++',        monaco: 'cpp'        },
  { value: 'java',       label: 'Java',       monaco: 'java'       },
]

// Strip Sample Input / Sample Output sections from description text
// They duplicate the example boxes shown from test cases
function stripSampleSections(description) {
  if (!description) return ''
  // Remove everything from **Sample Input** or **Sample Output** up to the next **section** or end
  return description
    .replace(/\*\*Sample Input\*\*[\s\S]*?(?=\*\*[A-Z]|\s*$)/gi, '')
    .replace(/\*\*Sample Output\*\*[\s\S]*?(?=\*\*[A-Z]|\s*$)/gi, '')
    .trim()
}
function CircularTimer({ seconds, total, onExpire, paused }) {
  const [remaining, setRemaining] = useState(seconds)
  const ref = useRef(null)

  useEffect(() => { setRemaining(seconds) }, [seconds])

  useEffect(() => {
    if (paused) { clearInterval(ref.current); return }
    ref.current = setInterval(() => {
      setRemaining(prev => {
        if (prev <= 1) { clearInterval(ref.current); onExpire(); return 0 }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(ref.current)
  }, [seconds, paused, onExpire])

  const pct = (total || seconds) > 0 ? remaining / (total || seconds) : 0
  const r = 52, cx = 60, cy = 60, circ = 2 * Math.PI * r
  const color = pct > 0.5 ? '#10b981' : pct > 0.25 ? '#f59e0b' : '#ef4444'
  const mins = Math.floor(remaining / 60), secs = remaining % 60

  return (
    <div className="flex flex-col items-center">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1A1A1A" strokeWidth="7" />
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="7"
          strokeDasharray={`${circ * pct} ${circ}`} strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: 'stroke-dasharray 1s linear, stroke 0.5s' }} />
        <text x={cx} y={cy - 5} textAnchor="middle" fill="white" fontSize="20" fontWeight="800">
          {mins}:{secs.toString().padStart(2, '0')}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fill="#4b5563" fontSize="10">remaining</text>
      </svg>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// SKILL RADAR (SVG)
// ─────────────────────────────────────────────────────────────────────────────
function SkillRadar({ scores }) {
  const dims = SKILL_DIMENSIONS
  const n = dims.length, cx = 130, cy = 130, r = 100

  const pts = dims.map((d, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2
    const val = Math.min(1, (scores[d.key] || 0) / 100)
    return {
      x: cx + r * val * Math.cos(angle), y: cy + r * val * Math.sin(angle),
      lx: cx + (r + 28) * Math.cos(angle), ly: cy + (r + 28) * Math.sin(angle),
    }
  })

  const poly = pts.map(p => `${p.x},${p.y}`).join(' ')

  return (
    <svg width="260" height="260" viewBox="0 0 260 260">
      {[0.25, 0.5, 0.75, 1].map(ring => {
        const rpts = dims.map((_, i) => {
          const a = (2 * Math.PI * i) / n - Math.PI / 2
          return `${cx + r * ring * Math.cos(a)},${cy + r * ring * Math.sin(a)}`
        }).join(' ')
        return <polygon key={ring} points={rpts} fill="none" stroke="#1A1A1A" strokeWidth="1" />
      })}
      {dims.map((_, i) => {
        const a = (2 * Math.PI * i) / n - Math.PI / 2
        return <line key={i} x1={cx} y1={cy} x2={cx + r * Math.cos(a)} y2={cy + r * Math.sin(a)} stroke="#1A1A1A" strokeWidth="1" />
      })}
      <polygon points={poly} fill="#3b82f615" stroke="#3B8CFF" strokeWidth="2" />
      {pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="5" fill="#3B8CFF" stroke="#1e1b4b" strokeWidth="2" />)}
      {pts.map((p, i) => (
        <text key={i} x={p.lx} y={p.ly} textAnchor="middle" dominantBaseline="middle" fill="#9ca3af" fontSize="10" fontWeight="600">
          <Ico of={dims[i].icon} /> {dims[i].label}
        </text>
      ))}
    </svg>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// LOADING QUESTION SCREEN
// ─────────────────────────────────────────────────────────────────────────────
function LoadingQuestion({ slot, dimension }) {
  const dim = SKILL_DIMENSIONS[slot] || SKILL_DIMENSIONS[0]
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-950 gap-8">
      <div className="relative">
        <div className="w-20 h-20 rounded-full border-4 border-blue-500/20" />
        <div className="absolute inset-0 w-20 h-20 rounded-full border-4 border-blue-500 border-t-transparent animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center text-2xl"><Ico of={dim.icon} /></div>
      </div>
      <div className="text-center">
        <p className="text-white text-xl font-bold mb-2">Generating Question {slot + 1} of {TOTAL_QUESTIONS}</p>
        <p className="text-gray-500 text-sm">Testing your <span className="text-blue-400 font-semibold">{dim.label}</span> skills...</p>
        <p className="text-gray-600 text-xs mt-2">AI is crafting a unique question just for you</p>
      </div>
      <div className="flex gap-2">
        {Array.from({ length: TOTAL_QUESTIONS }).map((_, i) => (
          <div key={i} className={`w-2 h-2 rounded-full transition-all ${i < slot ? 'bg-blue-500' : i === slot ? 'bg-blue-400 animate-pulse scale-150' : 'bg-gray-700'}`} />
        ))}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// RESULT SCREEN
// ─────────────────────────────────────────────────────────────────────────────
function ResultScreen({ rating, tier, topicScores, questionResults, onContinue }) {
  const cfg = TIER_CONFIG[tier?.name] || TIER_CONFIG.Beginner
  const [shown, setShown] = useState(false)
  const [count, setCount] = useState(0)

  useEffect(() => {
    setTimeout(() => setShown(true), 80)
    let n = 0
    const step = Math.max(1, Math.ceil(rating / 80))
    const iv = setInterval(() => {
      n = Math.min(n + step, rating)
      setCount(n)
      if (n >= rating) clearInterval(iv)
    }, 12)
    return () => clearInterval(iv)
  }, [rating])

  const totalPts = questionResults.reduce((s, r) => s + (r.pointsEarned || 0), 0)
  const maxPts   = questionResults.reduce((s, r) => s + (r.maxPoints || 300), 0)
  const accuracy = maxPts > 0 ? Math.round((totalPts / maxPts) * 100) : 0
  const solved   = questionResults.filter(r => r.passed).length

  // Build skill scores from question results
  const skillScores = {}
  questionResults.forEach(r => {
    const dim = r.skillDimension || 'logic'
    const score = r.totalTests > 0 ? Math.round((r.passedTests / r.totalTests) * 100) : 0
    skillScores[dim] = Math.max(skillScores[dim] || 0, score)
  })

  return (
    <div className={`min-h-screen bg-gray-950 transition-opacity duration-700 ${shown ? 'opacity-100' : 'opacity-0'}`}>
      {/* Ambient particles */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {Array.from({ length: 25 }).map((_, i) => (
          <div key={i} className="absolute rounded-full animate-ping"
            style={{ width: `${3 + (i % 5) * 2}px`, height: `${3 + (i % 5) * 2}px`,
              left: `${(i * 37) % 100}%`, top: `${(i * 53) % 100}%`,
              backgroundColor: ['#3B8CFF','#10b981','#3B8CFF','#f59e0b','#ef4444'][i % 5],
              animationDelay: `${(i * 0.3) % 3}s`, animationDuration: `${2 + (i % 3)}s`, opacity: 0.12 }} />
        ))}
      </div>

      <div className="relative z-10 max-w-5xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className={`w-32 h-32 rounded-full bg-gradient-to-br ${cfg.grad} flex items-center justify-center mx-auto mb-6 shadow-2xl`}
            style={{ boxShadow: `0 0 100px ${cfg.glow}` }}>
            <span className="text-6xl"><Ico of={cfg.icon} /></span>
          </div>
          <p className="text-gray-500 text-xs uppercase tracking-widest mb-2">Assessment Complete</p>
          <h1 className="text-6xl font-black mb-3" style={{ color: cfg.color }}>{tier?.name}</h1>
          <p className="text-gray-400 text-base max-w-md mx-auto">{cfg.desc}</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Starting Rating', value: count,    suffix: '',  color: cfg.color },
            { label: 'Questions Solved', value: `${solved}/${TOTAL_QUESTIONS}`, suffix: '', color: '#10b981' },
            { label: 'Score',           value: `${totalPts}/${maxPts}`, suffix: '', color: '#3B8CFF' },
            { label: 'Accuracy',        value: accuracy, suffix: '%', color: '#f59e0b' },
          ].map(s => (
            <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 text-center">
              <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">{s.label}</p>
              <p className="text-3xl font-black" style={{ color: s.color }}>{s.value}{s.suffix}</p>
            </div>
          ))}
        </div>

        {/* Radar + Question breakdown */}
        <div className="grid grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 flex flex-col items-center">
            <p className="text-white font-bold text-sm mb-1">Skill Profile</p>
            <p className="text-gray-500 text-xs mb-4">Based on actual code execution</p>
            <SkillRadar scores={skillScores} />
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <p className="text-white font-bold text-sm mb-4">Question Breakdown</p>
            <div className="space-y-3">
              {questionResults.map((r, i) => {
                const ds = DIFF_STYLE[r.difficulty] || DIFF_STYLE.easy
                const dim = SKILL_DIMENSIONS.find(d => d.key === r.skillDimension) || SKILL_DIMENSIONS[0]
                const pct = r.totalTests > 0 ? Math.round((r.passedTests / r.totalTests) * 100) : 0
                return (
                  <div key={i} className="bg-gray-800/50 rounded-xl p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${r.passed ? 'bg-emerald-500/20 text-emerald-400' : r.passedTests > 0 ? 'bg-amber-500/20 text-amber-400' : 'bg-red-500/20 text-red-400'}`}>
                        {r.passed ? '✓' : r.passedTests > 0 ? '~' : '✗'}
                      </span>
                      <span className="text-white text-xs font-medium flex-1 truncate">{r.title || `Question ${i + 1}`}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${ds.bg} ${ds.text}`}>{ds.label}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-1000"
                          style={{ width: `${pct}%`, backgroundColor: ds.bar }} />
                      </div>
                      <span className="text-gray-500 text-[10px] w-16 text-right">{r.passedTests}/{r.totalTests} tests · {r.pointsEarned}pts</span>
                    </div>
                    <div className="flex items-center gap-1 mt-1">
                      <span className="text-[10px]"><Ico of={dim.icon} /></span>
                      <span className="text-gray-600 text-[10px]">{dim.label}</span>
                      {r.timeTaken && <span className="text-gray-700 text-[10px] ml-auto">{r.timeTaken}s</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* What's next */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 mb-8">
          <p className="text-white font-bold mb-4">What happens now</p>
          <div className="grid grid-cols-2 gap-3">
            {[
              { icon: Target, title: 'Personalized Practice', desc: 'Questions matched to your exact skill level and weak topics' },
              { icon: TrendingUp, title: 'Live Rating Updates', desc: 'Your ELO adjusts after every practice session and match' },
              { icon: Trophy, title: 'Fair Matchmaking', desc: 'Compete against players with similar ratings only' },
              { icon: RefreshCw, title: 'Continuous Calibration', desc: 'The system gets smarter about your skills over time' },
            ].map((item, i) => (
              <div key={i} className="flex items-start gap-3 bg-gray-800/40 rounded-xl p-4">
                <span className="text-xl flex-shrink-0"><Ico of={item.icon} /></span>
                <div>
                  <p className="text-white text-xs font-semibold mb-0.5">{item.title}</p>
                  <p className="text-gray-500 text-xs leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <button onClick={onContinue}
          className="w-full py-5 rounded-2xl font-black text-white text-xl transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] shadow-2xl"
          style={{ background: `linear-gradient(135deg, ${cfg.color}dd, ${cfg.color}88)`, boxShadow: `0 20px 60px ${cfg.glow}` }}>
          Start Coding as {tier?.name} →
        </button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// INTRO SCREEN
// ─────────────────────────────────────────────────────────────────────────────
function IntroScreen({ onStart, onSkip }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-950 px-6">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-10">
          <div className="relative w-24 h-24 mx-auto mb-6">
            <div className="w-24 h-24 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <span className="text-5xl"><Ico of={Target} /></span>
            </div>
            <div className="absolute -top-2 -right-2 w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center text-white text-xs font-black shadow-lg">AI</div>
          </div>
          <h1 className="text-5xl font-black text-white mb-3">Skill Assessment</h1>
          <p className="text-gray-400 text-lg max-w-lg mx-auto leading-relaxed">
            Write real code. We execute it. Every user gets <span className="text-blue-400 font-semibold">different AI-generated questions</span> — no two assessments are the same.
          </p>
        </div>

        {/* How it works */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { step: '01', icon: Bot, title: 'AI Generates', desc: 'Unique questions crafted just for you — never repeated' },
            { step: '02', icon: Laptop, title: 'You Code', desc: 'Write real solutions in Python, JS, C++, or Java' },
            { step: '03', icon: Zap, title: 'We Execute', desc: 'Your code runs against test cases — no self-reporting' },
          ].map(item => (
            <div key={item.step} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 text-center">
              <div className="text-3xl mb-3"><Ico of={item.icon} /></div>
              <p className="text-blue-400 text-xs font-bold mb-1">STEP {item.step}</p>
              <p className="text-white font-semibold text-sm mb-1">{item.title}</p>
              <p className="text-gray-500 text-xs leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>

        {/* Skill dimensions tested */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 mb-6">
          <p className="text-gray-400 text-xs uppercase tracking-wider mb-4">5 Skill Dimensions Tested</p>
          <div className="grid grid-cols-5 gap-2">
            {SKILL_DIMENSIONS.map(d => (
              <div key={d.key} className="flex flex-col items-center gap-2 py-3 bg-gray-800/50 rounded-xl">
                <span className="text-xl"><Ico of={d.icon} /></span>
                <span className="text-xs font-semibold text-white">{d.label}</span>
                <span className="text-[10px] text-gray-500 text-center leading-tight px-1">{d.desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Tier outcomes */}
        <div className="flex gap-2 mb-8">
          {Object.entries(TIER_CONFIG).map(([name, cfg]) => (
            <div key={name} className="flex-1 flex flex-col items-center gap-1.5 py-3 bg-gray-900 border border-gray-800 rounded-xl">
              <span className="text-xl"><Ico of={cfg.icon} /></span>
              <span className="text-xs font-bold" style={{ color: cfg.color }}>{name}</span>
            </div>
          ))}
        </div>

        <div className="flex gap-3 mb-3 text-center text-gray-600 text-xs">
          {[['5', 'Questions'], ['~15min', 'Duration'], ['Real', 'Execution'], ['Adaptive', 'Difficulty']].map(([v, l]) => (
            <div key={l} className="flex-1 bg-gray-900/50 border border-gray-800 rounded-xl py-2">
              <p className="text-white font-bold text-sm">{v}</p>
              <p className="text-gray-600 text-[10px]">{l}</p>
            </div>
          ))}
        </div>

        <button onClick={onStart}
          className="w-full py-5 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-black text-xl transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] mb-3 shadow-lg shadow-blue-500/20 mt-4">
          Start My Assessment
        </button>
        <button onClick={onSkip}
          className="w-full py-3 rounded-xl text-gray-600 hover:text-gray-400 text-sm transition-colors">
          Skip — use default rating (1000 · Intermediate)
        </button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function SkillAssessment() {
  const { user, login } = useAuth()
  const navigate = useNavigate()

  // phase: intro | loading | quiz | running | submitting | result
  const [phase, setPhase] = useState('intro')
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState('')

  // Current question state
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [currentSlot, setCurrentSlot] = useState(0)
  const [currentDiff, setCurrentDiff] = useState('easy')
  const [timerKey, setTimerKey] = useState(0)
  const [timeLeft, setTimeLeft] = useState(300)      // from the server's clock when the question arrived
  const [timeLimit, setTimeLimit] = useState(300)
  const [timeExpired, setTimeExpired] = useState(false)
  const [submitted, setSubmitted] = useState(false)  // the server has graded the question on screen

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
  // The latest editor text, so an answer sent by the timer carries what was typed last
  const codeRef = useRef('')
  codeRef.current = code
  // The starter code for the question on screen, in the language chosen: the editor locks its harness against this
  const starterRef = useRef('')
  starterRef.current = starterFor(currentQuestion, language)

  // Someone who already finished is sent home when they open this page. It only applies on the intro screen:
  // finishing refreshes the user (completed = true) and the result screen has to stay up for them to read.
  useEffect(() => {
    if (user?.skill_quiz_completed && phase === 'intro') navigate('/home')
  }, [user, phase, navigate])

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

  // ── Load the next question ───────────────────────────────────────────
  // The server picks the question and its difficulty and keeps the clock; an open question comes back with the time it has left.
  async function loadQuestion() {
    setPhase('loading')
    setRunResult(null)
    setExecError('')
    setTimeExpired(false)
    setSubmitted(false)

    try {
      const { data } = await api.post('/skill-assessment/generate-question', { exclude_titles: usedTitles })

      setCurrentQuestion(data)
      setCurrentSlot(data.slot ?? 0)
      setCurrentDiff(data.difficulty || 'easy')
      setQuestionResults((data.previous_results || []).map(fromServerResult))
      setCode(starterFor(data, language) || `# Write your solution here\n`)
      setUsedTitles(prev => [...prev, data.title].filter(Boolean))
      setTimeLimit(data.time_limit_seconds || 300)
      setTimeLeft(data.time_remaining_seconds ?? data.time_limit_seconds ?? 300)
      setTimerKey(k => k + 1)
      setPhase('quiz')
    } catch (err) {
      if (err.response?.status === 409) {
        // every question is answered (finish), or the assessment is already done
        if (String(err.response?.data?.detail || '').startsWith('All questions')) return finishAssessment()
        return navigate('/home')
      }
      setExecError(err.response?.data?.detail || 'Failed to generate question. Please try again.')
      setPhase('quiz')
    }
  }

  function startAssessment() {
    setCurrentSlot(0)
    setQuestionResults([])
    setUsedTitles([])
    loadQuestion()
  }

  // ── Timer expired: send the current code once nothing is running ─────────
  const handleTimerExpire = useCallback(() => setTimeExpired(true), [])

  useEffect(() => {
    if (!timeExpired || running || submitted || phase !== 'quiz' || !currentQuestion) return
    const t = setTimeout(() => submitQuestion(true), 1500)
    return () => clearTimeout(t)
  }, [timeExpired, running, submitted, phase, currentQuestion])

  // ── Run (the sample tests; nothing is graded) ────────────────────────────
  async function runPreview() {
    if (!currentQuestion || running || submitted) return
    setRunning(true)
    setRunResult(null)
    setExecError('')
    try {
      const { data } = await api.post('/skill-assessment/run', {
        item_id: currentQuestion.item_id, code: codeRef.current, language,
      })
      const results = fromServerTests(data.tests)
      setRunResult({ preview: true, results, passedTests: data.passed_tests, totalTests: data.total_tests })
    } catch (err) {
      setExecError(err.response?.data?.detail || 'Execution failed')
    } finally { setRunning(false) }
  }

  // ── Submit (the server runs every test and grades the answer) ────────────
  async function submitQuestion(fromTimer = false) {
    if (!currentQuestion || running || submitted) return
    setRunning(true)
    setExecError('')
    try {
      const { data } = await api.post('/skill-assessment/submit-question', {
        item_id: currentQuestion.item_id, code: codeRef.current, language, timed_out: fromTimer,
      })
      setSubmitted(true)
      const result = fromServerResult(data)
      const newResults = [...questionResults, result]
      setQuestionResults(newResults)
      setRunResult({
        preview: false, results: fromServerTests(data.tests),
        passed: data.passed, passedTests: data.passed_tests, totalTests: data.total_tests,
      })
      if (data.late) setExecError('Sent after the time limit, so it scores no points.')

      // Move to the next question after 2.5s
      setTimeout(() => {
        if (data.finished) finishAssessment()
        else loadQuestion()
      }, 2500)
    } catch (err) {
      if (err.response?.status === 409) {   // already graded (a double submit): carry on
        setSubmitted(true)
        setTimeout(() => loadQuestion(), 1000)
      } else {
        setExecError(err.response?.data?.detail || 'Submission failed')
      }
    } finally { setRunning(false) }
  }

  // ── Finish: the server rates the answers it graded ───────────────────────
  async function finishAssessment() {
    setPhase('submitting')
    try {
      const { data } = await api.post('/skill-assessment', {})
      setFinalRating(data.rating)
      setFinalTier(data.tier)
      setFinalTopicScores(data.topic_scores || {})
      if (Array.isArray(data.results)) setQuestionResults(data.results.map(fromServerResult))
      const meRes = await api.get('/users/me')
      login(meRes.data, localStorage.getItem('token'))
      setPhase('result')
    } catch (err) {
      setExecError('Failed to save results. Please try again.')
      setPhase('quiz')
    }
  }

  async function handleSkip() {
    setPhase('submitting')
    try {
      const { data } = await api.post('/skill-assessment', { skip: true })
      setFinalRating(data.rating)
      setFinalTier(data.tier)
      const meRes = await api.get('/users/me')
      login(meRes.data, localStorage.getItem('token'))
      setPhase('result')
    } catch { navigate('/home') }
  }

  // ── Parse test cases helper ───────────────────────────────────────────────
  function parseTestCases(raw) {
    try { const a = typeof raw === 'string' ? JSON.parse(raw) : raw; return Array.isArray(a) ? a : [] }
    catch { return [] }
  }

  // ── Render phases ─────────────────────────────────────────────────────────
  if (phase === 'intro') return <IntroScreen onStart={startAssessment} onSkip={handleSkip} />

  if (phase === 'loading') return <LoadingQuestion slot={currentSlot} />

  if (phase === 'submitting') return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-950 gap-8">
      <div className="relative">
        <div className="w-20 h-20 rounded-full border-4 border-blue-500/20" />
        <div className="absolute inset-0 w-20 h-20 rounded-full border-4 border-blue-500 border-t-transparent animate-spin" />
      </div>
      <div className="text-center">
        <p className="text-white text-xl font-bold mb-2">Analyzing your performance...</p>
        <p className="text-gray-500 text-sm">Calculating skill rating across all dimensions</p>
      </div>
    </div>
  )

  if (phase === 'result') return (
    <ResultScreen rating={finalRating} tier={finalTier} topicScores={finalTopicScores}
      questionResults={questionResults} onContinue={() => navigate('/home')} />
  )

  if (!currentQuestion && phase === 'quiz') return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-950 gap-4">
      {execError && <p className="text-red-400 text-sm">{execError}</p>}
      <button onClick={() => loadQuestion()}
        className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold">
        Retry
      </button>
    </div>
  )

  // ── Quiz Screen ───────────────────────────────────────────────────────────
  const ds = DIFF_STYLE[currentDiff] || DIFF_STYLE.easy
  const dim = SKILL_DIMENSIONS[currentSlot] || SKILL_DIMENSIONS[0]
  const tcs = parseTestCases(currentQuestion?.test_cases || '[]')

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col" style={{ fontFamily: 'inherit' }}>
      {/* ── Top Bar ── */}
      <div className="border-b border-gray-800 px-5 py-3 flex items-center justify-between bg-gray-950/95 backdrop-blur sticky top-0 z-20">
        <div className="flex items-center gap-3">
          <span className="text-white font-black text-lg">CompileX</span>
          <span className="text-gray-700">|</span>
          <span className="text-gray-400 text-sm">Skill Assessment</span>
          <div className={`px-2.5 py-1 rounded-full border text-xs font-bold ${ds.bg} ${ds.border} ${ds.text}`}>{ds.label}</div>
          <div className="flex items-center gap-1.5 text-gray-500 text-xs">
            <span><Ico of={dim.icon} /></span><span>{dim.label}</span>
          </div>
        </div>
        <div className="flex items-center gap-5">
          {/* Progress */}
          <div className="flex items-center gap-2">
            {Array.from({ length: TOTAL_QUESTIONS }).map((_, i) => {
              const r = questionResults[i]
              return (
                <div key={i} className={`transition-all duration-300 rounded-full ${
                  i < questionResults.length
                    ? r?.passed ? 'w-3 h-3 bg-emerald-500' : r?.partial ? 'w-3 h-3 bg-amber-500' : 'w-3 h-3 bg-red-500'
                    : i === currentSlot ? 'w-4 h-4 bg-blue-500 ring-2 ring-blue-500/30' : 'w-3 h-3 bg-gray-700'
                }`} />
              )
            })}
            <span className="text-gray-500 text-xs ml-1">{currentSlot + 1}/{TOTAL_QUESTIONS}</span>
          </div>
          {/* Language */}
          <div className="flex gap-1">
            {LANGUAGES.map(l => (
              <button key={l.value} onClick={() => setLanguage(l.value)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${language === l.value ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}>
                <Ico of={l.icon} /> {l.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Main Layout ── */}
      <div className="flex-1 flex overflow-hidden" style={{ height: 'calc(100vh - 57px)' }}>
        {/* Left: Problem Panel */}
        <div className="w-[400px] flex-shrink-0 border-r border-gray-800 overflow-y-auto bg-gray-950">
          <div className="p-5">
            {/* Timer */}
            <div className="flex justify-center mb-5">
              <CircularTimer key={timerKey} seconds={timeLeft} total={timeLimit} onExpire={handleTimerExpire} paused={submitted} />
            </div>

            {timeExpired && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm text-center mb-4 animate-pulse">
                ⏰ Time's up! Submitting your current code...
              </div>
            )}

            {/* Question header */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-gray-600 text-xs font-mono">Q{currentSlot + 1}</span>
              <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${ds.bg} ${ds.text}`}>{ds.label}</div>
              <div className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400">
                {currentSlot === 4 ? 500 : currentSlot === 3 ? 400 : currentSlot === 2 ? 300 : 200} pts
              </div>
            </div>

            <h2 className="text-xl font-bold text-white mb-3">{currentQuestion?.title}</h2>
            <p className="text-gray-300 text-sm leading-relaxed mb-5 whitespace-pre-line">{stripSampleSections(currentQuestion?.description)}</p>

            {/* Test cases preview */}
            {tcs.slice(0, 2).map((tc, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-3 mb-2 font-mono text-xs">
                <p className="text-gray-500 text-[10px] uppercase tracking-wider mb-1.5">Example {i + 1}</p>
                <div className="text-gray-400 mb-1">Input: <span className="text-cyan-400 whitespace-pre-wrap">{tc.input ?? tc.stdin ?? ''}</span></div>
                <div className="text-gray-400">Output: <span className="text-green-400">{tc.expected_output ?? tc.output ?? ''}</span></div>
              </div>
            ))}

            {/* Constraints */}
            {currentQuestion?.constraints && (
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-3 mb-4">
                <p className="text-gray-500 text-[10px] uppercase tracking-wider mb-1">Constraints</p>
                <p className="text-gray-400 text-xs whitespace-pre-line">{currentQuestion.constraints}</p>
              </div>
            )}

            {/* Previous results mini-list */}
            {questionResults.length > 0 && (
              <div className="mt-5 pt-5 border-t border-gray-800">
                <p className="text-gray-600 text-[10px] uppercase tracking-wider mb-2">Previous</p>
                {questionResults.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 mb-1.5">
                    <span className={`text-xs font-bold ${r.passed ? 'text-emerald-400' : r.partial ? 'text-amber-400' : 'text-red-400'}`}>
                      {r.passed ? '✓' : r.partial ? '~' : '✗'}
                    </span>
                    <span className="text-gray-500 text-xs truncate flex-1">{r.title}</span>
                    <span className="text-gray-700 text-[10px]">{r.pointsEarned}pts</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Editor + Output */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            <Editor
              height="100%"
              language={LANGUAGES.find(l => l.value === language)?.monaco || 'python'}
              value={code}
              onChange={v => setCode(v || '')}
              onMount={(e, monaco) => { editorRef.current = e; attachProtectedRegion(e, monaco, () => starterRef.current) }}
              theme="vs-dark"
              options={{
                fontSize: 14, minimap: { enabled: false },
                scrollBeyondLastLine: false, padding: { top: 16 },
                fontFamily: 'JetBrains Mono, Fira Code, Consolas, monospace',
                lineNumbers: 'on', renderLineHighlight: 'all',
              }}
            />
          </div>

          {/* Output panel */}
          <div className="border-t border-gray-800 bg-gray-900 flex flex-col" style={{ minHeight: '180px', maxHeight: '260px' }}>
            <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 flex-shrink-0">
              <div className="flex items-center gap-3">
                {execError && <span className="text-red-400 text-xs">{execError}</span>}
                {runResult && !running && (
                  <span className={`text-xs font-bold ${runResult.passed ? 'text-emerald-400' : runResult.passedTests > 0 ? 'text-amber-400' : 'text-red-400'}`}>
                    {runResult.passed ? '✓ All tests passed!' : `${runResult.passedTests}/${runResult.totalTests} tests passed`}
                    {runResult.preview && <span className="text-gray-600 font-normal ml-1">(preview)</span>}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button onClick={runPreview} disabled={running || submitted}
                  className="px-4 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-xs font-semibold transition-all disabled:opacity-40 flex items-center gap-1.5">
                  {running && !runResult ? <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> : '▶'}
                  Run
                </button>
                <button onClick={() => submitQuestion(false)} disabled={running || submitted}
                  className="px-5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-black transition-all disabled:opacity-40 flex items-center gap-1.5">
                  {running ? <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Ico of={Zap} />}
                  Submit
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {!runResult && !running && (
                <p className="text-gray-700 text-xs text-center py-6">Click Run to test with examples, or Submit to evaluate all test cases</p>
              )}
              {running && (
                <div className="flex items-center gap-3 py-6 justify-center">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-gray-500 text-xs">Executing your code...</span>
                </div>
              )}
              {runResult && !running && (
                <div className="space-y-2">
                  {runResult.results.map((r, i) => (
                    <div key={i} className={`rounded-xl p-3 border text-xs font-mono ${r.passed ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'}`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={r.passed ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>{r.passed ? '✓' : '✗'}</span>
                        <span className="text-gray-500">Test {i + 1}</span>
                      </div>
                      {!r.passed && (
                        <div className="space-y-0.5 mt-1.5 pl-4">
                          <div className="text-gray-500">Expected: <span className="text-green-400">{r.expected}</span></div>
                          <div className="text-gray-500">Got: <span className="text-red-400">{r.output || '(no output)'}</span></div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
