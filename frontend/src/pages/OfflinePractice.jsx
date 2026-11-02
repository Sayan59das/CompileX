import React, { useState, useRef, useEffect, useCallback } from 'react'
import { AlertCircle, Bot, Check, CheckCircle2, FileCheck, FileText, Gauge, Info, ListChecks, ShieldCheck, Code2, Languages, XCircle } from 'lucide-react'
import Logo from '../components/Logo'
import CoderScene from '../components/CoderScene'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import Editor from '@monaco-editor/react'
import MathText from '../components/MathText'
import AnimatedBackgroundCSS from '../components/AnimatedBackgroundCSS'
import { attachProtectedRegion } from '../utils/protectedRegion'

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const LANGUAGES = [
  { value: 'python',     label: 'Python',     monaco: 'python'     },
  { value: 'cpp',        label: 'C++',        monaco: 'cpp'        },
  { value: 'java',       label: 'Java',       monaco: 'java'       },
  { value: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { value: 'c',          label: 'C',          monaco: 'c'          },
]

const DIFF = {
  easy:   { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/25', dot: 'bg-emerald-400' },
  medium: { text: 'text-amber-400',   bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   dot: 'bg-amber-400'   },
  hard:   { text: 'text-rose-400',    bg: 'bg-rose-500/10',    border: 'border-rose-500/25',    dot: 'bg-rose-400'    },
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function parseTestCases(raw) {
  try { const a = typeof raw === 'string' ? JSON.parse(raw) : raw; return Array.isArray(a) ? a : [] }
  catch { return [] }
}
function parseStarterCode(raw, lang) {
  try { const m = typeof raw === 'string' ? JSON.parse(raw) : raw; return m[lang] || '' }
  catch { return '' }
}
function parseQuestionSections(description) {
  if (!description) return { body: '', sections: [] }
  const SKIP = new Set(['Sample Input', 'Sample Output'])
  const ALL  = ['Input Format', 'Output Format', 'Constraints', 'Note', 'Explanation', 'Sample Input', 'Sample Output']
  const parts = description.split(new RegExp(`\\*\\*(${ALL.join('|')})\\*\\*`, 'gi'))
  const body = parts[0].trim()
  const sections = []
  for (let i = 1; i < parts.length; i += 2) {
    const name = parts[i], content = (parts[i + 1] || '').trim()
    if (name && content && !SKIP.has(name)) sections.push({ name, content })
  }
  return { body, sections }
}

// ─────────────────────────────────────────────────────────────────────────────
// SUB-COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

function HighlightedText({ text }) {
  if (!text) return null
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g)
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('`') && p.endsWith('`'))
          return <code key={i} className="px-1.5 py-0.5 rounded-md bg-white/[0.07] text-sky-300 font-mono text-[0.82em] border border-white/[0.06]">{p.slice(1,-1)}</code>
        if (p.startsWith('**') && p.endsWith('**'))
          return <strong key={i} className="text-white font-semibold"><MathText text={p.slice(2,-2)} /></strong>
        if ((p.startsWith('$$') && p.endsWith('$$')) || (p.startsWith('$') && p.endsWith('$')))
          return <MathText key={i} text={p} />
        return <span key={i}>{p}</span>
      })}
    </>
  )
}

function SectionBlock({ name, content }) {
  const STYLES = {
    'Input Format':  { label: 'text-sky-400',     bar: 'bg-sky-400',     code: true  },
    'Output Format': { label: 'text-blue-400',  bar: 'bg-blue-400',  code: true  },
    'Constraints':   { label: 'text-amber-400',   bar: 'bg-amber-400',   code: false },
    'Note':          { label: 'text-slate-400',   bar: 'bg-slate-400',   code: false },
    'Explanation':   { label: 'text-cyan-400',    bar: 'bg-cyan-400',    code: false },
  }
  const s = STYLES[name] || { label: 'text-slate-400', bar: 'bg-slate-500', code: false }
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className={`w-0.5 h-3.5 rounded-full ${s.bar}`} />
        <span className={`text-[10px] font-black uppercase tracking-[0.12em] ${s.label}`}>{name}</span>
      </div>
      {s.code ? (
        <pre className="bg-[#000000] border border-white/[0.06] rounded-xl px-4 py-3 text-[12px] font-mono text-slate-200 whitespace-pre-wrap leading-relaxed">
          {content}
        </pre>
      ) : (
        <div className="space-y-1 text-[12.5px] text-slate-300 leading-relaxed pl-2.5">
          {content.split('\n').map((l, i) => <p key={i}><HighlightedText text={l} /></p>)}
        </div>
      )}
    </div>
  )
}

function ScoreRing({ value, size = 56 }) {
  const sw = 5, r = (size - sw) / 2
  const circ = 2 * Math.PI * r
  const color = value >= 80 ? '#10b981' : value >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#1e2535" strokeWidth={sw} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={sw}
        strokeDasharray={`${(value/100)*circ} ${circ}`} strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 0.8s ease' }} />
      <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle"
        style={{ transform:'rotate(90deg)', transformOrigin:'50% 50%', fill:'#fff', fontSize: size*0.2, fontWeight: 800 }}>
        {value}%
      </text>
    </svg>
  )
}

function Spinner({ color = 'border-blue-500' }) {
  return (
    <div className={`w-5 h-5 rounded-full border-2 border-white/10 ${color} border-t-transparent animate-spin`} />
  )
}

