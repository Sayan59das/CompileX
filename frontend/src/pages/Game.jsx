import React, { useEffect, useState, useRef } from 'react'
import { useParams, useLocation, useNavigate, Link } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import { connectSocket } from '../services/socket'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useEditorTheme, ThemeToggle } from '../context/ThemeContext'
import Leaderboard from '../components/Leaderboard'
import Timer from '../components/Timer'
import Logo from '../components/Logo'
import Icon from '../components/Icons'
import Avatar from '../components/Avatar'
import ProblemStatement from '../components/ProblemStatement'
import CoachChat from '../components/CoachChat'
import { LogicReport, ComplexityReport, TestCaseViewer, Spinner, PanelNote } from '../components/Analysis'
import { attachProtectedRegion } from '../utils/protectedRegion'
import { registerEditorThemes, EDITOR_FONT } from '../utils/monacoTheme'

const LANGUAGES = [
  { value: 'python', label: 'Python', monaco: 'python' },
  { value: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { value: 'cpp', label: 'C++', monaco: 'cpp' },
  { value: 'java', label: 'Java', monaco: 'java' },
  { value: 'c', label: 'C', monaco: 'c' },
]

const PANEL_TABS = [
  ['problem', 'Problem'],
  ['leaderboard', 'Standings'],
  ['ai-analyzer', 'Review'],
  ['complexity', 'Complexity'],
]

/** Centered modal. Used for the match's blocking moments (time up, waiting, finished). */
function Dialog({ labelledBy, children, wide = false }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/55 p-4" role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
      <div className={`panel max-h-[90vh] w-full overflow-y-auto p-7 shadow-float ${wide ? 'max-w-lg' : 'max-w-md'}`}>{children}</div>
    </div>
  )
}

/** One dot per player; filled once they have submitted or finished. */
function ProgressDots({ done, total }) {
  return (
    <div className="flex items-center gap-1.5" aria-hidden="true">
      {Array.from({ length: Math.max(total, 2) }).map((_, i) => (
        <span key={i} className={`h-3 w-3 rounded-full ${i < done ? 'bg-ink' : 'bg-line-strong'}`} />
      ))}
    </div>
  )
}


const STARTER = {
  python: `# Read input
# n = int(input())
# arr = list(map(int, input().split()))

def solve():
    """
    Write your solution here
    
    Steps:
    1. Read and parse input
    2. Process the data
    3. Print the output
    """
    # Your code here
    pass

# Call the function
solve()
`,
  javascript: `// Read input
// const lines = require("fs").readFileSync("/dev/stdin","utf-8").trim().split("\\n");
// let idx = 0;
// const readline = () => lines[idx++];

function solve() {
    /**
     * Write your solution here
     * 
     * Steps:
     * 1. Read and parse input using readline()
     * 2. Process the data
     * 3. Print the output using console.log()
     */
    
    // Your code here
}

// Call the function
solve();
`,
  cpp: `#include <bits/stdc++.h>
using namespace std;

/**
 * Write your solution here
 * 
 * Steps:
 * 1. Read and parse input using cin
 * 2. Process the data
 * 3. Print the output using cout
 */
void solve() {
    // Your code here
    
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    solve();
    return 0;
}
`,
  java: `import java.util.*;
import java.io.*;

public class Main {
    /**
     * Write your solution here
     * 
     * Steps:
     * 1. Read and parse input using BufferedReader
     * 2. Process the data
     * 3. Print the output using System.out.println()
     */
    public static void solve() throws Exception {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        
        // Your code here
        
    }
    
    public static void main(String[] args) throws Exception {
        solve();
    }
}
`,
  c: `#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/**
 * Write your solution here
 * 
 * Steps:
 * 1. Read and parse input using scanf / fgets
 * 2. Process the data
 * 3. Print the output using printf
 * 
 * Note: Once a question is generated, the starter code will
 * include the correct function signature and input reading.
 */
int solve(int n) {
    // Your code here
    return 0;
}

int main() {
    int n;
    scanf("%d", &n);
    printf("%d\n", solve(n));
    return 0;
}
`,
}

// Generate code template based on question
function generateCodeTemplate(question, language) {
  if (!question) return STARTER[language]
  
  // Use server-generated function-based starter code if available
  if (question.starter_code) {
    try {
      const starterMap = typeof question.starter_code === 'string'
        ? JSON.parse(question.starter_code)
        : question.starter_code
      if (starterMap[language]) return starterMap[language]
    } catch (e) {
      // fall through to STARTER
    }
  }
  
  // Fallback to default starter
  return STARTER[language]
}

