import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useEditorTheme, ThemeToggle } from '../context/ThemeContext'
import api from '../services/api'
import Editor from '@monaco-editor/react'
import Logo from '../components/Logo'
import Icon from '../components/Icons'
import { DifficultyTag } from '../components/Avatar'
import ProblemStatement from '../components/ProblemStatement'
import CoachChat from '../components/CoachChat'
import { LogicReport, ComplexityReport, TestCaseViewer, Spinner, PanelNote } from '../components/Analysis'
import { attachProtectedRegion } from '../utils/protectedRegion'
import { registerEditorThemes, EDITOR_FONT } from '../utils/monacoTheme'
import { parseTestCases, parseStarterCode, caseIO } from '../utils/problem'
import { balloonFill } from '../utils/balloons'

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const LANGUAGES = [
  { value: 'python', label: 'Python', monaco: 'python' },
  { value: 'cpp', label: 'C++', monaco: 'cpp' },
  { value: 'java', label: 'Java', monaco: 'java' },
  { value: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { value: 'c', label: 'C', monaco: 'c' },
]

const DIFF_COLOR = { easy: 'grass', medium: 'sun', hard: 'tomato' }

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────
export default function OfflinePractice() {
  const { user } = useAuth()
  const nav = useNavigate()
  const editorTheme = useEditorTheme()

  // Right panel: null | 'questions' | 'ai' | 'complexity'
  const [rightPanel, setRightPanel] = useState(null)

  // Generator
  const [inputMode, setInputMode] = useState('type')
  const [typedTopic, setTypedTopic] = useState('')
  const [difficulty, setDifficulty] = useState(() => {
    const r = user?.rating || 1000
    return r < 900 ? 'easy' : r < 1300 ? 'medium' : 'hard'
  })
  const [numQuestions, setNumQuestions] = useState(3)
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [genError, setGenError] = useState('')
  const [availableTopics, setAvailableTopics] = useState([])

  // Questions
  const [questions, setQuestions] = useState([])
  const [activeQ, setActiveQ] = useState(0)
  const [submissionStatus, setSubmissionStatus] = useState({})
  const [showCompletionModal, setShowCompletionModal] = useState(false)

  // Editor
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState('')
  const editorRef = useRef(null)
  const protectedRef = useRef(null)

  // Problem panel width
  const [problemW, setProblemW] = useState(420)
  const probResizing = useRef(false)
  const probStartX = useRef(0)
  const probStartW = useRef(0)

  // Questions already seen this session, so a new batch never repeats
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
  const [bottomTab, setBottomTab] = useState('testcases')
  const [bottomH, setBottomH] = useState(260)
  const [bottomOpen, setBottomOpen] = useState(true)
  const btmResizing = useRef(false)
  const btmStartY = useRef(0)
  const btmStartH = useRef(0)

  // Test cases
  const [testCases, setTestCases] = useState([])
  const [selectedTC, setSelectedTC] = useState(0)
  const [tcResults, setTcResults] = useState([])

  // Run / submit
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)

  // Custom input
  const [customInput, setCustomInput] = useState('')
  const [customOutput, setCustomOutput] = useState(null)
  const [runningCustom, setRunningCustom] = useState(false)

  // AI feedback
  const [aiFeedback, setAiFeedback] = useState(null)
  const [loadingAI, setLoadingAI] = useState(false)

  // Coach chat
  const [coachMessages, setCoachMessages] = useState([])
  const [coachInput, setCoachInput] = useState('')
  const [coachLoading, setCoachLoading] = useState(false)

  // Complexity
  const [complexity, setComplexity] = useState(null)
  const [loadingCx, setLoadingCx] = useState(false)

  // Toast
  const [toast, setToast] = useState({ msg: '', type: 'info', visible: false })
  const toastTimer = useRef(null)
  const showToast = useCallback((msg, type = 'info') => {
    if (toastTimer.current) clearTimeout(toastTimer.current)
    setToast({ msg, type, visible: true })
    toastTimer.current = setTimeout(() => setToast((t) => ({ ...t, visible: false })), 2800)
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
      'arrays', 'strings', 'graphs', 'trees', 'dynamic programming',
      'sorting', 'hashing', 'stacks', 'queues', 'greedy',
      'backtracking', 'recursion', 'linked lists', 'math', 'two pointers',
    ]))
  }, [])

  useEffect(() => {
    const q = questions[activeQ]; if (!q) return
    setTestCases(parseTestCases(q.test_cases).map((tc, i) => ({ ...tc, hidden: i > 0 })))
    setTcResults([]); setSelectedTC(0); setSubmitResult(null)
    setAiFeedback(null); setComplexity(null); setCoachMessages([]); setCoachInput('')
    setCode(parseStarterCode(q.starter_code, language))
  }, [activeQ, questions])

  useEffect(() => {
    const q = questions[activeQ]
    if (q) setCode(parseStarterCode(q.starter_code, language))
  }, [language])

  // Problem panel resize
  useEffect(() => {
    const onMove = (e) => {
      if (!probResizing.current) return
      setProblemW(Math.min(640, Math.max(300, probStartW.current + e.clientX - probStartX.current)))
      triggerLayout()
    }
    const onUp = () => { if (probResizing.current) { probResizing.current = false; document.body.style.cursor = ''; triggerLayout() } }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [triggerLayout])

  // Bottom panel resize
  useEffect(() => {
    const onMove = (e) => {
      if (!btmResizing.current) return
      setBottomH(Math.min(520, Math.max(160, btmStartH.current + btmStartY.current - e.clientY)))
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
        questions.forEach((q) => q.title && addUsedTitle(q.title))
        for (let i = 0; i < numQuestions; i++) {
          const used = [...sessionUsedTitles.current, ...generated.map((q) => q.title?.toLowerCase()).filter(Boolean)]
          const { data } = await api.post('/questions/generate', { difficulty, topic: typedTopic.trim(), num_test_cases: 5, exclude_titles: used })
          const { data: saved } = await api.post('/questions', data)
          generated.push({ ...data, id: saved.id })
          if (data.title) addUsedTitle(data.title)
        }
        setQuestions(generated); setActiveQ(0)
      }
      setRightPanel('questions')
    } catch (err) {
      setGenError(err.response?.data?.detail || 'Could not generate questions. Try again.')
    } finally { setLoading(false) }
  }

  const handleSubmit = async () => {
    const q = questions[activeQ]; if (!q) return
    setSubmitting(true); setSubmitResult(null); setBottomTab('testcases'); setBottomOpen(true)
    try {
      const { data: dbQ } = await api.post('/questions', { title: q.title, description: q.description, difficulty: q.difficulty, topic: q.topic || 'general', starter_code: q.starter_code, test_cases: q.test_cases })
      const { data: lobby } = await api.post('/lobbies', { name: 'solo_' + Math.random().toString(36).slice(7), max_players: 2, time_limit: 3600 })
      await api.post(`/lobbies/${lobby.id}/join`, {})
      const { data: sub } = await api.post('/submissions', { code, language, question_id: dbQ.id })
      setSubmitResult(sub)
      if (sub.test_case_details) setTcResults(sub.test_case_details)
      setSubmissionStatus((prev) => ({ ...prev, [activeQ]: sub.status === 'passed' ? 'passed' : 'failed' }))
      fetchAI(sub)
    } catch (err) { showToast(err.response?.data?.detail || 'Submission failed', 'error') }
    finally { setSubmitting(false) }
  }

  const handleRunTests = async () => {
    const q = questions[activeQ]; if (!q) return
    setSubmitting(true); setSubmitResult(null); setBottomTab('testcases'); setBottomOpen(true)
    try {
      const { data: dbQ } = await api.post('/questions', { title: q.title, description: q.description, difficulty: q.difficulty, topic: q.topic || 'general', starter_code: q.starter_code, test_cases: q.test_cases })
      const { data: sub } = await api.post('/run-tests', { code, language, question_id: dbQ.id })
      setSubmitResult(sub)
      if (sub.test_case_details) setTcResults(sub.test_case_details)
    } catch (err) { showToast(err.response?.data?.detail || 'Run failed', 'error') }
    finally { setSubmitting(false) }
  }

  const handleRunCustom = async () => {
    setRunningCustom(true); setCustomOutput(null)
    try {
      const inputs = customInput.split('\n---').map((s) => s.trim()).filter(Boolean)
      const { data } = await api.post('/execute', { code, language, inputs: inputs.length ? inputs : [customInput] })
      setCustomOutput(data.results || [])
    } catch (err) { setCustomOutput([{ error: err.response?.data?.detail || 'Execution failed' }]) }
    finally { setRunningCustom(false) }
  }

  const fetchAI = async (sub) => {
    const q = questions[activeQ]; if (!q) return
    setLoadingAI(true); setRightPanel('ai')
    try {
      const { data } = await api.post('/analyze-code', { code, language, problem_statement: `${q.title}\n\n${q.description || ''}`, test_results: sub?.test_case_details || [], passed_tests: sub?.passed_tests ?? 0, total_tests: sub?.total_tests ?? 0 })
      setAiFeedback(data)
    } catch { setAiFeedback(null) }
    finally { setLoadingAI(false) }
  }

  const fetchComplexity = async () => {
    const q = questions[activeQ]; if (!q) return
    setLoadingCx(true); setRightPanel('complexity')
    try {
      const { data } = await api.post('/analyze-complexity', { code, language, problem_statement: `${q.title}\n\n${q.description || ''}` })
      setComplexity(data)
    } catch { setComplexity(null) }
    finally { setLoadingCx(false) }
  }

  async function sendCoachMessage(messageText) {
    const text = (messageText || coachInput).trim()
    if (!text || coachLoading) return

    const userMsg = { role: 'user', content: text }
    setCoachMessages((prev) => [...prev, userMsg])
    setCoachInput('')
    setCoachLoading(true)

    const qItem = questions[activeQ]
    try {
      const { data } = await api.post('/ai-feedback', {
        message: text,
        code: code || '',
        language,
        problem_statement: qItem ? `${qItem.title}\n\n${qItem.description || ''}` : '',
        history: coachMessages,
      })
      setCoachMessages((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Could not get a reply from the coach. Try again.'
      setCoachMessages((prev) => [...prev, { role: 'assistant', content: errMsg }])
    } finally {
      setCoachLoading(false)
    }
  }

  const q = questions[activeQ]
  const passedCount = tcResults.filter((r) => r.passed).length
  const totalCount = tcResults.length
  const isRunning = bottomTab === 'custom' ? runningCustom : submitting

  const caseViews = testCases.map((tc, i) => {
    const { input, output } = caseIO(tc)
    const r = tcResults[i]
    return {
      input,
      expected_output: output,
      actual_output: r?.actual_output ?? null,
      passed: r ? r.passed : null,
      error: r?.error ?? null,
      hidden: tc.hidden,
    }
  })

  // ── Pieces reused in more than one place ─────────────────────────────────
  const generator = (
    <div className="space-y-4">
      <div className="seg w-full" role="group" aria-label="Where questions come from">
        {[['type', 'A topic'], ['upload', 'A syllabus file']].map(([m, l]) => (
          <button key={m} aria-pressed={inputMode === m} onClick={() => setInputMode(m)} className="flex-1">{l}</button>
        ))}
      </div>

      {inputMode === 'type' ? (
        <>
          <div>
            <label htmlFor="topic" className="label">Topic</label>
            <input
              id="topic"
              value={typedTopic}
              onChange={(e) => setTypedTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              list="topic-suggestions"
              placeholder="For example: binary trees, graphs"
              className="field"
            />
            <datalist id="topic-suggestions">{availableTopics.map((t) => <option key={t} value={t} />)}</datalist>
          </div>
          <fieldset>
            <legend className="label">Difficulty</legend>
            <div className="seg w-full" role="group">
              {['easy', 'medium', 'hard'].map((d) => (
                <button key={d} aria-pressed={difficulty === d} onClick={() => setDifficulty(d)} className="flex-1 capitalize">{d}</button>
              ))}
            </div>
          </fieldset>
        </>
      ) : (
        <div>
          <input type="file" accept=".pdf,.txt,image/*" onChange={(e) => setFile(e.target.files?.[0])} className="sr-only" id="syllabus-file" />
          <label
            htmlFor="syllabus-file"
            className="flex cursor-pointer items-center gap-3 rounded-md border border-dashed border-line-strong bg-sunken p-4 transition-colors hover:border-ink-3"
          >
            <Icon name={file ? 'file' : 'upload'} size={22} />
            <span>
              <span className="block font-semibold">{file ? file.name : 'Choose a syllabus'}</span>
              <span className="block text-sm text-ink-3">PDF, text file or image</span>
            </span>
          </label>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="label !mb-0">How many questions</span>
        <div className="flex items-center gap-1">
          <button onClick={() => setNumQuestions((n) => Math.max(1, n - 1))} className="btn btn-secondary btn-icon h-8 w-8" aria-label="Fewer questions">
            <Icon name="minus" size={14} />
          </button>
          <span className="numeral w-9 text-center text-xl">{numQuestions}</span>
          <button onClick={() => setNumQuestions((n) => Math.min(10, n + 1))} className="btn btn-secondary btn-icon h-8 w-8" aria-label="More questions">
            <Icon name="plus" size={14} />
          </button>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading || (inputMode === 'type' ? !typedTopic.trim() : !file)}
        className="btn btn-primary w-full"
      >
        {loading ? (
          <>
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />
            Writing {numQuestions === 1 ? 'the question' : 'the questions'}…
          </>
        ) : (
          'Generate questions'
        )}
      </button>
      {genError && <p role="alert" className="text-sm font-medium text-tomato-ink">{genError}</p>}
    </div>
  )

  const panelTabs = [
    ['questions', 'Questions'],
    ['ai', 'Coach'],
    ['complexity', 'Complexity'],
  ]

  // ── RENDER ────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-paper">
      {toast.visible && (
        <div className="pointer-events-none fixed left-1/2 top-4 z-50 -translate-x-1/2 animate-fade-in" role="status">
          <div className={`flex items-center gap-2.5 rounded-md border px-4 py-2.5 text-sm font-semibold shadow-float ${
            toast.type === 'error' ? 'border-tomato-ink/50 bg-panel text-tomato-ink' : 'border-line-strong bg-panel text-ink'
          }`}>
            <Icon name={toast.type === 'error' ? 'alert' : 'info'} size={16} />
            {toast.msg}
          </div>
        </div>
      )}

      {/* Top bar */}
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line px-4">
        <Link to="/dashboard" className="btn btn-quiet btn-sm -ml-2" aria-label="Back to the dashboard">
          <Icon name="arrow-left" size={16} />
          <span className="hidden sm:inline">Dashboard</span>
        </Link>
        <span className="hidden h-5 w-px bg-line md:block" />
        <Logo size={24} wordmark={false} className="hidden md:inline-flex" />
        <span className="hidden font-bold md:block">Practice arena</span>

        {q && (
          <div className="mx-auto flex min-w-0 items-center gap-2.5">
            <DifficultyTag level={q.difficulty} />
            <span className="max-w-[26rem] truncate font-semibold">{q.title}</span>
          </div>
        )}

        <div className="ml-auto flex items-center gap-1">
          {user?.rating && (
            <span className="mr-2 hidden items-baseline gap-1.5 sm:flex">
              <span className="numeral text-xl">{Math.round(user.rating)}</span>
              <span className="text-xs text-ink-3">rating</span>
            </span>
          )}
          <ThemeToggle />
          <button
            onClick={() => setRightPanel((p) => (p ? null : 'questions'))}
            className="btn btn-quiet btn-icon"
            aria-label={rightPanel ? 'Hide side panel' : 'Show side panel'}
            aria-pressed={!!rightPanel}
          >
            <Icon name="sidebar" size={18} />
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1">
          {q ? (
            <>
              {/* Problem */}
              <section style={{ width: problemW }} className="relative shrink-0 overflow-y-auto border-r border-line p-6">
                <ProblemStatement question={q} exampleCount={2} />
                <div
                  className="absolute right-0 top-0 z-10 h-full w-1.5 cursor-col-resize transition-colors hover:bg-sky/40"
                  onMouseDown={(e) => { probResizing.current = true; probStartX.current = e.clientX; probStartW.current = problemW; document.body.style.cursor = 'col-resize'; e.preventDefault() }}
                  role="separator"
                  aria-orientation="vertical"
                  aria-label="Resize problem panel"
                />
              </section>

              {/* Editor column */}
              <div className="flex min-w-0 flex-1 flex-col">
                <div className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-line px-3">
                  <div className="seg" role="group" aria-label="Language">
                    {LANGUAGES.map((l) => (
                      <button key={l.value} aria-pressed={language === l.value} onClick={() => setLanguage(l.value)}>{l.label}</button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={fetchComplexity} disabled={loadingCx} className="btn btn-quiet btn-sm">
                      {loadingCx ? <Spinner /> : <Icon name="gauge" size={16} />}
                      <span className="hidden md:inline">Complexity</span>
                    </button>
                    <button
                      onClick={bottomTab === 'custom' ? handleRunCustom : handleRunTests}
                      disabled={isRunning || submissionStatus[activeQ]}
                      className="btn btn-secondary btn-sm"
                    >
                      {isRunning ? <Spinner /> : <Icon name="play" size={12} />}
                      Run tests
                    </button>
                    <button onClick={handleSubmit} disabled={submitting || submissionStatus[activeQ]} className="btn btn-primary btn-sm">
                      {submitting ? <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-paper/30 border-t-paper" /> : <Icon name="check" size={14} strokeWidth={2.4} />}
                      {submitting ? 'Running…' : 'Submit'}
                    </button>
                  </div>
                </div>

                <div className="min-h-0 flex-1 overflow-hidden">
                  <Editor
                    height="100%"
                    language={LANGUAGES.find((l) => l.value === language)?.monaco || language}
                    theme={editorTheme}
                    value={code}
                    onChange={(v) => setCode(v || '')}
                    beforeMount={registerEditorThemes}
                    onMount={(e, monaco) => { editorRef.current = e; protectedRef.current = attachProtectedRegion(e, monaco) }}
                    options={{
                      minimap: { enabled: false }, fontSize: 14, fontFamily: EDITOR_FONT, fontLigatures: true,
                      padding: { top: 16, bottom: 16 }, lineNumbers: 'on', scrollBeyondLastLine: false,
                      renderLineHighlight: 'line', bracketPairColorization: { enabled: true }, automaticLayout: true,
                    }}
                  />
                </div>

                {submitResult && (
                  <div className={`flex shrink-0 items-center justify-between gap-4 border-t px-5 py-2.5 ${
                    submitResult.status === 'passed' ? 'border-grass-ink/40 bg-grass/10' : 'border-tomato-ink/40 bg-tomato/10'
                  }`} role="status">
                    <div className="flex items-center gap-3">
                      <Icon name={submitResult.status === 'passed' ? 'check-circle' : 'x-circle'} size={22} className={submitResult.status === 'passed' ? 'text-grass-ink' : 'text-tomato-ink'} />
                      <div>
                        <div className="font-bold">
                          {submitResult.status === 'passed' ? 'All tests passed' : `${submitResult.passed_tests} of ${submitResult.total_tests} tests passed`}
                        </div>
                        {submitResult.execution_time_ms && <div className="text-xs text-ink-3">{Math.round(submitResult.execution_time_ms)} ms</div>}
                      </div>
                    </div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="numeral text-3xl">{submitResult.score}</span>
                      <span className="text-sm text-ink-3">points</span>
                    </div>
                  </div>
                )}

                {bottomOpen && (
                  <div
                    className="h-1.5 shrink-0 cursor-row-resize bg-line transition-colors hover:bg-sky/50"
                    onMouseDown={(e) => { btmResizing.current = true; btmStartY.current = e.clientY; btmStartH.current = bottomH; document.body.style.cursor = 'row-resize'; e.preventDefault() }}
                    role="separator"
                    aria-orientation="horizontal"
                    aria-label="Resize results panel"
                  />
                )}

                {bottomOpen ? (
                  <div style={{ height: bottomH }} className="flex shrink-0 flex-col overflow-hidden bg-panel">
                    <div className="flex shrink-0 items-center justify-between border-b border-line pl-2 pr-2">
                      <div className="tabs border-b-0" role="tablist">
                        <button role="tab" aria-selected={bottomTab === 'testcases'} onClick={() => setBottomTab('testcases')} className="tab">
                          Test cases
                          {totalCount > 0 && (
                            <span className="chip h-5 px-2" style={{ color: passedCount === totalCount ? 'rgb(var(--grass-ink))' : 'rgb(var(--tomato-ink))' }}>
                              {passedCount} of {totalCount}
                            </span>
                          )}
                        </button>
                        <button role="tab" aria-selected={bottomTab === 'custom'} onClick={() => setBottomTab('custom')} className="tab">Custom input</button>
                      </div>
                      <button onClick={() => setBottomOpen(false)} className="btn btn-quiet btn-icon h-8 w-8" aria-label="Hide results panel">
                        <Icon name="chevron-down" size={16} />
                      </button>
                    </div>

                    <div className="min-h-0 flex-1">
                      {bottomTab === 'testcases' && (
                        <TestCaseViewer cases={caseViews} selected={selectedTC} onSelect={setSelectedTC} />
                      )}

                      {bottomTab === 'custom' && (
                        <div className="flex h-full">
                          <div className="flex flex-1 flex-col border-r border-line">
                            <div className="flex items-center justify-between border-b border-line px-3 py-2">
                              <span className="text-sm text-ink-3">Separate several inputs with <code className="rounded bg-sunken px-1 font-mono">---</code></span>
                              <button onClick={handleRunCustom} disabled={runningCustom} className="btn btn-secondary btn-sm">
                                {runningCustom ? <Spinner /> : <Icon name="play" size={12} />} Run
                              </button>
                            </div>
                            <label htmlFor="custom-input" className="sr-only">Custom input</label>
                            <textarea
                              id="custom-input"
                              value={customInput}
                              onChange={(e) => setCustomInput(e.target.value)}
                              placeholder="Type the input your program reads"
                              className="flex-1 resize-none bg-transparent p-3 font-mono text-[13px] text-ink placeholder:text-ink-3 focus:outline-none"
                            />
                          </div>
                          <div className="flex-1 space-y-2 overflow-y-auto p-3">
                            <div className="text-sm font-medium text-ink-3">Output</div>
                            {!runningCustom && !customOutput && <p className="py-4 text-sm text-ink-3">Run your code to see its output here.</p>}
                            {runningCustom && <Spinner />}
                            {!runningCustom && customOutput?.map((r, i) => (
                              <div key={i} className={`rounded-md border p-3 ${r.error ? 'border-tomato-ink/40 bg-tomato/10' : 'border-grass-ink/40 bg-grass/10'}`}>
                                <div className={`mb-1 text-xs font-semibold ${r.error ? 'text-tomato-ink' : 'text-grass-ink'}`}>Input {i + 1}</div>
                                <pre className="whitespace-pre-wrap break-all font-mono text-[13px]">{r.error || r.output || '(empty)'}</pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex h-9 shrink-0 items-center gap-3 border-t border-line px-4">
                    <button onClick={() => setBottomOpen(true)} className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-2 hover:text-ink">
                      <Icon name="chevron-up" size={14} /> Show results
                    </button>
                    {totalCount > 0 && <span className="chip h-5 px-2">{passedCount} of {totalCount} passed</span>}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center overflow-y-auto p-6">
              <div className="grid w-full max-w-4xl items-start gap-10 md:grid-cols-[1fr_22rem]">
                <div>
                  <h1 className="display text-[clamp(2.6rem,5vw,4rem)]">Practice arena</h1>
                  <p className="measure mt-5 text-lg text-ink-2">
                    Pick a topic, or upload a syllabus, and get problems written for you. Run them against test cases, then ask the coach what went wrong.
                  </p>
                  <ul className="mt-8 space-y-4 text-ink-2">
                    <li><span className="font-semibold text-ink">Never a repeat.</span> Questions already seen on this device are excluded.</li>
                    <li><span className="font-semibold text-ink">Hidden tests.</span> Only the first case is visible, as in a real match.</li>
                    <li><span className="font-semibold text-ink">Feedback after every submit.</span> A logic score, hints, and a complexity report.</li>
                  </ul>
                </div>
                <div className="panel p-5">
                  <h2 className="mb-4 font-bold">New questions</h2>
                  {generator}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Side panel */}
        {rightPanel && (
          <aside className="flex w-[22rem] shrink-0 flex-col border-l border-line bg-panel">
            <div className="tabs shrink-0 px-2" role="tablist">
              {panelTabs.map(([key, label]) => (
                <button key={key} role="tab" aria-selected={rightPanel === key} onClick={() => setRightPanel(key)} className="tab">
                  {label}
                  {key === 'questions' && questions.length > 0 && <span className="chip h-5 px-2">{questions.length}</span>}
                </button>
              ))}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {rightPanel === 'questions' && (
                <div>
                  <div className="border-b border-line p-4">{generator}</div>
                  {questions.length === 0 ? (
                    <PanelNote title="No questions yet">Generate some above and they will be listed here.</PanelNote>
                  ) : (
                    <ol>
                      {questions.map((qItem, i) => {
                        const status = submissionStatus[i]
                        return (
                          <li key={i} className="border-b border-line">
                            <button
                              onClick={() => {
                                if (status && i !== activeQ) { showToast('You have already submitted this question.', 'info'); return }
                                setActiveQ(i)
                              }}
                              aria-current={i === activeQ}
                              className={`flex w-full items-start gap-3 px-4 py-3.5 text-left transition-colors ${i === activeQ ? 'bg-sunken' : 'hover:bg-sunken'}`}
                            >
                              <span className="mt-0.5">
                                {status ? (
                                  <Icon name={status === 'passed' ? 'check-circle' : 'x-circle'} size={18} className={status === 'passed' ? 'text-grass-ink' : 'text-tomato-ink'} />
                                ) : (
                                  <span className="numeral flex h-[18px] w-[18px] items-center justify-center text-base text-ink-3">{i + 1}</span>
                                )}
                              </span>
                              <span className="min-w-0 flex-1">
                                <span className="clamp-2 block font-semibold leading-snug">{qItem.title}</span>
                                <span className="mt-1 flex items-center gap-2 text-xs text-ink-3">
                                  <span className="dot" style={{ background: balloonFill(DIFF_COLOR[qItem.difficulty] || 'sun') }} />
                                  <span className="capitalize">{qItem.difficulty}</span>
                                  <span>{qItem.topic || 'General'}</span>
                                </span>
                              </span>
                            </button>
                          </li>
                        )
                      })}
                    </ol>
                  )}
                </div>
              )}

              {rightPanel === 'ai' && (
                <div className="space-y-5 p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold">Review of your solution</h3>
                    <button onClick={() => fetchAI(submitResult)} disabled={loadingAI || !q} className="btn btn-quiet btn-sm">
                      <Icon name="refresh" size={14} />
                      Analyse
                    </button>
                  </div>
                  {loadingAI && (
                    <div className="flex items-center gap-3 py-6 text-sm text-ink-2" role="status"><Spinner /> Reading your code…</div>
                  )}
                  {!loadingAI && !aiFeedback && (
                    <p className="text-sm text-ink-2">Submit your code, or press Analyse, to get a logic score and hints.</p>
                  )}
                  {!loadingAI && aiFeedback && <LogicReport data={aiFeedback} showPredicted={false} />}
                  {!loadingAI && (
                    <CoachChat
                      messages={coachMessages}
                      input={coachInput}
                      setInput={setCoachInput}
                      loading={coachLoading}
                      onSend={sendCoachMessage}
                      onClear={() => setCoachMessages([])}
                    />
                  )}
                </div>
              )}

              {rightPanel === 'complexity' && (
                <div className="p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="font-bold">Complexity</h3>
                    <button onClick={fetchComplexity} disabled={loadingCx || !q} className="btn btn-quiet btn-sm">
                      <Icon name="refresh" size={14} />
                      Analyse
                    </button>
                  </div>
                  {loadingCx && <div className="flex items-center gap-3 py-6 text-sm text-ink-2" role="status"><Spinner /> Working out how your code scales…</div>}
                  {!loadingCx && !complexity && <p className="text-sm text-ink-2">Press Analyse to see the time and space complexity of your solution.</p>}
                  {!loadingCx && complexity && <ComplexityReport data={complexity} />}
                </div>
              )}
            </div>
          </aside>
        )}
      </div>

      {/* Completion dialog */}
      {showCompletionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4" role="dialog" aria-modal="true" aria-labelledby="done-title">
          <div className="panel w-full max-w-sm p-7 shadow-float">
            <h2 id="done-title" className="stretch-narrow text-3xl font-extrabold tracking-tight">Session complete</h2>
            <p className="mt-1.5 text-ink-2">You have submitted every question in this set.</p>

            {(() => {
              const passed = Object.values(submissionStatus).filter((s) => s === 'passed').length
              const lagging = [...new Set(questions.filter((_, i) => submissionStatus[i] === 'failed').map((x) => x.topic).filter(Boolean))]
              return (
                <>
                  <dl className="mt-6 grid grid-cols-2 divide-x divide-line rounded-md border border-line">
                    <div className="px-4 py-4">
                      <dd className="numeral text-4xl text-grass-ink">{passed}</dd>
                      <dt className="mt-1 text-sm text-ink-3">Passed</dt>
                    </div>
                    <div className="px-4 py-4">
                      <dd className="numeral text-4xl text-tomato-ink">{questions.length - passed}</dd>
                      <dt className="mt-1 text-sm text-ink-3">Not passed</dt>
                    </div>
                  </dl>
                  {lagging.length > 0 ? (
                    <div className="mt-5">
                      <p className="mb-2 text-sm font-semibold">Worth another look</p>
                      <div className="flex flex-wrap gap-2">{lagging.map((t) => <span key={t} className="chip capitalize">{t}</span>)}</div>
                    </div>
                  ) : (
                    <p className="mt-5 text-sm font-semibold text-grass-ink">A perfect set. Nothing to review.</p>
                  )}
                </>
              )
            })()}

            <div className="mt-7 flex gap-3">
              <button onClick={() => setShowCompletionModal(false)} className="btn btn-secondary flex-1">Keep reviewing</button>
              <button onClick={() => { setShowCompletionModal(false); nav('/profile') }} className="btn btn-primary flex-1">See your progress</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