// Right-side icon tab button
function IconTab({ icon, label, active, onClick, badge }) {
  return (
    <button onClick={onClick} title={label}
      className={`relative flex flex-col items-center gap-1 py-3 w-full transition-all duration-200 group ${
        active ? 'text-white' : 'text-slate-500 hover:text-slate-200'
      }`}>
      {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-8 bg-blue-500 rounded-r-full" />}
      {typeof icon === 'string' ? <span className="text-base">{icon}</span> : React.createElement(icon, { className: 'h-[18px] w-[18px]', 'aria-hidden': true })}
      <span className="text-[10px] font-medium leading-none">{label}</span>
      {badge != null && (
        <span className={`absolute top-1.5 right-1.5 text-[8px] font-black min-w-[14px] h-3.5 flex items-center justify-center rounded-full px-0.5 ${
          active ? 'bg-blue-500 text-white' : 'bg-white/10 text-slate-400'
        }`}>{badge}</span>
      )}
    </button>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function OfflinePractice() {
  const { user } = useAuth()
  const nav = useNavigate()

  // Right panel: null | 'questions' | 'ai' | 'complexity'
  const [rightPanel, setRightPanel] = useState('questions')

  // Generator
  const [inputMode,       setInputMode]       = useState('type')
  const [typedTopic,      setTypedTopic]       = useState('')
  const [difficulty,      setDifficulty]       = useState(() => {
    const r = user?.rating || 1000
    return r < 900 ? 'easy' : r < 1300 ? 'medium' : 'hard'
  })
  const [numQuestions,    setNumQuestions]     = useState(3)
  const [file,            setFile]             = useState(null)
  const [loading,         setLoading]          = useState(false)
  const [genError,        setGenError]         = useState('')
  const [availableTopics, setAvailableTopics]  = useState([])

  // Questions
  const [questions, setQuestions] = useState([])
  const [activeQ,   setActiveQ]   = useState(0)
  const [submissionStatus, setSubmissionStatus] = useState({})
  const [showCompletionModal, setShowCompletionModal] = useState(false)

  // Editor
  const [language, setLanguage] = useState('python')
  const [code,     setCode]     = useState('')
  const editorRef = useRef(null)
  const protectedRef = useRef(null)
  // The starter code for the question on screen, in the language chosen: the editor locks its harness against this
  const starterRef = useRef('')
  starterRef.current = parseStarterCode(questions[activeQ]?.starter_code, language)

  // Problem panel width
  const [problemW,  setProblemW]  = useState(380)
  const probResizing = useRef(false)
  const probStartX   = useRef(0)
  const probStartW   = useRef(0)

  // Session dedup
  const sessionUsedTitles = useRef((() => {
    try { return new Set(JSON.parse(localStorage.getItem('compilex_used_titles') || '[]')) }
    catch { return new Set() }
  })())
  const addUsedTitle = useCallback((t) => {
    if (!t) return
    sessionUsedTitles.current.add(t.toLowerCase())
    try { localStorage.setItem('compilex_used_titles', JSON.stringify([...sessionUsedTitles.current].slice(-100))) } catch {}
  }, [])

  // Bottom panel
  const [bottomTab,  setBottomTab]  = useState('testcases')
  const [bottomH,    setBottomH]    = useState(220)
  const [bottomOpen, setBottomOpen] = useState(true)
  const btmResizing = useRef(false)
  const btmStartY   = useRef(0)
  const btmStartH   = useRef(0)

  // Test cases
  const [testCases,  setTestCases]  = useState([])
  const [selectedTC, setSelectedTC] = useState(0)
  const [tcResults,  setTcResults]  = useState([])

  // Run / submit
  const [submitting,   setSubmitting]   = useState(false)
  const [submitResult, setSubmitResult] = useState(null)

  // Custom input
  const [customInput,  setCustomInput]  = useState('')
  const [customOutput, setCustomOutput] = useState(null)
  const [runningCustom, setRunningCustom] = useState(false)

  // AI feedback
  const [aiFeedback, setAiFeedback] = useState(null)
  const [loadingAI,  setLoadingAI]  = useState(false)

  // Grok AI feedback chat
  const [grokMessages, setGrokMessages] = useState([])
  const [grokInput, setGrokInput] = useState('')
  const [grokLoading, setGrokLoading] = useState(false)
  const grokChatEndRef = useRef(null)

  useEffect(() => {
    grokChatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [grokMessages, grokLoading])

  // Complexity
  const [complexity, setComplexity] = useState(null)
  const [loadingCx,  setLoadingCx]  = useState(false)

  // Toast
  const [toast, setToast] = useState({ msg: '', type: 'info', visible: false })
  const toastTimer = useRef(null)
  const showToast = useCallback((msg, type = 'info') => {
    if (toastTimer.current) clearTimeout(toastTimer.current)
    setToast({ msg, type, visible: true })
    toastTimer.current = setTimeout(() => setToast(t => ({ ...t, visible: false })), 2800)
  }, [])

  const triggerLayout = useCallback(() => {
    setTimeout(() => editorRef.current?.layout(), 60)
  }, [])

  useEffect(() => { triggerLayout() }, [rightPanel, triggerLayout])

  useEffect(() => {
    if (questions.length > 0 && Object.keys(submissionStatus).length === questions.length) {
      setShowCompletionModal(true)
    }
  }, [Object.keys(submissionStatus).length, questions.length])

  useEffect(() => {
    api.get('/questions/topics').then(({ data }) => {
      if (data?.topics) setAvailableTopics(data.topics)
    }).catch(() => setAvailableTopics([
      'arrays','strings','graphs','trees','dynamic programming',
      'sorting','hashing','stacks','queues','greedy',
      'backtracking','recursion','linked lists','math','two pointers',
    ]))
  }, [])

  useEffect(() => {
    const q = questions[activeQ]; if (!q) return
    setTestCases(parseTestCases(q.test_cases).map((tc, i) => ({ ...tc, hidden: i > 0 })))
    setTcResults([]); setSelectedTC(0); setSubmitResult(null)
    setAiFeedback(null); setComplexity(null); setGrokMessages([]); setGrokInput('')
    setCode(parseStarterCode(q.starter_code, language))
  }, [activeQ, questions])

  useEffect(() => {
    const q = questions[activeQ]
    if (q) setCode(parseStarterCode(q.starter_code, language))
  }, [language])

  // Problem panel resize
  useEffect(() => {
    const onMove = e => {
      if (!probResizing.current) return
      setProblemW(Math.min(600, Math.max(280, probStartW.current + e.clientX - probStartX.current)))
      triggerLayout()
    }
    const onUp = () => { if (probResizing.current) { probResizing.current = false; document.body.style.cursor = ''; triggerLayout() } }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [triggerLayout])

  // Bottom panel resize
  useEffect(() => {
    const onMove = e => {
      if (!btmResizing.current) return
      setBottomH(Math.min(520, Math.max(140, btmStartH.current + btmStartY.current - e.clientY)))
      triggerLayout()
    }
    const onUp = () => { if (btmResizing.current) { btmResizing.current = false; document.body.style.cursor = ''; triggerLayout() } }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [triggerLayout])

  // ── Actions ──────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setGenError(''); setLoading(true)
    setSubmissionStatus({})
    setShowCompletionModal(false)
    try {
      if (inputMode === 'upload') {
        if (!file) return
        const fd = new FormData(); fd.append('file', file); fd.append('num_questions', numQuestions)
        const { data } = await api.post('/questions/parse_syllabus', fd)
        setQuestions(data); setActiveQ(0)
      } else {
        if (!typedTopic.trim()) return
        const generated = []
        questions.forEach(q => q.title && addUsedTitle(q.title))
        for (let i = 0; i < numQuestions; i++) {
          const used = [...sessionUsedTitles.current, ...generated.map(q => q.title?.toLowerCase()).filter(Boolean)]
          const { data } = await api.post('/questions/generate', { difficulty, topic: typedTopic.trim(), num_test_cases: 5, exclude_titles: used })
          const { data: saved } = await api.post('/questions', data)
          generated.push({ ...data, id: saved.id })
          if (data.title) addUsedTitle(data.title)
        }
        setQuestions(generated); setActiveQ(0)
      }
      setRightPanel('questions')
    } catch (err) {
      setGenError(err.response?.data?.detail || 'Failed to generate questions.')
    } finally { setLoading(false) }
  }

  const handleSubmit = async () => {
    const q = questions[activeQ]; if (!q) return
    setSubmitting(true); setSubmitResult(null); setBottomTab('testcases'); setBottomOpen(true)
    try {
      const { data: dbQ } = await api.post('/questions', { title: q.title, description: q.description, difficulty: q.difficulty, topic: q.topic || 'general', starter_code: q.starter_code, test_cases: q.test_cases, ref: q.ref })
      const { data: lobby } = await api.post('/lobbies', { name: 'solo_' + Math.random().toString(36).slice(7), max_players: 2, time_limit: 3600 })
      await api.post(`/lobbies/${lobby.id}/join`, {})
      const { data: sub } = await api.post('/submissions', { code, language, question_id: dbQ.id })
      setSubmitResult(sub)
      if (sub.test_case_details) setTcResults(sub.test_case_details)
      setSubmissionStatus(prev => ({ ...prev, [activeQ]: sub.status === 'passed' ? 'passed' : 'failed' }))
      fetchAI(sub)
    } catch (err) { showToast(err.response?.data?.detail || 'Submission failed', 'error') }
    finally { setSubmitting(false) }
  }

  const handleRunTests = async () => {
    const q = questions[activeQ]; if (!q) return
    setSubmitting(true); setSubmitResult(null); setBottomTab('testcases'); setBottomOpen(true)
    try {
      const { data: dbQ } = await api.post('/questions', { title: q.title, description: q.description, difficulty: q.difficulty, topic: q.topic || 'general', starter_code: q.starter_code, test_cases: q.test_cases, ref: q.ref })
      const { data: sub } = await api.post('/run-tests', { code, language, question_id: dbQ.id })
      setSubmitResult(sub)
      if (sub.test_case_details) setTcResults(sub.test_case_details)
    } catch (err) { showToast(err.response?.data?.detail || 'Run failed', 'error') }
    finally { setSubmitting(false) }
  }

  const handleRunCustom = async () => {
    setRunningCustom(true); setCustomOutput(null)
    try {
      const inputs = customInput.split('\n---').map(s => s.trim()).filter(Boolean)
      const { data } = await api.post('/execute', { code, language, inputs: inputs.length ? inputs : [customInput] })
      setCustomOutput(data.results || [])
    } catch (err) { setCustomOutput([{ error: err.response?.data?.detail || 'Execution failed' }]) }
    finally { setRunningCustom(false) }
  }

  const fetchAI = async (sub) => {
    const q = questions[activeQ]; if (!q) return
    setLoadingAI(true); setRightPanel('ai')
    try {
      const { data } = await api.post('/analyze-code', { code, language, problem_statement: `${q.title}\n\n${q.description||''}`, test_results: sub?.test_case_details||[], passed_tests: sub?.passed_tests??0, total_tests: sub?.total_tests??0 })
      setAiFeedback(data)
    } catch { setAiFeedback(null) }
    finally { setLoadingAI(false) }
  }

  const fetchComplexity = async () => {
    const q = questions[activeQ]; if (!q) return
    setLoadingCx(true); setRightPanel('complexity')
    try {
      const { data } = await api.post('/analyze-complexity', { code, language, problem_statement: `${q.title}\n\n${q.description||''}` })
      setComplexity(data)
    } catch { setComplexity(null) }
    finally { setLoadingCx(false) }
  }

  async function sendGrokMessage(messageText) {
    const text = (messageText || grokInput).trim()
    if (!text || grokLoading) return

    const userMsg = { role: 'user', content: text }
    const updatedHistory = [...grokMessages, userMsg]
    setGrokMessages(updatedHistory)
    setGrokInput('')
    setGrokLoading(true)

    const qItem = questions[activeQ]
    try {
      const { data } = await api.post('/ai-feedback', {
        message: text,
        code: code || '',
        language: language,
        problem_statement: qItem ? `${qItem.title}\n\n${qItem.description||''}` : '',
        history: grokMessages,
      })
      setGrokMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to get AI response. Please try again.'
      setGrokMessages(prev => [...prev, { role: 'assistant', content: errMsg }])
    } finally {
      setGrokLoading(false)
    }
  }

  const q           = questions[activeQ]
  const ds          = DIFF[q?.difficulty] || DIFF.medium
  const passedCount = tcResults.filter(r => r.passed).length
  const totalCount  = tcResults.length
  const isRunning   = bottomTab === 'custom' ? runningCustom : submitting

  // ── RENDER ────────────────────────────────────────────────────────────────
  return (
    <div className="h-screen bg-[#000000] flex flex-col overflow-hidden text-white relative" style={{ fontFamily: 'inherit' }}>
      <div className="absolute inset-0 z-0 pointer-events-none">
        <AnimatedBackgroundCSS />
      </div>

      {/* ── TOAST ── */}
      <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 pointer-events-none ${toast.visible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-3'}`}>
        <div className={`flex items-center gap-2.5 px-4 py-2.5 rounded-2xl shadow-2xl text-xs font-semibold backdrop-blur border ${
          toast.type === 'error' ? 'bg-rose-950/90 border-rose-500/40 text-rose-300' :
          toast.type === 'success' ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-300' :
          'bg-[#1a1f2e]/90 border-white/10 text-slate-300'
        }`}>
          {toast.type === 'error' ? <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" /> : toast.type === 'success' ? <Check className="h-4 w-4 shrink-0" aria-hidden="true" /> : <Info className="h-4 w-4 shrink-0" aria-hidden="true" />}
          {toast.msg}
        </div>
      </div>

      {/* ── TOP BAR ── */}
      <header className="h-11 flex items-center justify-between px-4 border-b border-white/[0.05] bg-[#000000]/95 backdrop-blur shrink-0 z-40">
        <div className="flex items-center gap-3">
          <Link to="/dashboard" className="flex items-center gap-2" aria-label="Back to dashboard">
            <Logo size={24} />
          </Link>
          <div className="h-4 w-px bg-white/10" />
          <span className="text-[14px] font-semibold text-white">Practice</span>
        </div>

        {q && (
          <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
            <span className={`text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wide ${ds.text} ${ds.bg} border ${ds.border}`}>{q.difficulty}</span>
            {q.topic && <span className="text-[10px] px-2.5 py-1 rounded-full font-semibold bg-blue-500/10 border border-blue-500/20 text-blue-300">#{q.topic}</span>}
            <span className="text-sm font-bold text-white max-w-xs truncate">{q.title}</span>
          </div>
        )}

        <div className="flex items-center gap-2">
          {user?.rating && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.07] text-[10px] text-slate-400">
              <span>Rating</span>
              <span className="font-bold text-blue-400">{user.rating}</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.07] text-[10px] text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            {user?.username}
          </div>
        </div>
      </header>

      {/* ── BODY ── */}
      <div className="flex flex-1 overflow-hidden relative z-10">

        {/* ══ MAIN CONTENT ══ */}
        <div className="flex-1 flex overflow-hidden min-w-0">
          {q ? (
            <>
              {/* PROBLEM PANEL */}
              <div style={{ width: problemW }} className="shrink-0 flex flex-col border-r border-white/[0.05] bg-[#080c16] overflow-hidden relative">
                <div className="flex-1 overflow-y-auto scrollbar-thin">
                  <div className="px-6 pt-6 pb-4">
                    <div className="flex items-center gap-2 mb-3 flex-wrap">
                      <span className={`inline-flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wide ${ds.text} ${ds.bg} border ${ds.border}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${ds.dot}`} />{q.difficulty}
                      </span>
                      {q.topic && <span className="text-[10px] px-2.5 py-1 rounded-full font-semibold bg-blue-500/8 border border-blue-500/20 text-blue-400">#{q.topic}</span>}
                    </div>
                    <h2 className="text-lg font-black text-white leading-tight tracking-tight mb-1">{q.title}</h2>
                  </div>

                  <div className="px-6 pb-6 space-y-5">
                    {(() => {
                      const { body, sections } = parseQuestionSections(q.description || '')
                      return (
                        <>
                          {body && (
                            <div className="text-[13px] text-slate-300/90 leading-[1.75] space-y-1.5">
                              {body.split('\n').filter(Boolean).map((line, i) => (
                                <p key={i}><HighlightedText text={line} /></p>
                              ))}
                            </div>
                          )}
                          {q.diagram && (
                            <div className="rounded-xl overflow-hidden border border-white/[0.06]">
                              <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest px-3 py-2 border-b border-white/[0.05]">Diagram</p>
                              <img src={q.diagram} alt="diagram" className="w-full" />
                            </div>
                          )}
                          {/* Test case examples (replaces Sample Input/Output) */}
                          {parseTestCases(q.test_cases).slice(0, 2).map((tc, i) => {
                            const inp = tc.input || tc.input_data || ''
                            const out = tc.output || tc.expected_output || ''
                            return (
                              <div key={i} className="rounded-xl border border-white/[0.06] bg-[#000000] overflow-hidden">
                                <div className="px-3 py-1.5 border-b border-white/[0.05] bg-white/[0.02]">
                                  <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">Example {i + 1}</span>
                                </div>
                                <div className="p-3 space-y-2 font-mono text-[11.5px]">
                                  <div><span className="text-slate-500 text-[10px] font-bold">Input</span><pre className="text-sky-300 mt-0.5 whitespace-pre-wrap">{inp}</pre></div>
                                  <div><span className="text-slate-500 text-[10px] font-bold">Output</span><pre className="text-emerald-300 mt-0.5 whitespace-pre-wrap">{out}</pre></div>
                                </div>
                              </div>
                            )
                          })}
                          {sections.map((sec, i) => <SectionBlock key={i} name={sec.name} content={sec.content} />)}
                        </>
                      )
                    })()}
                  </div>
                </div>
                {/* Resize handle */}
                <div className="absolute top-0 right-0 w-1 h-full cursor-col-resize z-10 group"
                  onMouseDown={e => { probResizing.current = true; probStartX.current = e.clientX; probStartW.current = problemW; document.body.style.cursor = 'col-resize'; e.preventDefault() }}>
                  <div className="w-full h-full bg-white/[0.02] group-hover:bg-blue-500/40 transition-colors" />
                </div>
              </div>

              {/* EDITOR COLUMN */}
              <div className="flex-1 flex flex-col overflow-hidden min-w-0">
                {/* Editor toolbar */}
                <div className="h-11 flex items-center justify-between px-3 border-b border-white/[0.05] bg-[#000000] shrink-0">
                  <div className="flex items-center gap-0.5 overflow-x-auto hide-scrollbar">
                    {LANGUAGES.map(l => (
                      <button key={l.value} onClick={() => setLanguage(l.value)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                          language === l.value
                            ? 'bg-blue-500/15 text-blue-300 border border-blue-500/30'
                            : 'text-slate-500 hover:text-slate-300 hover:bg-white/[0.04]'
                        }`}>
                        <span>{l.label}</span>
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    <button onClick={fetchComplexity} disabled={loadingCx}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-amber-400/80 hover:text-amber-300 hover:bg-amber-500/8 border border-amber-500/15 hover:border-amber-500/30 transition-all disabled:opacity-40">
                      {loadingCx ? <Spinner color="border-amber-500" /> : <Gauge className="h-3.5 w-3.5" aria-hidden="true" />}
                      <span className="hidden md:inline">Complexity</span>
                    </button>
                    <button onClick={bottomTab === 'custom' ? handleRunCustom : handleRunTests} disabled={isRunning || submissionStatus[activeQ]}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.08] transition-all disabled:opacity-40">
                      {isRunning ? <Spinner /> : <svg width="9" height="9" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>}
                      Run
                    </button>
                    <button onClick={handleSubmit} disabled={submitting || submissionStatus[activeQ]}
                      className="relative flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-black text-white overflow-hidden group disabled:opacity-40 transition-all hover:scale-105 active:scale-95">
                      <div className="absolute inset-0 bg-gradient-to-r from-emerald-600 to-teal-500 rounded-lg" />
                      <div className="absolute inset-0 bg-white/0 group-hover:bg-white/10 transition-all rounded-lg" />
                      <span className="relative z-10 flex items-center gap-1.5">
                        {submitting ? <Spinner color="border-white" /> : <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>}
                        {submitting ? 'Running…' : 'Submit'}
                      </span>
                    </button>
                  </div>
                </div>

                {/* Monaco */}
                <div className="flex-1 min-h-0 overflow-hidden">
                  <Editor height="100%"
                    language={LANGUAGES.find(l => l.value === language)?.monaco || language}
                    theme="vs-dark" value={code}
                    onChange={v => setCode(v || '')}
                    onMount={(e, monaco) => { editorRef.current = e; protectedRef.current = attachProtectedRegion(e, monaco, () => starterRef.current) }}
                    options={{ minimap: { enabled: false }, fontSize: 13.5, fontFamily: '"JetBrains Mono","Fira Code",monospace', fontLigatures: true, padding: { top: 16, bottom: 16 }, lineNumbers: 'on', scrollBeyondLastLine: false, renderLineHighlight: 'all', bracketPairColorization: { enabled: true }, smoothScrolling: true, cursorBlinking: 'smooth' }}
                  />
                </div>

                {/* Bottom resize handle */}
                {bottomOpen && (
                  <div className="h-2 shrink-0 cursor-ns-resize group bg-white/[0.03] hover:bg-blue-500/30 transition-colors flex items-center justify-center relative z-20"
                    onMouseDown={e => { btmResizing.current = true; btmStartY.current = e.clientY; btmStartH.current = bottomH; document.body.style.cursor = 'ns-resize'; e.preventDefault() }}>
                    <div className="w-12 h-[2px] rounded-full bg-white/20 group-hover:bg-white/60 transition-colors" />
                  </div>
                )}

                {/* Bottom panel */}
                {bottomOpen ? (
                  <div style={{ height: bottomH }} className="shrink-0 flex flex-col border-t border-white/[0.05] bg-[#080c16] overflow-hidden">
                    <div className="flex items-center justify-between px-4 border-b border-white/[0.05] bg-[#000000] shrink-0 h-9">
                      <div className="flex h-full">
                        {[
                          { id: 'testcases', label: 'Tests', badge: totalCount > 0 ? `${passedCount}/${totalCount}` : null, badgeOk: passedCount === totalCount && totalCount > 0 },
                          { id: 'custom',    label: '⌨️ Custom' },
                        ].map(t => (
                          <button key={t.id} onClick={() => setBottomTab(t.id)}
                            className={`flex items-center gap-2 px-4 text-xs font-semibold border-b-2 transition-all h-full ${
                              bottomTab === t.id ? 'border-blue-500 text-blue-300' : 'border-transparent text-slate-500 hover:text-slate-300'
                            }`}>
                            {t.label}
                            {t.badge && <span className={`text-[9px] font-black px-1.5 py-0.5 rounded-full ${t.badgeOk ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>{t.badge}</span>}
                          </button>
                        ))}
                      </div>
                      <button onClick={() => setBottomOpen(false)} className="text-slate-600 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/[0.05]">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>
                      </button>
                    </div>

                    <div className="flex-1 overflow-hidden">
                      {/* Test Cases */}
                      {bottomTab === 'testcases' && (
                        <div className="flex h-full">
                          <div className="w-24 shrink-0 border-r border-white/[0.05] overflow-y-auto p-2 space-y-1">
                            {testCases.map((_, i) => {
                              const r = tcResults[i]
                              return (
                                <button key={i} onClick={() => setSelectedTC(i)}
                                  className={`w-full flex items-center gap-2 px-2 py-2 rounded-xl text-[11px] font-semibold transition-all ${
                                    selectedTC === i ? 'bg-blue-500/15 text-blue-300 border border-blue-500/25' : 'text-slate-500 hover:bg-white/[0.04] hover:text-slate-300'
                                  }`}>
                                  <span className={`w-5 h-5 rounded-lg flex items-center justify-center text-[9px] font-black shrink-0 ${
                                    !r ? 'bg-white/[0.06] text-slate-600' :
                                    r.passed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                                  }`}>{r ? (r.passed ? '✓' : '✗') : i+1}</span>
                                  Case {i+1}
                                </button>
                              )
                            })}
                          </div>
                          <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">
                            {testCases[selectedTC] ? (() => {
                              const tc = testCases[selectedTC]
                              const r  = tcResults[selectedTC]
                              return (
                                <>
                                  {tc.hidden ? (
                                    <div className="flex flex-col items-center justify-center py-10 text-slate-500">
                                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mb-3 opacity-50">
                                        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
                                        <circle cx="12" cy="12" r="3"/>
                                        <line x1="3" y1="3" x2="21" y2="21"/>
                                      </svg>
                                      <div className="font-semibold text-sm mb-1 uppercase tracking-widest text-white/50">Hidden Test Case</div>
                                      <div className="text-xs text-center opacity-70 mb-4 max-w-[250px]">
                                        The input and expected output for this test case are hidden.
                                      </div>
                                      {r && (
                                        <div className="w-full bg-black/20 border border-white/5 rounded-lg p-3 text-center">
                                          <p className={`text-[10px] font-black uppercase tracking-widest mb-1 ${r.passed ? 'text-emerald-500' : 'text-rose-500'}`}>
                                            YOUR OUTPUT — {r.passed ? '✓ PASSED' : '✗ FAILED'}
                                          </p>
                                          {!r.passed && r.error && (
                                            <p className="text-rose-400 text-[9px] mt-2 whitespace-pre-wrap text-left bg-rose-500/10 p-2 rounded">{r.error}</p>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  ) : (
                                    <>
                                      {[
                                        { label: 'INPUT',           value: tc.input || tc.input_data || '—', color: 'text-sky-300'    },
                                    { label: 'EXPECTED OUTPUT', value: tc.output || tc.expected_output || '—', color: 'text-slate-300' },
                                  ].map(item => (
                                    <div key={item.label}>
                                      <p className="text-[9px] text-slate-600 font-black uppercase tracking-widest mb-1.5">{item.label}</p>
                                      <pre className={`bg-white/[0.03] border border-white/[0.05] rounded-xl px-3 py-2.5 whitespace-pre-wrap break-all leading-relaxed ${item.color}`}>{item.value}</pre>
                                    </div>
                                  ))}
                                  {r && (
                                    <div>
                                      <p className={`text-[9px] font-black uppercase tracking-widest mb-1.5 ${r.passed ? 'text-emerald-500' : 'text-rose-500'}`}>
                                        YOUR OUTPUT — {r.passed ? '✓ PASSED' : '✗ FAILED'}
                                      </p>
                                      <pre className={`rounded-xl px-3 py-2.5 whitespace-pre-wrap break-all leading-relaxed border ${
                                        r.passed ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300' : 'bg-rose-500/5 border-rose-500/20 text-rose-300'
                                      }`}>{r.actual_output || r.error || '—'}</pre>
                                    </div>
                                  )}
                                  {!r && submitting && (
                                    <div className="flex items-center gap-2 text-slate-500 text-xs py-2">
                                      <Spinner color="border-blue-500" /><span>Running tests…</span>
                                    </div>
                                  )}
                                  </>
                                )}
                                </>
                              )
                            })() : <p className="text-slate-600 text-xs text-center py-6">Select a test case</p>}
                          </div>
                        </div>
                      )}

                      {/* Custom Input */}
                      {bottomTab === 'custom' && (
                        <div className="flex h-full">
                          <div className="flex-1 flex flex-col border-r border-white/[0.05]">
                            <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.05] shrink-0">
                              <span className="text-[10px] text-slate-600 font-semibold">Separate cases with <code className="text-slate-400 bg-white/[0.05] px-1 rounded">---</code></span>
                              <button onClick={handleRunCustom} disabled={runningCustom}
                                className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-bold bg-blue-500/10 text-blue-300 border border-blue-500/25 hover:bg-blue-500/20 transition-all disabled:opacity-40">
                                {runningCustom ? <Spinner color="border-blue-400" /> : '▶'} Run
                              </button>
                            </div>
                            <textarea value={customInput} onChange={e => setCustomInput(e.target.value)}
                              placeholder="Enter test input…"
                              className="flex-1 bg-transparent p-3 text-xs font-mono text-slate-300 placeholder-slate-700 resize-none focus:outline-none" />
                          </div>
                          <div className="flex-1 overflow-y-auto p-3 space-y-2">
                            <p className="text-[9px] text-slate-600 font-black uppercase tracking-widest mb-2">OUTPUT</p>
                            {!runningCustom && !customOutput && <p className="text-xs text-slate-600 text-center py-6">Run to see output</p>}
                            {runningCustom && <div className="flex justify-center pt-4"><Spinner color="border-blue-500" /></div>}
                            {!runningCustom && customOutput?.map((r, i) => (
                              <div key={i} className={`rounded-xl border p-3 text-xs font-mono ${r.error ? 'bg-rose-500/5 border-rose-500/20' : 'bg-emerald-500/5 border-emerald-500/20'}`}>
                                <p className={`text-[9px] font-black uppercase tracking-widest mb-1 ${r.error ? 'text-rose-500' : 'text-emerald-500'}`}>Case {i+1}</p>
                                <pre className={`whitespace-pre-wrap break-all ${r.error ? 'text-rose-300' : 'text-emerald-300'}`}>{r.error || r.output || '(empty)'}</pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-7 flex items-center px-4 border-t border-white/[0.05] bg-[#000000] shrink-0">
                    <button onClick={() => setBottomOpen(true)} className="flex items-center gap-1.5 text-[10px] text-slate-600 hover:text-slate-300 transition-colors">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M18 15l-6-6-6 6"/></svg>
                      Show panel
                    </button>
                    {totalCount > 0 && (
                      <span className={`ml-3 text-[9px] font-black px-2 py-0.5 rounded-full ${passedCount === totalCount ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'}`}>
                        {passedCount}/{totalCount} passed
                      </span>
                    )}
                  </div>
                )}

                {/* Submit result banner */}
                {submitResult && (
                  <div className={`shrink-0 flex items-center justify-between px-5 py-2.5 border-t ${
                    submitResult.status === 'passed' ? 'bg-emerald-500/8 border-emerald-500/20' : 'bg-rose-500/8 border-rose-500/20'
                  }`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-base ${submitResult.status === 'passed' ? 'bg-emerald-500/20' : 'bg-rose-500/20'}`}>
                        {submitResult.status === 'passed' ? <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" /> : <XCircle className="h-4 w-4 text-rose-400" aria-hidden="true" />}
                      </div>
                      <div>
                        <p className={`font-bold text-sm ${submitResult.status === 'passed' ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {submitResult.status === 'passed' ? 'All Tests Passed!' : `${submitResult.passed_tests}/${submitResult.total_tests} Tests Passed`}
                        </p>
                        {submitResult.execution_time_ms && <p className="text-[10px] text-slate-500">{Math.round(submitResult.execution_time_ms)}ms execution</p>}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-black text-white leading-none">{submitResult.score}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">points</p>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            /* Empty state */
            <div className="flex flex-1 items-center justify-center p-8">
              <div className="w-full max-w-xl">
                <CoderScene className="mb-4 h-[300px] w-full" interactive={false} fps={30} />
                <h2 className="font-display text-[28px] font-bold tracking-tight text-white">Start a practice set</h2>
                <p className="mt-2 text-[15px] leading-relaxed text-slate-400">
                  Choose a topic and a difficulty in the panel on the right, set how many problems you want, and press Generate.
                  You can also upload a syllabus and we will pick topics from it.
                </p>
                <ul className="mt-8 grid gap-3 sm:grid-cols-3">
                  {[
                    { icon: Languages, l: 'Five languages', d: 'Python, C++, Java, JavaScript and C' },
                    { icon: ShieldCheck, l: 'Hidden tests', d: 'Graded on the server' },
                    { icon: Gauge, l: 'Complexity', d: 'Time and space read from your code' },
                  ].map(f => (
                    <li key={f.l} className="rounded-xl border border-white/10 bg-[#0A0A0A] p-4">
                      <f.icon className="mb-2 h-4 w-4 text-arc" aria-hidden="true" />
                      <div className="text-[14px] font-medium text-white">{f.l}</div>
                      <div className="mt-0.5 text-[13px] text-slate-400">{f.d}</div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* ══ RIGHT ICON RAIL ══ */}
        <div className="w-[76px] shrink-0 flex flex-col border-l border-white/[0.05] bg-[#000000]/80 backdrop-blur-xl relative z-10">
          <IconTab icon={ListChecks} label="Problems"  active={rightPanel === 'questions'}  onClick={() => setRightPanel(p => p === 'questions'  ? null : 'questions')}  badge={questions.length || null} />
          <IconTab icon={Bot} label="Coach" active={rightPanel === 'ai'}         onClick={() => setRightPanel(p => p === 'ai'         ? null : 'ai')}         />
          <IconTab icon={Gauge} label="Complexity" active={rightPanel === 'complexity'} onClick={() => setRightPanel(p => p === 'complexity' ? null : 'complexity')} />
        </div>

        {/* ══ RIGHT SLIDING PANEL ══ */}
        {rightPanel && (
          <div className="w-80 shrink-0 flex flex-col border-l border-white/[0.05] bg-[#000000]/80 backdrop-blur-xl overflow-hidden relative z-10">

            {/* ── QUESTIONS panel ── */}
            {rightPanel === 'questions' && (
              <div className="flex flex-col h-full">
                <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between shrink-0">
                  <span className="text-xs font-black text-white uppercase tracking-widest">Questions</span>
                  {questions.length > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/15 border border-blue-500/25 text-blue-300 font-bold">{questions.length}</span>
                  )}
                </div>

                {/* Generator */}
                <div className="border-b border-white/[0.05] p-3 space-y-2.5">
                  <div className="flex gap-1 p-1 bg-white/[0.03] rounded-xl border border-white/[0.04]">
                    {[['type','Topic'],['upload','Syllabus file']].map(([m,l]) => (
                      <button key={m} onClick={() => setInputMode(m)}
                        className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all ${inputMode === m ? 'bg-blue-600/25 text-violet-200 border border-blue-500/30' : 'text-slate-600 hover:text-slate-300'}`}>{l}</button>
                    ))}
                  </div>

                  {inputMode === 'type' ? (
                    <>
                      <input value={typedTopic} onChange={e => setTypedTopic(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleGenerate()}
                        list="topic-suggestions" placeholder="e.g. binary trees, graphs…"
                        className="w-full px-3 py-2 rounded-xl text-xs bg-white/[0.03] border border-white/[0.06] text-white placeholder-slate-700 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/15 transition-all" />
                      <datalist id="topic-suggestions">{availableTopics.map(t => <option key={t} value={t} />)}</datalist>
                      <div className="flex gap-1">
                        {['easy','medium','hard'].map(d => (
                          <button key={d} onClick={() => setDifficulty(d)}
                            className={`flex-1 py-1.5 rounded-xl text-[10px] font-bold capitalize border transition-all ${
                              difficulty === d ? `${DIFF[d].bg} ${DIFF[d].text} ${DIFF[d].border}` : 'bg-white/[0.02] text-slate-600 border-white/[0.04] hover:text-slate-300'
                            }`}>{d}</button>
                        ))}
                      </div>
                    </>
                  ) : (
                    <>
                      <input type="file" accept=".pdf,.txt,image/*" onChange={e => setFile(e.target.files?.[0])} className="hidden" id="fu" />
                      <label htmlFor="fu" className="flex items-center gap-3 p-3 border-2 border-dashed border-white/[0.06] rounded-xl cursor-pointer hover:border-blue-500/30 hover:bg-blue-500/3 transition-all">
                        {file ? <FileCheck className="h-5 w-5 text-emerald-400" aria-hidden="true" /> : <FileText className="h-5 w-5 text-slate-400" aria-hidden="true" />}
                        <div><p className="text-xs font-semibold text-white">{file ? file.name : 'Upload Syllabus'}</p><p className="text-[10px] text-slate-600">PDF, TXT, or Image</p></div>
                      </label>
                    </>
                  )}

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-500 flex-1">Questions</span>
                    <div className="flex items-center gap-1">
                      {[-1,null,1].map((delta, i) => delta === null
                        ? <span key="n" className="w-8 text-center text-sm font-black text-white">{numQuestions}</span>
                        : <button key={delta} onClick={() => setNumQuestions(n => Math.min(10, Math.max(1, n + delta)))}
                            className="w-6 h-6 rounded-lg bg-white/[0.05] border border-white/[0.07] text-slate-400 hover:text-white hover:bg-white/[0.1] transition-all text-sm flex items-center justify-center font-bold">
                            {delta < 0 ? '−' : '+'}
                          </button>
                      )}
                    </div>
                  </div>

                  <button onClick={handleGenerate} disabled={loading || (inputMode === 'type' ? !typedTopic.trim() : !file)}
                    className="relative w-full py-2.5 rounded-xl text-xs font-black text-white overflow-hidden group disabled:opacity-40 transition-all hover:scale-[1.02] active:scale-95">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600" />
                    <div className="absolute inset-0 bg-white/0 group-hover:bg-white/10 transition-all" />
                    <span className="relative z-10 flex items-center justify-center gap-2">
                      {loading ? <><Spinner color="border-white" /> Generating…</> : <>Generate</>}
                    </span>
                  </button>
                  {genError && <p className="text-[10px] text-rose-400 bg-rose-500/8 border border-rose-500/15 rounded-xl px-3 py-2">{genError}</p>}
                </div>

                {/* Question list */}
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                  {questions.map((qItem, i) => {
                    const s = DIFF[qItem.difficulty] || DIFF.medium
                    const status = submissionStatus[i]
                    return (
                      <button key={i} onClick={() => {
                          if (status && i !== activeQ) {
                            showToast('You have already submitted this question.', 'info')
                            return
                          }
                          setActiveQ(i)
                        }}
                        className={`w-full text-left p-3 rounded-2xl border transition-all ${
                          i === activeQ
                            ? 'bg-gradient-to-br from-blue-500/12 to-cyan-500/8 border-blue-500/30'
                            : 'bg-white/[0.02] border-white/[0.04] hover:bg-white/[0.04] hover:border-white/[0.08]'
                        } ${status ? 'opacity-80' : ''}`}>
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <div className="flex items-center gap-2 min-w-0">
                            {status === 'passed' ? (
                              <span className="w-5 h-5 rounded-lg flex items-center justify-center shrink-0 bg-emerald-500/20 text-emerald-400 text-[10px] font-black">✓</span>
                            ) : status === 'failed' ? (
                              <span className="w-5 h-5 rounded-lg flex items-center justify-center shrink-0 bg-rose-500/20 text-rose-400 text-[10px] font-black">✗</span>
                            ) : (
                              <span className={`text-[9px] font-black w-5 h-5 rounded-lg flex items-center justify-center shrink-0 ${i === activeQ ? 'bg-blue-500/30 text-blue-300' : 'bg-white/[0.05] text-slate-600'}`}>{i+1}</span>
                            )}
                            <span className="text-[11px] font-semibold text-white leading-tight line-clamp-2">{qItem.title}</span>
                          </div>
                          <span className={`text-[8px] px-1.5 py-0.5 rounded-full border font-black shrink-0 uppercase ${s.text} ${s.bg} ${s.border}`}>{qItem.difficulty}</span>
                        </div>
                        <p className="text-[9px] text-slate-600 ml-7">{qItem.topic || 'General'}</p>
                      </button>
                    )
                  })}
                  {questions.length === 0 && (
                    <div className="text-center py-10">
                      <p className="text-xs text-slate-600">Generate questions above</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── AI FEEDBACK panel ── */}
            {rightPanel === 'ai' && (
              <div className="flex flex-col h-full">
                <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-white uppercase tracking-widest">AI Feedback</span>
                    {aiFeedback && (
                      <span className={`text-[9px] font-black px-2 py-0.5 rounded-full ${aiFeedback.logic_correctness >= 80 ? 'bg-emerald-500/15 text-emerald-400' : aiFeedback.logic_correctness >= 50 ? 'bg-amber-500/15 text-amber-400' : 'bg-rose-500/15 text-rose-400'}`}>
                        {aiFeedback.logic_correctness}%
                      </span>
                    )}
                  </div>
                  <button onClick={() => fetchAI(submitResult)} disabled={loadingAI}
                    className="text-[10px] font-bold text-blue-400 hover:text-blue-300 disabled:opacity-40 transition-colors px-2 py-1 rounded-lg hover:bg-blue-500/10">
                    {loadingAI ? '…' : '↻'}
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {loadingAI && <div className="flex flex-col items-center justify-center py-16 gap-3"><Spinner color="border-blue-500" /><p className="text-xs text-slate-500">Analyzing…</p></div>}
                  {!loadingAI && !aiFeedback && (
                    <div className="flex flex-col items-center justify-center text-center gap-4 py-8 px-4 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
                      <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-300"><Bot className="h-7 w-7" aria-hidden="true" /></div>
                      <div><p className="text-sm font-bold text-white mb-1">AI Code Review</p><p className="text-xs text-slate-500 leading-relaxed">Submit code to get intelligent analysis and suggestions.</p></div>
                      <button onClick={() => fetchAI(submitResult)} className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600/20 text-blue-300 border border-blue-500/30 hover:bg-blue-600/30 transition-all">Analyze Now</button>
                    </div>
                  )}
                  {!loadingAI && aiFeedback && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-gradient-to-br from-blue-500/8 to-cyan-500/5 border border-blue-500/15">
                        <ScoreRing value={aiFeedback.logic_correctness} />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-black text-white mb-1">Logic Score</p>
                          <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-3">{aiFeedback.analysis}</p>
                        </div>
                      </div>
                      {aiFeedback.breakdown && Object.keys(aiFeedback.breakdown).length > 0 && (
                        <div className="p-3.5 rounded-2xl bg-white/[0.025] border border-white/[0.05] space-y-2.5">
                          <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Breakdown</p>
                          {Object.entries(aiFeedback.breakdown).map(([k, v]) => (
                            <div key={k}>
                              <div className="flex justify-between text-[10px] mb-1.5">
                                <span className="text-slate-400 capitalize">{k.replace(/_/g,' ')}</span>
                                <span className="font-black" style={{ color: v >= 80 ? '#10b981' : v >= 50 ? '#f59e0b' : '#ef4444' }}>{v}%</span>
                              </div>
                              <div className="h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                                <div className="h-full rounded-full transition-all duration-700"
                                  style={{ width:`${v}%`, background: v >= 80 ? '#10b981' : v >= 50 ? '#f59e0b' : '#ef4444' }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      {aiFeedback.suggestions?.length > 0 && (
                        <div className="p-3.5 rounded-2xl bg-white/[0.025] border border-white/[0.05] space-y-2">
                          <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Suggestions</p>
                          {aiFeedback.suggestions.map((s, i) => (
                            <div key={i} className="flex gap-2 text-[11px] text-slate-300 leading-relaxed">
                              <span className="text-blue-400 shrink-0 mt-0.5 font-bold">›</span><span>{s}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* ── AI Feedback Chat ── */}
                  {!loadingAI && (
                    <div className="rounded-xl overflow-hidden" style={{ background: '#0F0F0F', border: '1px solid rgba(59,140,255,0.3)' }}>
                      {/* Chat header */}
                      <div className="px-3 py-2.5 flex items-center justify-between" style={{ background: 'rgba(59,140,255,0.12)', borderBottom: '1px solid rgba(59,140,255,0.2)' }}>
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 rounded-full flex items-center justify-center text-[11px]" style={{ background: '#1A1A1A' }}><Bot className="h-3 w-3 text-arc" aria-hidden="true" /></div>
                          <span className="text-xs font-bold text-white">Ask AI Coach</span>
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase" style={{ background: 'rgba(59,140,255,0.25)', color: '#5AA2FF' }}>NVIDIA</span>
                        </div>
                        {grokMessages.length > 0 && (
                          <button
                            onClick={() => setGrokMessages([])}
                            className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
                            title="Clear chat"
                          >
                            Clear
                          </button>
                        )}
                      </div>

                      {/* Chat messages */}
                      <div className="overflow-y-auto p-3 space-y-3" style={{ maxHeight: '320px', minHeight: grokMessages.length === 0 ? '0px' : '120px' }}>
                        {grokMessages.length === 0 && (
                          <div className="text-center py-4">
                            <div className="text-2xl mb-2"><Bot className="h-3 w-3 text-arc" aria-hidden="true" /></div>
                            <div className="text-[11px] text-slate-400 mb-1">Ask anything about your code</div>
                            <div className="text-[10px] text-slate-600">e.g. "Why is my solution O(n²)?" or "How do I fix this bug?"</div>
                          </div>
                        )}
                        {grokMessages.map((msg, i) => (
                          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            {msg.role === 'assistant' && (
                              <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] shrink-0 mr-2 mt-0.5" style={{ background: '#1A1A1A' }}><Bot className="h-3 w-3 text-arc" aria-hidden="true" /></div>
                            )}
                            <div
                              className="rounded-xl px-3 py-2 text-[11px] leading-relaxed max-w-[85%]"
                              style={msg.role === 'user'
                                ? { background: 'rgba(59,140,255,0.25)', color: '#D0D0D0', borderBottomRightRadius: '4px' }
                                : { background: 'rgba(255,255,255,0.05)', color: '#B0B0B0', borderBottomLeftRadius: '4px', border: '1px solid rgba(255,255,255,0.07)' }
                              }
                            >
                              {msg.content}
                            </div>
                          </div>
                        ))}
                        {grokLoading && (
                          <div className="flex justify-start">
                            <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] shrink-0 mr-2 mt-0.5" style={{ background: '#1A1A1A' }}><Bot className="h-3 w-3 text-arc" aria-hidden="true" /></div>
                            <div className="rounded-xl px-3 py-2" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.07)' }}>
                              <div className="flex gap-1 items-center h-4">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                              </div>
                            </div>
                          </div>
                        )}
                        <div ref={grokChatEndRef} />
                      </div>

                      {/* Quick prompts */}
                      {grokMessages.length === 0 && (
                        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
                          {[
                            'Why is my code wrong?',
                            'Explain the time complexity',
                            'How can I optimize this?',
                            'What edge cases am I missing?',
                          ].map(prompt => (
                            <button
                              key={prompt}
                              onClick={() => sendGrokMessage(prompt)}
                              disabled={grokLoading}
                              className="px-2 py-1 rounded-full text-[10px] transition-all hover:scale-105 active:scale-95 disabled:opacity-40"
                              style={{ background: 'rgba(59,140,255,0.15)', color: '#5AA2FF', border: '1px solid rgba(59,140,255,0.25)' }}
                            >
                              {prompt}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Input box */}
                      <div className="p-2.5 pt-0" style={{ borderTop: grokMessages.length > 0 ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
                        <div className="flex gap-2 items-end rounded-xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(59,140,255,0.25)' }}>
                          <textarea
                            value={grokInput}
                            onChange={e => setGrokInput(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                sendGrokMessage()
                              }
                            }}
                            placeholder="Ask about your code… (Enter to send)"
                            disabled={grokLoading}
                            rows={1}
                            className="flex-1 bg-transparent text-[11px] text-slate-200 placeholder-slate-600 resize-none outline-none px-3 py-2.5 disabled:opacity-50"
                            style={{ maxHeight: '80px', lineHeight: '1.5' }}
                          />
                          <button
                            onClick={() => sendGrokMessage()}
                            disabled={grokLoading || !grokInput.trim()}
                            className="m-1.5 w-7 h-7 rounded-lg flex items-center justify-center transition-all hover:scale-110 active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
                            style={{ background: grokInput.trim() ? 'linear-gradient(135deg,#2B70E8,#A387FF)' : 'rgba(59,140,255,0.2)' }}
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                            </svg>
                          </button>
                        </div>
                        <div className="text-[9px] text-slate-600 mt-1 px-1">Shift+Enter for new line · Powered by NVIDIA NIM</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── COMPLEXITY panel ── */}
            {rightPanel === 'complexity' && (
              <div className="flex flex-col h-full">
                <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between shrink-0">
                  <span className="text-xs font-black text-white uppercase tracking-widest">Complexity</span>
                  <button onClick={fetchComplexity} disabled={loadingCx}
                    className="text-[10px] font-bold text-amber-400 hover:text-amber-300 disabled:opacity-40 transition-colors px-2 py-1 rounded-lg hover:bg-amber-500/10">
                    {loadingCx ? '…' : '↻ Analyze'}
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {loadingCx && <div className="flex flex-col items-center justify-center h-full gap-3"><Spinner color="border-amber-500" /><p className="text-xs text-slate-500">Analyzing…</p></div>}
                  {!loadingCx && !complexity && (
                    <div className="flex flex-col items-center justify-center h-full text-center gap-4 p-6">
                      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-300"><Gauge className="h-7 w-7" aria-hidden="true" /></div>
                      <div><p className="text-sm font-bold text-white mb-1">Complexity Analyzer</p><p className="text-xs text-slate-500 leading-relaxed">Analyze time & space complexity of your solution.</p></div>
                      <button onClick={fetchComplexity} className="px-4 py-2 rounded-xl text-xs font-bold bg-amber-600/20 text-amber-300 border border-amber-500/30 hover:bg-amber-600/30 transition-all">Analyze Now</button>
                    </div>
                  )}
                  {!loadingCx && complexity && (
                    <div className="p-4 space-y-3">
                      {[['Time Complexity', complexity.time_complexity, { Best:'#10b981', Avg:'#f59e0b', Worst:'#ef4444' }],
                        ['Space Complexity', complexity.space_complexity, { Best:'#A387FF', Avg:'#A387FF', Worst:'#A387FF' }]
                      ].map(([title, cx, colors]) => cx && (
                        <div key={title} className="p-3.5 rounded-2xl bg-white/[0.025] border border-white/[0.05]">
                          <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-3">{title}</p>
                          <div className="grid grid-cols-3 gap-2">
                            {[['Best', cx.best], ['Avg', cx.average], ['Worst', cx.worst]].map(([l, v]) => (
                              <div key={l} className="text-center p-2 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                                <p className="text-[8px] text-slate-600 font-bold mb-1 uppercase">{l}</p>
                                <p className="text-xs font-black font-mono" style={{ color: colors[l] }}>{v || 'N/A'}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                      {complexity.analysis && (
                        <div className="p-3.5 rounded-2xl bg-white/[0.025] border border-white/[0.05]">
                          <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-2">Analysis</p>
                          <p className="text-[11px] text-slate-300 leading-relaxed">{complexity.analysis}</p>
                        </div>
                      )}
                      {complexity.suggestions?.length > 0 && (
                        <div className="p-3.5 rounded-2xl bg-white/[0.025] border border-white/[0.05] space-y-2">
                          <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest">Optimizations</p>
                          {complexity.suggestions.map((s, i) => (
                            <div key={i} className="flex gap-2 text-[11px] text-slate-300 leading-relaxed">
                              <span className="text-amber-400 shrink-0 mt-0.5 font-bold">›</span><span>{s}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── COMPLETION MODAL ── */}
      {showCompletionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm transition-opacity duration-300">
          <div className="bg-[#0f1524] border border-white/10 rounded-2xl shadow-2xl p-8 max-w-sm w-full relative text-center">
            <button onClick={() => setShowCompletionModal(false)} className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
            <div className="w-20 h-20 mx-auto bg-gradient-to-br from-emerald-400 to-teal-500 rounded-full flex items-center justify-center mb-6 shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="h-9 w-9 text-black" aria-hidden="true" />
            </div>
            <h2 className="text-2xl font-black text-white mb-2">Practice Complete!</h2>
            <p className="text-slate-400 text-sm mb-6">You have finished this practice session.</p>
            
            {(() => {
              const passedCount = Object.values(submissionStatus).filter(s => s === 'passed').length
              const laggingTopics = [...new Set(questions.filter((_, i) => submissionStatus[i] === 'failed').map(q => q.topic).filter(Boolean))]
              return (
                <div className="mb-8 space-y-4">
                  <div className="flex items-center justify-center gap-6">
                    <div className="text-center">
                      <p className="text-2xl font-black text-emerald-400">{passedCount}</p>
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Passed</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-black text-rose-400">{questions.length - passedCount}</p>
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Failed</p>
                    </div>
                  </div>
                  {laggingTopics.length > 0 && (
                    <div className="pt-4 border-t border-white/5">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-rose-400 mb-2">Areas for Improvement</p>
                      <div className="flex flex-wrap justify-center gap-2">
                        {laggingTopics.map(topic => (
                          <span key={topic} className="px-2.5 py-1 rounded-md text-[10px] font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/20">
                            #{topic}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {laggingTopics.length === 0 && (
                    <div className="pt-4 border-t border-white/5">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">Perfect score</p>
                    </div>
                  )}
                </div>
              )
            })()}

            <button 
              onClick={() => { setShowCompletionModal(false); nav('/profile') }}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white font-bold text-sm transition-all shadow-lg shadow-blue-500/25 active:scale-[0.98]"
            >
              View Learning Chart
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