export default function Game() {
  const { code } = useParams()
  const { state } = useLocation()

  // ── Feedback helpers (used when the analysis service has nothing better) ──
  function _dynamicAnalysis(passed, total) {
    const pct = total > 0 ? Math.round((passed / total) * 100) : 0
    const failed = total - passed
    if (passed === total) return `All ${total} test cases passed. Your solution is correct.`
    const analyses = [
      `${passed} of ${total} test cases passed (${pct}%). Check the failing cases for hints.`,
      `${failed} of ${total} tests are failing (${pct}% pass rate). Review your logic.`,
      `Your solution passes ${passed} out of ${total} tests. Trace through the failing inputs.`,
      `${pct}% correct, with ${failed} test case${failed > 1 ? 's' : ''} still failing. Compare the expected and actual output.`,
      `${passed} of ${total} tests pass. Debug the ${failed} failing case${failed > 1 ? 's' : ''} to find the issue.`,
    ]
    return analyses[Math.floor(Math.random() * analyses.length)]
  }

  function _perfectSuggestions() {
    const pool = [
      'Perfect score. Every test case passed.',
      'Flawless solution. Every test case passed.',
      'All tests are green. Your logic is correct.',
      'Everything passes. Submit to lock in your score.',
      'A full pass. Nicely done.',
    ]
    return [pool[Math.floor(Math.random() * pool.length)]]
  }

  function _dynamicSuggestions(passed, total, failedTcs = []) {
    const failed = total - passed
    const pct = total > 0 ? Math.round((passed / total) * 100) : 0

    const pool = []

    if (pct === 0) {
      pool.push(
        `All ${total} test cases are failing. Check your core algorithm.`,
        'Start by tracing through the sample input by hand.',
        'Your output format may be wrong. Compare it with the expected output exactly.',
        'Make sure you are reading the input correctly (see the input format).',
        'Add print statements to see what your code actually produces.',
      )
    } else if (pct < 50) {
      pool.push(
        `${failed} test case${failed > 1 ? 's' : ''} failing. Your approach handles some cases but misses others.`,
        'Check edge cases: empty input, a single element, all-equal values.',
        'Your logic works for simple cases but breaks on complex ones.',
        'Look at the first failing test and ask what is different about that input.',
        'Compare your output format with the expected output exactly.',
      )
    } else if (pct < 100) {
      pool.push(
        `${failed} edge case${failed > 1 ? 's' : ''} still failing, and you are close.`,
        'Check negative numbers, zero values and maximum constraints.',
        'Your main logic is right. Look for off-by-one errors or boundary conditions.',
        'Select a failing test case to compare expected and actual output.',
        'Check that your solution handles the smallest and largest input sizes.',
      )
    }

    pool.push('Select a failing test case below to see its exact input, expected output and your output.')

    const shuffled = pool.sort(() => Math.random() - 0.5)
    return shuffled.slice(0, Math.floor(Math.random() * 2) + 2)
  }

  const { user } = useAuth()
  const nav = useNavigate()
  const editorTheme = useEditorTheme()

  const lobby = state?.lobby
  const playerId = state?.player_id

  const [question, setQuestion] = useState(null)
  const [lang, setLang] = useState('python')
  const [editorCode, setEditorCode] = useState(STARTER['python'])
  const [leaderboard, setLeaderboard] = useState([])
  const [result, setResult] = useState(null)
  
  // Update editor code when question changes
  useEffect(() => {
    if (question) {
      const template = generateCodeTemplate(question, lang)
      setEditorCode(template)
    }
  }, [question, lang])
  const [submitting, setSubmitting] = useState(false)
  const [gameOver, setGameOver] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [difficulty, setDifficulty] = useState(
    (lobby?.difficulty?.toLowerCase ? lobby.difficulty.toLowerCase() : lobby?.difficulty) || 'medium'
  )
  const [topic, setTopic] = useState('')

  const [currentRound, setCurrentRound] = useState(1)
  const [totalRounds, setTotalRounds] = useState(state?.num_rounds || lobby?.num_rounds || 1)
  const [questionIndex, setQuestionIndex] = useState(0)
  const [questionsPerRound, setQuestionsPerRound] = useState(state?.questions_per_round || lobby?.questions_per_round || 1)
  const [totalQuestionsAnswered, setTotalQuestionsAnswered] = useState(0)
  const [roundEnded, setRoundEnded] = useState(false)
  const [roundLeaderboard, setRoundLeaderboard] = useState([])
  const [timeUp, setTimeUp] = useState(false)
  const [showCompletionPopup, setShowCompletionPopup] = useState(false)
  const [finishedCount, setFinishedCount] = useState(0)
  const [totalPlayerCount, setTotalPlayerCount] = useState(0)
  const [waitingForOthers, setWaitingForOthers] = useState(false)
  const [submittedCount, setSubmittedCount] = useState(0)
  const [waitingTotal, setWaitingTotal] = useState(0)

  const [startedAt, setStartedAt] = useState(state?.started_at || null)
  const [timeLimit, setTimeLimit] = useState(state?.time_per_question || state?.time_limit || lobby?.time_per_question || 600)
  const [questionStartedAt, setQuestionStartedAt] = useState(null)
  const socketRef = useRef(null)
  const answeredRef = useRef(0) // track locally to avoid stale closure in socket handlers
  const usedTitlesRef = useRef([]) // track all question titles seen this session for deduplication

  const [selectedTestCase, setSelectedTestCase] = useState(0)
  const [testCaseDetails, setTestCaseDetails] = useState([])
  const [consoleOutput, setConsoleOutput] = useState([])
  const [runningCustom, setRunningCustom] = useState(false)
  const [customInput, setCustomInput] = useState('')
  const [useCustomInput, setUseCustomInput] = useState(false)
  const [showCustomWarning, setShowCustomWarning] = useState(false)

  const [activePanel, setActivePanel] = useState('problem')
  const [rightPanelTab, setRightPanelTab] = useState('tests')
  const [debugHint, setDebugHint] = useState(null)         // AI analyzer result (persists across test case selection)
  const [testCaseHint, setTestCaseHint] = useState(null)   // Per-test-case debug hint from /debug/hint
  const [complexityData, setComplexityData] = useState(null)

  // Grok AI feedback chat
  const [grokMessages, setGrokMessages] = useState([])     // [{role, content}]
  const [grokInput, setGrokInput] = useState('')
  const [grokLoading, setGrokLoading] = useState(false)
  const [loadingHint, setLoadingHint] = useState(false)
  const [loadingComplexity, setLoadingComplexity] = useState(false)
  const [bottomPanelMinimized, setBottomPanelMinimized] = useState(false)
  
  // Panel widths
  const [problemWidth, setProblemWidth] = useState(600)
  const [aiAnalyzerWidth, setAiAnalyzerWidth] = useState(320)
  const [complexityWidth, setComplexityWidth] = useState(320)
  const [leaderboardWidth, setLeaderboardWidth] = useState(320)
  
  // Resize states
  const [isResizingProblem, setIsResizingProblem] = useState(false)
  const [isResizingAiAnalyzer, setIsResizingAiAnalyzer] = useState(false)
  const [isResizingComplexity, setIsResizingComplexity] = useState(false)
  const [isResizingLeaderboard, setIsResizingLeaderboard] = useState(false)

  useEffect(() => {
    if (!lobby || !playerId) { nav('/home'); return }
    const socket = connectSocket()
    socketRef.current = socket

    socket.on('leaderboard_update', ({ leaderboard }) => setLeaderboard(leaderboard))
    socket.on('player_finished', ({ finished_count, total_count }) => {
      setFinishedCount(finished_count)
      setTotalPlayerCount(total_count)
    })
    socket.on('game_ended', ({ leaderboard }) => {
      setLeaderboard(leaderboard)
      setShowCompletionPopup(false)
      setGameOver(true)
    })
    socket.on('new_question', ({ question, question_index, time_per_question }) => {
      // All players receive the same question from the server
      if (!question) return
      if (typeof question.parameters === 'string') {
        try { question.parameters = JSON.parse(question.parameters) }
        catch { question.parameters = [] }
      }
      setQuestion(question)
      setResult(null)
      setTestCaseDetails([])
      setDebugHint(null)
      setTestCaseHint(null)
      setEditorCode(STARTER[lang])
      if (question?.title) {
        usedTitlesRef.current = [...usedTitlesRef.current, question.title.toLowerCase()]
      }
      if (question_index !== undefined) setQuestionIndex(question_index)
      if (time_per_question) setTimeLimit(time_per_question)
      setQuestionStartedAt(new Date().toISOString())
      setGenerating(false)
    })
    socket.on('round_started', ({ round_number, total_rounds, time_per_question }) => {
      setCurrentRound(round_number)
      if (total_rounds) setTotalRounds(total_rounds)
      setRoundEnded(false)
      setQuestionIndex(0)
      if (time_per_question) setTimeLimit(time_per_question)
    })
    socket.on('round_ended', ({ round_number, leaderboard }) => {
      setRoundLeaderboard(leaderboard)
      setRoundEnded(true)
    })
    socket.on('game_started', ({ started_at, time_limit, num_rounds, questions_per_round, time_per_question }) => {
      setStartedAt(started_at)
      if (time_per_question) setTimeLimit(time_per_question)
      if (num_rounds) setTotalRounds(num_rounds)
      if (questions_per_round) setQuestionsPerRound(questions_per_round)
    })

    // Per-question sync: update waiting counter
    socket.on('question_submission_update', ({ submitted_count, total_count }) => {
      setSubmittedCount(submitted_count)
      setWaitingTotal(total_count)
    })

    // All players submitted this question — proceed to next
    socket.on('all_submitted', ({ question_index: qi }) => {
      setWaitingForOthers(false)
      setSubmittedCount(0)
      const answered = answeredRef.current
      const totalQ = questionsPerRound * totalRounds
      if (answered < totalQ) {
        setQuestion(null)
        setResult(null)
        setTestCaseDetails([])
        setDebugHint(null)
        setTestCaseHint(null)
        // Only host generates the next question
        if (lobby?.created_by && user?.id && lobby.created_by === user.id) {
          generateQuestion()
        } else {
          setGenerating(true)
        }
      } else {
        // All questions done — show completion popup
        socketRef.current?.emit('player_finished', { lobby_id: lobby.id, player_id: playerId })
        setTimeout(() => setShowCompletionPopup(true), 600)
      }
    })

    return () => {
      socket.off('leaderboard_update')
      socket.off('player_finished')
      socket.off('game_ended')
      socket.off('new_question')
      socket.off('round_started')
      socket.off('round_ended')
      socket.off('game_started')
      socket.off('question_submission_update')
      socket.off('all_submitted')
    }
  }, [])

  // Panel resize handler
  useEffect(() => {
    const handleMouseMove = (e) => {
      const newWidth = e.clientX
      
      if (isResizingProblem) {
        // Problem panel: 400-800px
        if (newWidth >= 400 && newWidth <= 800) {
          setProblemWidth(newWidth)
        } else if (newWidth < 400) {
          setProblemWidth(400)
        } else if (newWidth > 800) {
          setProblemWidth(800)
        }
      } else if (isResizingAiAnalyzer) {
        // AI Analyzer: 250-600px
        if (newWidth >= 250 && newWidth <= 600) {
          setAiAnalyzerWidth(newWidth)
        } else if (newWidth < 250) {
          setAiAnalyzerWidth(250)
        } else if (newWidth > 600) {
          setAiAnalyzerWidth(600)
        }
      } else if (isResizingComplexity) {
        // Complexity: 250-600px
        if (newWidth >= 250 && newWidth <= 600) {
          setComplexityWidth(newWidth)
        } else if (newWidth < 250) {
          setComplexityWidth(250)
        } else if (newWidth > 600) {
          setComplexityWidth(600)
        }
      } else if (isResizingLeaderboard) {
        // Leaderboard: 250-600px
        if (newWidth >= 250 && newWidth <= 600) {
          setLeaderboardWidth(newWidth)
        } else if (newWidth < 250) {
          setLeaderboardWidth(250)
        } else if (newWidth > 600) {
          setLeaderboardWidth(600)
        }
      }
    }

    const handleMouseUp = () => {
      if (isResizingProblem) setIsResizingProblem(false)
      if (isResizingAiAnalyzer) setIsResizingAiAnalyzer(false)
      if (isResizingComplexity) setIsResizingComplexity(false)
      if (isResizingLeaderboard) setIsResizingLeaderboard(false)
    }

    const isResizing = isResizingProblem || isResizingAiAnalyzer || isResizingComplexity || isResizingLeaderboard

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    } else {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingProblem, isResizingAiAnalyzer, isResizingComplexity, isResizingLeaderboard])

  useEffect(() => {
    if (question) {
      console.log('[useEffect] Question received:', question.title)
      console.log('[useEffect] test_cases type:', typeof question.test_cases)
      console.log('[useEffect] test_cases preview:', String(question.test_cases).substring(0, 100))
      try {
        let tcs = question.test_cases;
        if (typeof tcs === 'string') {
          tcs = JSON.parse(tcs);
        }
        const visibleTcs = Array.isArray(tcs) ? tcs : [];
        console.log('[useEffect] Parsed test cases count:', visibleTcs.length)
        
        if (visibleTcs.length === 0) {
          console.log('[useEffect] No test cases found!')
          setTestCaseDetails([]);
          return;
        }
        
        console.log('[useEffect] Setting test case details...')
        // Keep custom input empty - let users type their own test input
        // setCustomInput(visibleTcs.map(tc => tc.input || tc.input_data || '').join('\n'))
        setTestCaseDetails(visibleTcs.map((tc, i) => ({
          index: i,
          input: tc.input || tc.input_data || '',
          expected_output: tc.output || tc.expected_output || '',
          actual_output: null,
          passed: null,
          error: null,
          hidden: i > 0,
        })))
        setSelectedTestCase(0)
        console.log('[useEffect] Test case details set successfully')
      } catch (e) {
        console.error('[useEffect] Error parsing test cases:', e)
        setTestCaseDetails([])
      }
    }
  }, [question])

  function changeLang(l) { 
    setLang(l); 
    const template = question ? generateCodeTemplate(question, l) : STARTER[l]
    setEditorCode(template) 
  }

  // Auto-update AI analyzer panel when tests are run (via Run Tests button)
  // Note: submission results are handled directly in submitCode() above
  useEffect(() => {
    const ran = testCaseDetails.filter(tc => tc.passed !== null && tc.actual_output !== null)
    if (ran.length === 0) return
    const passed = ran.filter(tc => tc.passed).length
    const total = ran.length
    const passRate = Math.round((passed / total) * 100)

    if (passed === total) {
      setDebugHint({
        logic_correctness: 100,
        analysis: `All ${total} test cases passed! Your solution is correct.`,
        predicted_score: 100,
        suggestions: _perfectSuggestions(),
        breakdown: { algorithm_approach: 100, edge_case_handling: 100, implementation_quality: 100, code_structure: 100 },
        is_pre_submission: false,
      })
    } else {
      // Call backend with actual test results to get accurate, problem-specific hints
      const problemStatement = question
        ? `${question.title}\n\n${question.description || question.problem_statement || ''}`
        : ''
      api.post('/analyze-code', {
        code: editorCode,
        language: lang,
        problem_statement: problemStatement,
        test_results: ran,
        passed_tests: passed,
        total_tests: total,
      }).then(({ data }) => {
        const failedTcs = ran.filter(tc => !tc.passed)
        setDebugHint({
          logic_correctness: data.logic_correctness ?? passRate,
          analysis: data.analysis || _dynamicAnalysis(passed, total),
          predicted_score: data.predicted_score ?? passRate,
          suggestions: data.suggestions && data.suggestions.length > 0
            ? data.suggestions
            : _dynamicSuggestions(passed, total, failedTcs),
          breakdown: data.breakdown || {},
          is_pre_submission: false,
        })
      }).catch(() => {
        // Fallback to dynamic hints if backend call fails
        const failedTcs = ran.filter(tc => !tc.passed)
        setDebugHint({
          logic_correctness: passRate,
          analysis: _dynamicAnalysis(passed, total),
          predicted_score: passRate,
          suggestions: _dynamicSuggestions(passed, total, failedTcs),
          breakdown: { algorithm_approach: passRate, edge_case_handling: passRate, implementation_quality: passRate, code_structure: passRate },
          is_pre_submission: false,
        })
      })
    }
  }, [testCaseDetails])

  async function generateQuestion() {
    // Only the host generates questions — non-host players receive via socket
    if (!lobby?.created_by || !user?.id || lobby.created_by !== user.id) return

    setGenerating(true)
    try {
      const genTopic = topic || (lobby?.topics ? JSON.parse(lobby.topics)?.[0] : undefined)
      const { data } = await api.post('/questions/generate', {
        difficulty: difficulty,
        topic: genTopic || undefined,
        exclude_titles: usedTitlesRef.current,
        lobby_id: lobby.id,
      })

      const { data: saved } = await api.post('/questions', data)
      const questionWithId = { ...data, id: saved.id }
      if (typeof questionWithId.parameters === 'string') {
        try { questionWithId.parameters = JSON.parse(questionWithId.parameters) }
        catch { questionWithId.parameters = [] }
      }

      // Track title to avoid repeats
      if (data.title) {
        usedTitlesRef.current = [...usedTitlesRef.current, data.title.toLowerCase()]
      }

      // Broadcast to ALL players via server — everyone gets the same question
      socketRef.current?.emit('broadcast_question', {
        lobby_id: lobby.id,
        question: questionWithId,
        question_index: answeredRef.current,
      })
    } catch (err) {
      setResult({ error: err.response?.data?.detail || 'Failed to generate question' })
      setGenerating(false)
    }
    // Note: setGenerating(false) is handled when new_question arrives for the host too
  }

  function handleTimeUp() {
    if (!question) return
    setTimeUp(true)
    setTimeout(() => {
      setTimeUp(false)
      const answered = answeredRef.current
      const totalQ = questionsPerRound * totalRounds
      if (answered + 1 >= totalQ) {
        submitCode()
      } else {
        const next = answered + 1
        setTotalQuestionsAnswered(next)
        answeredRef.current = next
        setQuestion(null)
        setResult(null)
        setTestCaseDetails([])
        setDebugHint(null)
        setTestCaseHint(null)
        if (lobby?.created_by && user?.id && lobby.created_by === user.id) {
          generateQuestion()
        } else {
          setGenerating(true)
        }
      }
    }, 3000)
  }

  // ── Grok AI Feedback ──────────────────────────────────────────────────────
  async function sendGrokMessage(messageText) {
    const text = (messageText || grokInput).trim()
    if (!text || grokLoading) return

    const userMsg = { role: 'user', content: text }
    const updatedHistory = [...grokMessages, userMsg]
    setGrokMessages(updatedHistory)
    setGrokInput('')
    setGrokLoading(true)

    try {
      const { data } = await api.post('/ai-feedback', {
        message: text,
        code: editorCode || '',
        language: lang,
        problem_statement: question?.description || question?.problem_statement || '',
        // Send history BEFORE the current message (backend appends it)
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

  async function submitCode() {
    setSubmitting(true); setResult(null)
    try {
      const { data } = await api.post('/submissions', { code: editorCode, language: lang, question_id: question.id })
      setResult(data)
      socketRef.current?.emit('score_update', { lobby_id: lobby.id, player_id: playerId, score: data.score })
      
      if (data.test_case_details && data.test_case_details.length > 0) {
        setTestCaseDetails(data.test_case_details.map((tc, i) => ({ ...tc, hidden: i > 0 })))
        setSelectedTestCase(0)
        setRightPanelTab('tests')
      }

      // Update AI analyzer panel directly from submission response
      if (data.logic_analysis) {
        const la = data.logic_analysis
        setDebugHint({
          logic_correctness: la.logic_correctness ?? la.partial_score ?? 0,
          analysis: la.analysis || '',
          predicted_score: la.partial_score ?? la.logic_correctness ?? 0,
          suggestions: la.suggestions || [],
          breakdown: la.breakdown || {},
          is_pre_submission: false,
        })
      } else if (data.test_case_details) {
        // Fallback: compute from test results directly
        const tcs = data.test_case_details
        const passed = tcs.filter(tc => tc.passed).length
        const total = tcs.length
        const pct = total > 0 ? Math.round((passed / total) * 100) : 0
        setDebugHint({
          logic_correctness: pct,
          analysis: passed === total
            ? `All ${total} test cases passed! Your solution is correct.`
            : _dynamicAnalysis(passed, total),
          predicted_score: pct,
          suggestions: passed === total
            ? _perfectSuggestions()
            : _dynamicSuggestions(passed, total, tcs.filter(tc => !tc.passed)),
          breakdown: {},
          is_pre_submission: false,
        })
      }

      // Track answered count
      const answered = totalQuestionsAnswered + 1
      setTotalQuestionsAnswered(answered)
      answeredRef.current = answered
      const totalQ = questionsPerRound * totalRounds

      if (answered < totalQ) {
        // Show waiting popup — don't advance until all players submit
        setWaitingForOthers(true)
        setSubmittedCount(1)  // at least this player submitted
        setWaitingTotal(Object.keys(lobby?.players || {}).length || 2)
        // Tell the server this player submitted for this question index
        socketRef.current?.emit('question_submitted', {
          lobby_id: lobby.id,
          player_id: playerId,
          question_index: answeredRef.current - 1,
        })
      } else {
        // Last question — wait for others to finish too before ending
        setWaitingForOthers(true)
        setSubmittedCount(1)
        setWaitingTotal(Object.keys(lobby?.players || {}).length || 2)
        socketRef.current?.emit('question_submitted', {
          lobby_id: lobby.id,
          player_id: playerId,
          question_index: answeredRef.current - 1,
        })
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Submission failed'
      setResult({ error: msg, status: 'error' })
      console.error('[Submit] Error:', msg)
    } finally { setSubmitting(false) }
  }

  async function runCode() {
    if (!question) return
    setRunningCustom(true)
    try {
      let inputs
      let runType = ''
      
      if (useCustomInput) {
        // For custom input: split by lines
        inputs = customInput.split('\n').filter(l => l.length > 0)
        runType = 'custom'
      } else if (testCaseDetails.length > 0) {
        // For test cases: each test case is a separate input (can be multi-line)
        inputs = testCaseDetails.map(tc => tc.input).filter(l => l && l.length > 0)
        runType = 'testcases'
      } else {
        inputs = ['']
        runType = 'empty'
      }
      
      if (inputs.length === 0 || (inputs.length === 1 && inputs[0] === '')) {
        setRunningCustom(false)
        return
      }
      
      const { data } = await api.post('/execute', {
        code: editorCode,
        language: lang,
        inputs: inputs
      })
      
      if (useCustomInput) {
        // Custom input mode: show in Console tab
        const results = data.results || []
        const enrichedResults = results.map((r, i) => ({
          ...r,
          input: inputs[i] || '',
          index: i,
          runType,
        }))
        setConsoleOutput(enrichedResults)
        setRightPanelTab('console')
      } else {
        // Test cases mode: update test case details with actual output
        const results = data.results || []
        const updatedTestCases = testCaseDetails.map((tc, i) => {
          const res = results[i]
          if (!res) return tc
          const actualOut = (res.output || '').trim()
          const expectedOut = (tc.expected_output || '').trim()
          const isPassed = !res.error && actualOut === expectedOut
          return {
            ...tc,
            actual_output: res.output || null,
            passed: isPassed,
            error: res.error || null,
          }
        })
        setTestCaseDetails(updatedTestCases)
        setRightPanelTab('tests')
      }
    } catch (err) {
      if (useCustomInput) {
        setConsoleOutput([{ error: err.response?.data?.detail || 'Execution failed', index: 0 }])
        setRightPanelTab('console')
      }
    } finally { 
      setRunningCustom(false) 
    }
  }

  function endGame() { socketRef.current?.emit('end_game', { lobby_id: lobby.id }) }

  async function getDebugHint() {
    const tc = testCaseDetails[selectedTestCase]
    if (!tc || !question) return
    setLoadingHint(true)
    setTestCaseHint(null)
    try {
      const { data } = await api.post('/debug/hint', {
        problem_statement: question.description || question.problem_statement || '',
        code: editorCode,
        language: lang,
        test_input: tc.input || '',
        expected_output: tc.expected_output || '',
        actual_output: tc.actual_output || '',
      })
      setTestCaseHint(data)
    } catch {
      setTestCaseHint({ status: 'Error', line: null, message: 'Could not fetch hint.', hint: 'Check your logic manually.' })
    } finally {
      setLoadingHint(false)
    }
  }

  // ── Analysis actions for the side panel ───────────────────────────────────
  async function analyzeCode() {
    if (!question || !editorCode) return

    // If tests have already run, use those results directly instead of the
    // pre-submission API (which scores an unsubmitted solution at 0%).
    const ranTests = testCaseDetails.filter((tc) => tc.passed !== null)
    if (ranTests.length > 0) {
      const passed = ranTests.filter((tc) => tc.passed).length
      const total = ranTests.length
      const passRate = Math.round((passed / total) * 100)
      if (passed === total) {
        setDebugHint({
          logic_correctness: 100,
          analysis: `All ${total} test cases passed. Your solution is correct.`,
          predicted_score: 100,
          suggestions: _perfectSuggestions(),
          is_pre_submission: false,
        })
      } else {
        setDebugHint({
          logic_correctness: passRate,
          analysis: _dynamicAnalysis(passed, total),
          predicted_score: passRate,
          suggestions: _dynamicSuggestions(passed, total, ranTests.filter((tc) => !tc.passed)),
          is_pre_submission: false,
        })
      }
      return
    }

    setLoadingHint(true)
    try {
      const { data } = await api.post('/analyze-code', {
        code: editorCode,
        language: lang,
        problem_statement: question.description || question.problem_statement || '',
        question_id: question.id,
      })
      setDebugHint(data)
    } catch {
      setDebugHint({ logic_correctness: 0, analysis: 'The analysis failed. Try again.', predicted_score: 0, suggestions: [] })
    } finally {
      setLoadingHint(false)
    }
  }

  async function analyzeComplexity() {
    if (!question || !editorCode) return
    setLoadingComplexity(true)
    try {
      const payload = {
        code: editorCode,
        language: lang,
        problem_statement: question.description || question.problem_statement || '',
      }
      if (result && result.execution_time_ms) payload.execution_time_ms = result.execution_time_ms
      if (result && result.passed_tests != null) payload.passed_tests = result.passed_tests
      if (result && result.total_tests != null) payload.total_tests = result.total_tests
      const { data } = await api.post('/analyze-complexity', payload)
      setComplexityData(data)
    } catch {
      setComplexityData({
        time_complexity: { best: 'N/A', average: 'N/A', worst: 'N/A' },
        space_complexity: { best: 'N/A', average: 'N/A', worst: 'N/A' },
        analysis: 'The analysis failed. Try again.',
        suggestions: [], structured_suggestions: [], verdict: 'unknown', verdict_explanation: '',
        is_optimal: false, detected_patterns: [], execution_stats: null,
      })
    } finally {
      setLoadingComplexity(false)
    }
  }

  const isHost = !!(lobby?.created_by && user?.id && lobby.created_by === user.id)
  const totalQuestions = questionsPerRound * totalRounds
  const passedCount = testCaseDetails.filter((tc) => tc.passed === true).length
  const totalTests = testCaseDetails.length
  const codeUntouched = !editorCode || editorCode === STARTER[lang] || editorCode === generateCodeTemplate(question, lang)

  // ── Between rounds ────────────────────────────────────────────────────────
  if (roundEnded && !gameOver) {
    const isLastRound = currentRound >= totalRounds
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-5 py-10">
        <div className="w-full max-w-md">
          <p className="text-ink-2">{isLastRound ? 'Final standings' : `${totalRounds - currentRound} ${totalRounds - currentRound === 1 ? 'round' : 'rounds'} to go`}</p>
          <h1 className="display mt-1 text-5xl">Round {currentRound} complete</h1>
          <div className="panel mt-8 overflow-hidden">
            <Leaderboard entries={roundLeaderboard} currentPlayerId={playerId} />
          </div>
          {isLastRound ? (
            <button onClick={endGame} className="btn btn-primary btn-lg mt-6 w-full">Finish the match</button>
          ) : (
            <button onClick={() => { setRoundEnded(false); setQuestion(null); setCurrentRound((prev) => prev + 1) }} className="btn btn-primary btn-lg mt-6 w-full">
              Start round {currentRound + 1}
            </button>
          )}
        </div>
      </div>
    )
  }

  // ── Match over ────────────────────────────────────────────────────────────
  if (gameOver) {
    const myEntry = leaderboard.find((e) => (e.player_id ?? e.id) === playerId)
    const myRank = myEntry ? leaderboard.indexOf(myEntry) + 1 : null

    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-paper px-5 py-10">
        <div className="w-full max-w-xl">
          <p className="text-ink-2">Match over</p>
          <h1 className="display mt-1 text-[clamp(3rem,8vw,5rem)]">
            {myRank === 1 ? 'You won.' : myRank ? `You finished ${myRank}${['st', 'nd', 'rd'][myRank - 1] || 'th'}.` : 'Final standings'}
          </h1>

          <div className="panel mt-8 overflow-hidden">
            {leaderboard.length === 0 ? (
              <p className="px-5 py-10 text-center text-ink-2">No scores were recorded.</p>
            ) : (
              <Leaderboard entries={leaderboard} currentPlayerId={playerId} />
            )}
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button onClick={() => nav('/dashboard')} className="btn btn-primary btn-lg">Back to the dashboard</button>
            <button onClick={() => nav('/history')} className="btn btn-secondary btn-lg">See match history</button>
          </div>
        </div>
      </div>
    )
  }

  const currentLang = LANGUAGES.find((l) => l.value === lang) || LANGUAGES[0]
  const answeredShown = Math.min(totalQuestionsAnswered, totalQuestions)

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-paper">
      {/* ── Blocking moments ─────────────────────────────────────────────── */}
      {timeUp && (
        <Dialog labelledBy="timeup-title">
          <h2 id="timeup-title" className="stretch-narrow text-3xl font-extrabold tracking-tight">Time is up</h2>
          <p className="mt-2 text-ink-2">
            {answeredRef.current + 1 >= totalQuestions ? 'Submitting the code you have.' : 'Moving on to the next question.'}
          </p>
          <div className="mt-5 flex items-center gap-3 text-sm text-ink-3" role="status"><Spinner /> One moment</div>
        </Dialog>
      )}

      {waitingForOthers && !showCompletionPopup && !gameOver && (
        <Dialog labelledBy="waiting-title">
          <h2 id="waiting-title" className="stretch-narrow text-3xl font-extrabold tracking-tight">Submitted</h2>
          <p className="mt-2 text-ink-2">Waiting for the other players to submit this question.</p>
          <div className="mt-6 flex items-center gap-4">
            <ProgressDots done={submittedCount} total={waitingTotal} />
            <span className="tnum text-sm font-semibold">{submittedCount} of {waitingTotal} submitted</span>
          </div>
        </Dialog>
      )}

      {showCompletionPopup && !gameOver && (
        <Dialog labelledBy="finished-title" wide>
          <h2 id="finished-title" className="stretch-narrow text-3xl font-extrabold tracking-tight">You have answered everything</h2>
          <p className="mt-2 text-ink-2">
            That was all {totalQuestions} question{totalQuestions !== 1 ? 's' : ''}. The match ends when everyone has finished.
          </p>
          {totalPlayerCount > 0 && (
            <div className="mt-5 flex items-center gap-4">
              <ProgressDots done={finishedCount} total={totalPlayerCount} />
              <span className="tnum text-sm font-semibold">{finishedCount} of {totalPlayerCount} done</span>
            </div>
          )}
          <div className="mt-6 overflow-hidden rounded-md border border-line">
            <div className="border-b border-line bg-sunken px-4 py-2 text-sm font-medium text-ink-3">Live standings</div>
            <Leaderboard entries={leaderboard} currentPlayerId={playerId} />
          </div>
          <button onClick={() => nav('/dashboard')} className="btn btn-secondary mt-6 w-full">Leave the match</button>
        </Dialog>
      )}

      {showCustomWarning && (
        <Dialog labelledBy="custom-title">
          <h2 id="custom-title" className="stretch-narrow text-2xl font-extrabold tracking-tight">Custom input is on</h2>
          <p className="mt-2 text-ink-2">
            Run is using the input you typed instead of the test cases. Turn it off to see the test cases again.
          </p>
          <div className="mt-6 flex gap-3">
            <button onClick={() => setShowCustomWarning(false)} className="btn btn-secondary flex-1">Cancel</button>
            <button
              onClick={() => { setUseCustomInput(false); setShowCustomWarning(false); setRightPanelTab('tests') }}
              className="btn btn-primary flex-1"
            >
              Turn it off
            </button>
          </div>
        </Dialog>
      )}

      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line px-4">
        <Link to="/" aria-label="CompileX home" className="shrink-0"><Logo size={26} wordmark={false} /></Link>
        <div className="hidden min-w-0 items-center gap-2.5 md:flex">
          <span className="truncate font-bold">{lobby?.name || 'Match'}</span>
          <span className="chip font-mono">{code}</span>
        </div>

        <div className="mx-auto flex items-center gap-4">
          <ol className="flex items-center gap-1.5" aria-label={`Question ${answeredShown + 1} of ${totalQuestions}`}>
            {Array.from({ length: Math.min(totalQuestions, 12) }).map((_, i) => (
              <li
                key={i}
                className={`h-3 w-3 rounded-full border-2 ${
                  i < answeredShown ? 'border-ink bg-ink' : i === answeredShown ? 'border-ink bg-panel' : 'border-line-strong'
                }`}
              />
            ))}
          </ol>
          <span className="hidden text-sm text-ink-2 sm:block">
            Question <span className="tnum font-semibold text-ink">{Math.min(answeredShown + 1, totalQuestions)}</span> of {totalQuestions}
            {totalRounds > 1 && <>, round <span className="tnum font-semibold text-ink">{currentRound}</span> of {totalRounds}</>}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <Timer startedAt={questionStartedAt || startedAt} timeLimit={timeLimit} onExpire={handleTimeUp} />
          <ThemeToggle className="ml-2" />
          <button
            onClick={() => setActivePanel(activePanel === 'right' ? 'problem' : 'right')}
            className="btn btn-quiet btn-icon"
            aria-pressed={activePanel !== 'right'}
            aria-label={activePanel === 'right' ? 'Show the side panel' : 'Hide the side panel'}
          >
            <Icon name="sidebar" size={18} />
          </button>
          <span className="ml-1"><Avatar name={user?.username} size={30} /></span>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* ── Left panel ─────────────────────────────────────────────────── */}
        {activePanel !== 'right' && (
          <aside style={{ width: problemWidth }} className="relative flex shrink-0 flex-col border-r border-line">
            <div className="tabs shrink-0 px-2" role="tablist">
              {PANEL_TABS.map(([key, label]) => (
                <button key={key} role="tab" aria-selected={activePanel === key} onClick={() => setActivePanel(key)} className="tab">
                  {label}
                  {key === 'ai-analyzer' && debugHint?.logic_correctness !== undefined && !debugHint?.is_pre_submission && (
                    <span className="chip h-5 px-2">{Math.round(debugHint.logic_correctness)}%</span>
                  )}
                </button>
              ))}
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {/* Problem */}
              {activePanel === 'problem' && (
                !question ? (
                  <div className="p-6">
                    {isHost ? (
                      <>
                        <h2 className="stretch-narrow text-3xl font-extrabold tracking-tight">Choose the first problem</h2>
                        <p className="mt-2 text-ink-2">Everyone in the room gets the same one, and the clock starts when it appears.</p>
                        <div className="mt-6 space-y-5">
                          <fieldset>
                            <legend className="label">Difficulty</legend>
                            <div className="seg w-full" role="group">
                              {['easy', 'medium', 'hard'].map((d) => (
                                <button key={d} aria-pressed={difficulty === d} onClick={() => setDifficulty(d)} className="flex-1 capitalize">{d}</button>
                              ))}
                            </div>
                          </fieldset>
                          <div>
                            <label htmlFor="topic" className="label">Topic <span className="font-normal text-ink-3">optional</span></label>
                            <input id="topic" className="field" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="For example: arrays, strings, dp" />
                          </div>
                          <button onClick={generateQuestion} disabled={generating} className="btn btn-primary btn-lg w-full">
                            {generating ? (<><span className="h-4 w-4 animate-spin rounded-full border-2 border-paper/30 border-t-paper" />Writing the problem…</>) : 'Generate the problem'}
                          </button>
                        </div>
                      </>
                    ) : (
                      <div className="py-10 text-center" role="status">
                        <Spinner className="!h-7 !w-7" />
                        <h2 className="mt-5 text-xl font-bold">Waiting for the host</h2>
                        <p className="mx-auto mt-1.5 max-w-xs text-ink-2">The host is choosing the first problem. It will appear here as soon as it is ready.</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-6">
                    <ProblemStatement question={question} exampleCount={1} />

                    {isHost && (
                      <section className="mt-8 border-t border-line pt-5">
                        <h3 className="mb-3 text-sm font-bold">Host controls</h3>
                        <div className="flex gap-2">
                          <select
                            value={difficulty}
                            onChange={(e) => setDifficulty(e.target.value)}
                            className="field h-9 w-28 shrink-0 text-sm capitalize"
                            aria-label="Difficulty of the replacement question"
                          >
                            <option value="easy">Easy</option>
                            <option value="medium">Medium</option>
                            <option value="hard">Hard</option>
                          </select>
                          <input
                            value={topic}
                            onChange={(e) => setTopic(e.target.value)}
                            placeholder="Topic"
                            aria-label="Topic of the replacement question"
                            className="field h-9 min-w-0 flex-1 text-sm"
                            onKeyDown={(e) => { if (e.key === 'Enter' && !generating) generateQuestion() }}
                          />
                          <button onClick={generateQuestion} disabled={generating} className="btn btn-secondary btn-sm h-9">
                            {generating ? <Spinner /> : 'Swap question'}
                          </button>
                        </div>
                        <p className="hint">Replaces the problem for everyone in the room.</p>
                      </section>
                    )}
                  </div>
                )
              )}

              {/* Standings */}
              {activePanel === 'leaderboard' && (
                <div>
                  <Leaderboard entries={leaderboard} currentPlayerId={playerId} />
                  {leaderboard.length > 0 && (
                    <dl className="grid grid-cols-2 divide-x divide-line border-t border-line">
                      <div className="px-5 py-4">
                        <dd className="numeral text-3xl">{leaderboard.length}</dd>
                        <dt className="mt-1 text-sm text-ink-3">Players</dt>
                      </div>
                      <div className="px-5 py-4">
                        <dd className="numeral text-3xl">{leaderboard.find((e) => (e.player_id ?? e.id) === playerId)?.questions_solved ?? 0}</dd>
                        <dt className="mt-1 text-sm text-ink-3">You have solved</dt>
                      </div>
                    </dl>
                  )}
                </div>
              )}

              {/* Review */}
              {activePanel === 'ai-analyzer' && (
                <div className="space-y-5 p-5">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold">Review of your code</h3>
                    <button onClick={analyzeCode} disabled={loadingHint || !question || codeUntouched} className="btn btn-quiet btn-sm">
                      {loadingHint ? <Spinner /> : <Icon name="refresh" size={14} />}
                      Analyse
                    </button>
                  </div>

                  {!question ? (
                    <PanelNote title="No problem yet">The review is available once the problem has appeared.</PanelNote>
                  ) : codeUntouched ? (
                    <PanelNote title="Write some code first">Once you have started, you can ask for a review of your logic.</PanelNote>
                  ) : (
                    <>
                      {debugHint && debugHint.logic_correctness !== undefined ? (
                        <LogicReport data={debugHint} />
                      ) : (
                        <p className="text-sm text-ink-2">Press Analyse for a quick read of your solution before you submit.</p>
                      )}
                      {testCaseDetails.length > 0 && (
                        <div className="flex items-baseline justify-between border-t border-line pt-4 text-sm">
                          <span className="text-ink-2">Tests passed</span>
                          <span className="numeral text-2xl">{passedCount} of {totalTests}</span>
                        </div>
                      )}
                      <CoachChat
                        messages={grokMessages}
                        input={grokInput}
                        setInput={setGrokInput}
                        loading={grokLoading}
                        onSend={sendGrokMessage}
                        onClear={() => setGrokMessages([])}
                      />
                    </>
                  )}
                </div>
              )}

              {/* Complexity */}
              {activePanel === 'complexity' && (
                <div className="p-5">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="font-bold">Time and space complexity</h3>
                    <button onClick={analyzeComplexity} disabled={loadingComplexity || !question || codeUntouched} className="btn btn-quiet btn-sm">
                      {loadingComplexity ? <Spinner /> : <Icon name="refresh" size={14} />}
                      Analyse
                    </button>
                  </div>
                  {!question ? (
                    <PanelNote title="No problem yet">Complexity analysis is available once the problem has appeared.</PanelNote>
                  ) : codeUntouched ? (
                    <PanelNote title="Write some code first">Then press Analyse to see how your solution scales.</PanelNote>
                  ) : loadingComplexity ? (
                    <div className="flex items-center gap-3 py-6 text-sm text-ink-2" role="status"><Spinner /> Working out how your code scales…</div>
                  ) : !complexityData ? (
                    <p className="text-sm text-ink-2">Press Analyse to check the time and space complexity of your solution.</p>
                  ) : (
                    <ComplexityReport data={complexityData} />
                  )}
                </div>
              )}
            </div>

            {isHost && (
              <div className="flex shrink-0 items-center justify-between border-t border-line px-4 py-2.5">
                <span className="text-sm text-ink-3">You are the host</span>
                <button onClick={endGame} className="btn btn-quiet btn-sm text-tomato-ink">End the match</button>
              </div>
            )}

            <div
              onMouseDown={(e) => { e.preventDefault(); setIsResizingProblem(true) }}
              className="absolute right-0 top-0 z-10 h-full w-1.5 translate-x-1/2 cursor-ew-resize transition-colors hover:bg-sky/40"
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize the side panel"
            />
          </aside>
        )}

        {/* ── Editor and results ─────────────────────────────────────────── */}
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-12 shrink-0 items-center gap-3 border-b border-line px-3">
            <div className="seg" role="group" aria-label="Language">
              {LANGUAGES.map((l) => (
                <button key={l.value} aria-pressed={lang === l.value} onClick={() => changeLang(l.value)}>{l.label}</button>
              ))}
            </div>

            <div className="min-w-0 flex-1 truncate text-sm font-semibold">
              {result?.error ? (
                <span className="text-tomato-ink">{result.error}</span>
              ) : result ? (
                <span className={result.status === 'passed' ? 'text-grass-ink' : 'text-tomato-ink'}>
                  {result.status === 'passed' ? 'Passed' : 'Not passed'}: {result.passed_tests} of {result.total_tests} tests
                  {result.score != null && <span className="ml-2 text-ink-2">{result.score} points</span>}
                </span>
              ) : null}
            </div>

            <button
              onClick={() => setEditorCode(question ? generateCodeTemplate(question, lang) : STARTER[lang])}
              className="btn btn-quiet btn-sm"
              title="Reset to the starter code"
            >
              Reset
            </button>
            <button onClick={runCode} disabled={runningCustom || !question} className="btn btn-secondary btn-sm" title={useCustomInput ? 'Run with your custom input' : 'Run against the test cases'}>
              {runningCustom ? <Spinner /> : <Icon name="play" size={12} />}
              {runningCustom ? 'Running…' : useCustomInput ? 'Run custom input' : 'Run tests'}
            </button>
            <button onClick={submitCode} disabled={submitting || !question} className="btn btn-primary btn-sm">
              {submitting ? <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-paper/30 border-t-paper" /> : <Icon name="check" size={14} strokeWidth={2.4} />}
              {submitting ? 'Submitting…' : 'Submit'}
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden">
            <Editor
              height="100%"
              language={currentLang.monaco}
              value={editorCode}
              onChange={(v) => setEditorCode(v || '')}
              theme={editorTheme}
              beforeMount={registerEditorThemes}
              onMount={(editor, monaco) => { attachProtectedRegion(editor, monaco) }}
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                padding: { top: 16, bottom: 16 },
                fontFamily: EDITOR_FONT,
                fontLigatures: false,
                renderLineHighlight: 'line',
                cursorBlinking: 'blink',
                smoothScrolling: true,
                automaticLayout: true,
                tabSize: 4,
                wordWrap: 'on',
                bracketPairColorization: { enabled: true },
                guides: { bracketPairs: true, indentation: true },
              }}
            />
          </div>

          {/* Results */}
          <div className="flex shrink-0 flex-col border-t border-line bg-panel" style={{ height: bottomPanelMinimized ? 44 : 300 }}>
            <div className="flex h-11 shrink-0 items-center justify-between pl-2 pr-2">
              <div className="tabs border-b-0" role="tablist">
                <button
                  role="tab"
                  aria-selected={rightPanelTab === 'tests'}
                  onClick={() => { if (useCustomInput && rightPanelTab !== 'tests') setShowCustomWarning(true); else setRightPanelTab('tests') }}
                  className="tab"
                >
                  Test cases
                  {totalTests > 0 && (
                    <span className="chip h-5 px-2" style={{ color: passedCount === totalTests ? 'rgb(var(--grass-ink))' : 'inherit' }}>{passedCount} of {totalTests}</span>
                  )}
                </button>
                <button role="tab" aria-selected={rightPanelTab === 'custom'} onClick={() => setRightPanelTab('custom')} className="tab">
                  Custom input
                  {useCustomInput && <span className="chip h-5 px-2">On</span>}
                </button>
                <button role="tab" aria-selected={rightPanelTab === 'console'} onClick={() => setRightPanelTab('console')} className="tab">Console</button>
                {result?.logic_analysis && (
                  <button role="tab" aria-selected={rightPanelTab === 'logic'} onClick={() => setRightPanelTab('logic')} className="tab">
                    Logic analysis
                    <span className="chip h-5 px-2">{result.logic_analysis.logic_correctness}%</span>
                  </button>
                )}
              </div>
              <button
                onClick={() => setBottomPanelMinimized(!bottomPanelMinimized)}
                className="btn btn-quiet btn-icon h-8 w-8"
                aria-label={bottomPanelMinimized ? 'Show the results panel' : 'Hide the results panel'}
              >
                <Icon name={bottomPanelMinimized ? 'chevron-up' : 'chevron-down'} size={16} />
              </button>
            </div>

            {!bottomPanelMinimized && (
              <div className="min-h-0 flex-1 border-t border-line">
                {rightPanelTab === 'tests' && (
                  <TestCaseViewer
                    cases={testCaseDetails}
                    selected={selectedTestCase}
                    onSelect={(i) => { setSelectedTestCase(i); setTestCaseHint(null) }}
                    onHint={getDebugHint}
                    hint={testCaseHint}
                    loadingHint={loadingHint}
                  />
                )}

                {rightPanelTab === 'custom' && (
                  <div className="h-full space-y-3 overflow-y-auto p-4">
                    <label className="flex cursor-pointer items-center gap-2.5 text-sm font-medium">
                      <input
                        type="checkbox"
                        checked={useCustomInput}
                        onChange={(e) => setUseCustomInput(e.target.checked)}
                        className="h-4 w-4 rounded"
                        style={{ accentColor: 'rgb(var(--ink))' }}
                      />
                      Use my own input when I press Run
                    </label>
                    <div>
                      <label htmlFor="custom-input" className="sr-only">Custom input</label>
                      <textarea
                        id="custom-input"
                        value={customInput}
                        onChange={(e) => setCustomInput(e.target.value)}
                        placeholder={useCustomInput ? 'Type the input your program reads' : 'Turn on custom input above to edit this'}
                        disabled={!useCustomInput}
                        rows={4}
                        className="field font-mono text-[13px]"
                      />
                    </div>
                    <button onClick={runCode} disabled={runningCustom || !question || !useCustomInput} className="btn btn-secondary btn-sm">
                      {runningCustom ? <Spinner /> : <Icon name="play" size={12} />}
                      {runningCustom ? 'Running…' : 'Run with this input'}
                    </button>
                  </div>
                )}

                {rightPanelTab === 'console' && (
                  <div className="h-full overflow-y-auto p-4">
                    {consoleOutput.length > 0 ? (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-semibold">
                            Output{consoleOutput[0]?.runType === 'custom' ? ' for your input' : consoleOutput[0]?.runType === 'testcases' ? ' for the test cases' : ''}
                          </span>
                          <span className="text-ink-3">{consoleOutput.length} result{consoleOutput.length !== 1 ? 's' : ''}</span>
                        </div>
                        {consoleOutput.map((res, i) => (
                          <div key={i} className={`overflow-hidden rounded-md border ${res.error ? 'border-tomato-ink/40' : 'border-grass-ink/40'}`}>
                            <div className={`px-3 py-1.5 text-sm font-semibold ${res.error ? 'bg-tomato/10 text-tomato-ink' : 'bg-grass/10 text-grass-ink'}`}>
                              {res.error ? 'Error' : `Run ${i + 1}`}
                            </div>
                            {res.input && (
                              <div className="border-b border-line px-3 py-2">
                                <div className="mb-1 text-xs text-ink-3">Input</div>
                                <pre className="whitespace-pre-wrap font-mono text-[13px]">{res.input}</pre>
                              </div>
                            )}
                            <div className="px-3 py-2">
                              <div className="mb-1 text-xs text-ink-3">Output</div>
                              <pre className={`whitespace-pre-wrap font-mono text-[13px] ${res.error ? 'text-tomato-ink' : ''}`}>{res.error || res.output || '(no output)'}</pre>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <PanelNote title="Nothing has run yet">Turn on custom input, then press Run to see what your program prints.</PanelNote>
                    )}
                  </div>
                )}

                {rightPanelTab === 'logic' && result?.logic_analysis && (
                  <div className="h-full overflow-y-auto p-5">
                    <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
                      <LogicReport
                        data={{
                          logic_correctness: result.logic_analysis.logic_correctness,
                          analysis: result.logic_analysis.analysis,
                          breakdown: result.logic_analysis.breakdown,
                          suggestions: result.logic_analysis.suggestions,
                        }}
                        showPredicted={false}
                      />
                      <dl className="h-fit rounded-md border border-line">
                        <div className="flex items-baseline justify-between border-b border-line px-4 py-3">
                          <dt className="text-ink-2">Tests passed</dt>
                          <dd className="numeral text-2xl">{result.passed_tests} of {result.total_tests}</dd>
                        </div>
                        <div className="flex items-baseline justify-between px-4 py-3">
                          <dt className="text-ink-2">Final score</dt>
                          <dd className="numeral text-2xl">{result.score}</dd>
                        </div>
                        <p className="border-t border-line px-4 py-3 text-xs text-ink-3">Partial credit is awarded when only some tests pass.</p>
                      </dl>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
