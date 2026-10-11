import React, { useEffect, useState, useRef } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import Icon from '../components/Icons'
import { connectSocket } from '../services/socket'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import Leaderboard from '../components/Leaderboard'
import Timer from '../components/Timer'
import { attachProtectedRegion } from '../utils/protectedRegion'
import MathText from '../components/MathText'

const LANGUAGES = [
  { value: 'python', label: 'Python', monaco: 'python' },
  { value: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { value: 'cpp', label: 'C++', monaco: 'cpp' },
  { value: 'java', label: 'Java', monaco: 'java' },
  { value: 'c', label: 'C', monaco: 'c' },
]

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

const DIFFICULTY_COLORS = {
  easy: { bg: 'rgba(16, 185, 129, 0.15)', text: '#34d399', border: '#059669' },
  medium: { bg: 'rgba(245, 158, 11, 0.15)', text: '#fbbf24', border: '#d97706' },
  hard: { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171', border: '#dc2626' },
}

const ACTIVITY_ICONS = {
  problem: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" fill="currentColor" fillOpacity="0.1"/>
      <path d="M9 9h6M9 12h6M9 15h4" strokeWidth="2"/>
      <circle cx="7" cy="9" r="0.5" fill="currentColor"/>
      <circle cx="7" cy="12" r="0.5" fill="currentColor"/>
      <circle cx="7" cy="15" r="0.5" fill="currentColor"/>
    </svg>
  ),
  code: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6"/>
      <polyline points="8 6 2 12 8 18"/>
    </svg>
  ),
  test: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4"/>
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
    </svg>
  ),
  custom: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 14.66V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h5.34"/>
      <polygon points="18 2 22 6 12 16 8 16 8 12 18 2"/>
    </svg>
  ),
  console: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5"/>
      <line x1="12" y1="19" x2="20" y2="19"/>
    </svg>
  ),
  leaderboard: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" fill="currentColor" fillOpacity="0.1"/>
      <path d="M8 14v3M12 11v6M16 8v9" strokeWidth="2"/>
      <circle cx="12" cy="6" r="1.5" fill="currentColor"/>
    </svg>
  ),
  users: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" fill="currentColor" fillOpacity="0.1"/>
      <circle cx="9" cy="9" r="2" strokeWidth="2"/>
      <circle cx="15" cy="9" r="2" strokeWidth="2"/>
      <path d="M6 16c0-1.5 1.5-3 3-3s3 1.5 3 3" strokeWidth="2"/>
      <path d="M12 16c0-1.5 1.5-3 3-3s3 1.5 3 3" strokeWidth="2"/>
    </svg>
  ),
  aiAnalyzer: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" fill="currentColor" fillOpacity="0.15"/>
      <circle cx="12" cy="12" r="4" strokeWidth="2"/>
      <path d="M12 8v8M8 12h8" strokeWidth="2"/>
      <circle cx="12" cy="12" r="1.5" fill="currentColor"/>
      <path d="M17 7l1-1M7 7L6 6M17 17l1 1M7 17l-1 1" strokeWidth="2"/>
    </svg>
  ),
  complexity: (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" fill="currentColor" fillOpacity="0.15"/>
      <path d="M7 17l3-6 4 4 3-8" strokeWidth="2.5" strokeLinecap="round"/>
      <circle cx="7" cy="17" r="1" fill="currentColor"/>
      <circle cx="10" cy="11" r="1" fill="currentColor"/>
      <circle cx="14" cy="15" r="1" fill="currentColor"/>
      <circle cx="17" cy="7" r="1" fill="currentColor"/>
    </svg>
  ),
}

// ─────────────────────────────────────────────────────────────────────────────
// Complexity Visualization Chart (pure SVG, no external library)
// ─────────────────────────────────────────────────────────────────────────────
function ComplexityChart({ userComplexity }) {
  const W = 340, H = 180
  const PAD = { top: 12, right: 16, bottom: 36, left: 36 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom
  const N = 20  // x-axis: input size 1..20

  // Map complexity notation → function value at n
  function complexityValue(notation, n) {
    switch (notation) {
      case 'O(1)':       return 1
      case 'O(log n)':   return Math.log2(n + 1)
      case 'O(sqrt n)':  return Math.sqrt(n)
      case 'O(n)':       return n
      case 'O(n log n)': return n * Math.log2(n + 1)
      case 'O(n²)':      return n * n
      case 'O(2^n)':     return Math.min(Math.pow(2, n), N * N * 4)
      case 'O(n!)':      return Math.min(n <= 8 ? [1,1,2,6,24,120,720,5040,40320][n] || N*N*4 : N*N*4, N*N*4)
      default:           return n
    }
  }

  const CURVES = [
    { label: 'O(1)',      color: '#22c55e',  dash: '' },
    { label: 'O(log n)',  color: '#3b82f6',  dash: '' },
    { label: 'O(n)',      color: '#60a5fa',  dash: '' },
    { label: 'O(n log n)',color: '#f59e0b',  dash: '' },
    { label: 'O(n²)',     color: '#ef4444',  dash: '' },
  ]

  // Compute max value across all curves for scaling
  const allVals = CURVES.flatMap(c => Array.from({length: N}, (_, i) => complexityValue(c.label, i + 1)))
  const maxVal = Math.max(...allVals, 1)

  function toX(n) { return PAD.left + ((n - 1) / (N - 1)) * chartW }
  function toY(v) { return PAD.top + chartH - (Math.min(v, maxVal) / maxVal) * chartH }

  function makePath(label) {
    const pts = Array.from({length: N}, (_, i) => {
      const n = i + 1
      return `${toX(n).toFixed(1)},${toY(complexityValue(label, n)).toFixed(1)}`
    })
    return 'M' + pts.join('L')
  }

  // X-axis ticks
  const xTicks = [1, 5, 10, 15, 20]
  // Y-axis ticks (0, 25, 50, 75, 100 as % of max)
  const yTicks = [0, 25, 50, 75, 100]

  // Determine if user's complexity matches one of our curves
  const userLabel = userComplexity || null

  return (
    <svg width={W} height={H} style={{ display: 'block', maxWidth: '100%' }}>
      {/* Grid lines */}
      {yTicks.map(pct => {
        const y = PAD.top + chartH - (pct / 100) * chartH
        return (
          <line key={pct} x1={PAD.left} y1={y} x2={PAD.left + chartW} y2={y}
            stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="3,3" />
        )
      })}
      {xTicks.map(n => {
        const x = toX(n)
        return (
          <line key={n} x1={x} y1={PAD.top} x2={x} y2={PAD.top + chartH}
            stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="3,3" />
        )
      })}

      {/* Axes */}
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + chartH}
        stroke="rgba(255,255,255,0.2)" strokeWidth="1" />
      <line x1={PAD.left} y1={PAD.top + chartH} x2={PAD.left + chartW} y2={PAD.top + chartH}
        stroke="rgba(255,255,255,0.2)" strokeWidth="1" />

      {/* Axis labels */}
      <text x={PAD.left + chartW / 2} y={H - 4} textAnchor="middle"
        fill="rgba(148,163,184,0.7)" fontSize="9">Input Size (n)</text>
      <text x={10} y={PAD.top + chartH / 2} textAnchor="middle"
        fill="rgba(148,163,184,0.7)" fontSize="9"
        transform={`rotate(-90, 10, ${PAD.top + chartH / 2})`}>Operations</text>

      {/* X tick labels */}
      {xTicks.map(n => (
        <text key={n} x={toX(n)} y={PAD.top + chartH + 12} textAnchor="middle"
          fill="rgba(148,163,184,0.6)" fontSize="8">{n}</text>
      ))}

      {/* Y tick labels */}
      {yTicks.map(pct => {
        const y = PAD.top + chartH - (pct / 100) * chartH
        return (
          <text key={pct} x={PAD.left - 4} y={y + 3} textAnchor="end"
            fill="rgba(148,163,184,0.6)" fontSize="8">{pct}</text>
        )
      })}

      {/* Complexity curves */}
      {CURVES.map(c => {
        const isUser = userLabel === c.label
        return (
          <path key={c.label} d={makePath(c.label)}
            fill="none"
            stroke={c.color}
            strokeWidth={isUser ? 2.5 : 1.2}
            strokeOpacity={isUser ? 1 : 0.45}
            strokeDasharray={isUser ? '' : ''}
          />
        )
      })}

      {/* User's code curve highlight (if not in standard list) */}
      {userLabel && !CURVES.find(c => c.label === userLabel) && (
        <path d={makePath(userLabel)} fill="none" stroke="#60a5fa" strokeWidth="2.5" />
      )}

      {/* "Your Code" label on the user curve */}
      {userLabel && (() => {
        const midN = Math.floor(N * 0.6)
        const x = toX(midN)
        const y = toY(complexityValue(userLabel, midN))
        return (
          <g>
            <circle cx={x} cy={y} r="3" fill="#60a5fa" />
            <text x={x + 5} y={y - 4} fill="#60a5fa" fontSize="8" fontWeight="bold">Your Code</text>
          </g>
        )
      })()}
    </svg>
  )
}

// Legend for the chart
function ChartLegend({ userComplexity }) {
  const items = [
    { label: 'O(1)',       color: '#22c55e' },
    { label: 'O(log n)',   color: '#3b82f6' },
    { label: 'O(n)',       color: '#60a5fa' },
    { label: 'O(n log n)', color: '#f59e0b' },
    { label: 'O(n²)',      color: '#ef4444' },
  ]
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
      {items.map(it => (
        <div key={it.label} className="flex items-center gap-1">
          <div className="w-4 h-0.5 rounded" style={{
            background: it.color,
            opacity: userComplexity === it.label ? 1 : 0.5,
            height: userComplexity === it.label ? '2px' : '1.5px',
          }} />
          <span className="text-[9px]" style={{
            color: userComplexity === it.label ? it.color : 'rgba(148,163,184,0.6)',
            fontWeight: userComplexity === it.label ? 700 : 400,
          }}>
            {it.label}{userComplexity === it.label ? ' — Your Code' : ''}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function Game() {
  const { code } = useParams()
  const { state } = useLocation()

  // ── Dynamic feedback helpers ──────────────────────────────────────────────
  function _dynamicAnalysis(passed, total) {
    const pct = total > 0 ? Math.round((passed / total) * 100) : 0
    const failed = total - passed
    if (passed === total) return `All ${total} test cases passed! Your solution is correct.`
    const analyses = [
      `${passed}/${total} test cases passed (${pct}%). Check the failing cases for hints.`,
      `${failed} of ${total} tests are failing (${pct}% pass rate). Review your logic.`,
      `Your solution passes ${passed} out of ${total} tests. Trace through the failing inputs.`,
      `${pct}% correct — ${failed} test case${failed > 1 ? 's' : ''} still failing. Look at the expected vs actual output.`,
      `${passed}/${total} tests pass. Debug the ${failed} failing case${failed > 1 ? 's' : ''} to find the issue.`,
    ]
    return analyses[Math.floor(Math.random() * analyses.length)]
  }

  function _perfectSuggestions() {
    const pool = [
      'Perfect score! All test cases passed.',
      'Flawless solution — every test case passed!',
      'All tests green! Your logic is correct.',
      'Perfect! Submit to lock in your score.',
      '100% — excellent work!',
    ]
    return [pool[Math.floor(Math.random() * pool.length)]]
  }

  function _dynamicSuggestions(passed, total, failedTcs = []) {
    const failed = total - passed
    const pct = total > 0 ? Math.round((passed / total) * 100) : 0

    // Build a pool of varied, specific suggestions
    const pool = []

    if (pct === 0) {
      pool.push(
        `All ${total} test cases failing — check your core algorithm logic`,
        `Start by tracing through the sample input manually`,
        `Your output format may be wrong — check the expected output carefully`,
        `Make sure you're reading the input correctly (check the Input Format section)`,
        `Add print statements to see what your code actually produces`,
      )
    } else if (pct < 50) {
      pool.push(
        `${failed} test case${failed > 1 ? 's' : ''} failing — your approach handles some cases but misses others`,
        `Check edge cases: empty input, single element, all-same values`,
        `Your logic works for simple cases but breaks on complex ones`,
        `Look at the first failing test — what's different about that input?`,
        `Compare your output format with the expected output exactly`,
      )
    } else if (pct < 100) {
      pool.push(
        `${failed} edge case${failed > 1 ? 's' : ''} still failing — you're close!`,
        `Check: negative numbers, zero values, maximum constraints`,
        `Your main logic is right — look for off-by-one errors or boundary conditions`,
        `Click a failing test case to compare expected vs actual output`,
        `Check if your solution handles the minimum and maximum input sizes`,
      )
    }

    // Always add a "click failing test" hint
    pool.push(`Click a failing test case below to see the exact input, expected, and actual output`)

    // Shuffle and pick 2–3 unique suggestions
    const shuffled = pool.sort(() => Math.random() - 0.5)
    return shuffled.slice(0, Math.floor(Math.random() * 2) + 2)
  }
  const { user } = useAuth()
  const nav = useNavigate()

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
  const grokChatEndRef = useRef(null)
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
      const newWidth = e.clientX - 14 // Account for icon sidebar (14px)
      
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

  // Auto-scroll Grok chat to bottom when new messages arrive
  useEffect(() => {
    grokChatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [grokMessages])

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
      setGrokMessages(prev => [...prev, { role: 'assistant', content: `${errMsg}` }])
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

  function renderMarkdown(text) {
    if (!text) return null
    const lines = text.split('\n')
    const elements = []
    let key = 0

    const HEADERS = ['Input Format', 'Output Format', 'Constraints', 'Sample Input', 'Sample Output', 'Explanation']
    const headerRe = new RegExp(`^\\*\\*(${HEADERS.join('|')})\\*\\*$`)
    // Skip these — they duplicate the test case examples shown below the description
    const SKIP_SECTIONS = new Set(['Sample Input', 'Sample Output'])

    function renderKeywords(text) {
      if (!text) return text
      const keywords = ['integer', 'string', 'boolean', 'float', 'double', 'array', 'int']
      const parts = text.split(new RegExp(`\\b(${keywords.join('|')})\\b`, 'gi'))
      if (parts.length <= 1) return text
      return parts.map((w, j) =>
        keywords.includes(w.toLowerCase())
          ? <span key={j} style={{ color: '#22d3ee', fontWeight: 500 }}>{w}</span>
          : w
      )
    }

    function renderBoldLine(line) {
      if (!line) return ''
      const parts = line.split(/(\*\*[^*]+\*\*)/)
      return parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**')
          ? <strong key={i} style={{ color: '#f1f5f9', fontWeight: 600 }}><MathText text={p.slice(2, -2)} /></strong>
          : <MathText key={i} text={p} />
      )
    }

    const boxStyle = {
      background: 'rgba(30, 30, 50, 0.6)',
      padding: '14px 18px',
      borderRadius: '10px',
      fontFamily: "'JetBrains Mono','Fira Code',monospace",
      fontSize: '13px',
      lineHeight: '1.7',
      color: '#e2e8f0',
      border: '1px solid rgba(255, 255, 255, 0.08)',
    }

    let i = 0
    while (i < lines.length) {
      const line = lines[i]
      const headerMatch = line.match(headerRe)

      if (headerMatch) {
        const sectionName = headerMatch[1]
        const sectionLines = []
        i++
        while (i < lines.length && !lines[i].match(headerRe)) {
          sectionLines.push(lines[i])
          i++
        }
        const content = sectionLines.join('\n').trim()
        const isExplanation = sectionName === 'Explanation'
        const isSample = ['Sample Input', 'Sample Output'].includes(sectionName)

        // Skip Sample Input/Output — already shown as test case examples
        if (SKIP_SECTIONS.has(sectionName)) continue

        const accentColors = {
          'Input Format': '#22d3ee',
          'Output Format': '#60a5fa',
          'Constraints': '#fbbf24',
          'Sample Input': '#34d399',
          'Sample Output': '#34d399',
          'Explanation': '#22d3ee',
        }

        elements.push(
          <div key={key++} style={{ marginBottom: '18px' }}>
            <div style={{ 
              fontSize: '12px', 
              fontWeight: 700, 
              color: accentColors[sectionName] || '#94a3b8', 
              marginBottom: '10px', 
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}>
              <span style={{ 
                width: '3px', 
                height: '14px', 
                background: accentColors[sectionName] || '#94a3b8',
                borderRadius: '2px',
              }} />
              {sectionName}
            </div>
            <div style={boxStyle}>
              {isSample ? (
                <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
              ) : (
                sectionLines.filter(l => l.trim()).map((l, lIdx) => (
                  <div key={lIdx} style={{ marginBottom: lIdx < sectionLines.length - 1 ? '6px' : 0 }}>
                    {renderBoldLine(l.trim())}
                  </div>
                ))
              )}
            </div>
          </div>
        )
      } else {
        if (line.trim()) {
          elements.push(
            <p key={key++} style={{ color: '#cbd5e1', fontSize: '14px', lineHeight: '1.7', marginBottom: '10px' }}>
              {renderBoldLine(line)}
            </p>
          )
        }
        i++
      }
    }
    return elements.length > 0 ? elements : (
      <p style={{ color: '#cbd5e1', fontSize: '14px', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}><MathText text={text} /></p>
    )
  }

  if (roundEnded && !gameOver) {
    const isLastRound = currentRound >= totalRounds
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-hero-glow pointer-events-none" />
        <div className="relative text-center ">
          <Icon name="bars" size={44} className="mb-4" />
          <h2 className="text-3xl font-extrabold text-white mb-1">Round {currentRound} Complete</h2>
          <p className="text-slate-400 mb-6">{isLastRound ? 'Final standings' : `${totalRounds - currentRound} round(s) remaining`}</p>
          <div className="glass rounded-2xl p-6 w-full max-w-sm mx-auto glow mb-6">
            <Leaderboard entries={roundLeaderboard} currentPlayerId={playerId} />
          </div>
          {isLastRound ? (
            <button onClick={endGame} className="btn-primary px-10 py-3 text-base">Finish Game</button>
          ) : (
            <button onClick={() => { setRoundEnded(false); setQuestion(null); setCurrentRound(prev => prev + 1) }} className="btn-primary px-10 py-3 text-base">Next Round</button>
          )}
        </div>
      </div>
    )
  }

  if (gameOver) {
    const winner = leaderboard[0]
    const myEntry = leaderboard.find(e => (e.player_id ?? e.id) === playerId)
    const myRank = myEntry ? (leaderboard.indexOf(myEntry) + 1) : null

    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden"
        style={{ background: '#0d0d14' }}>
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.15) 0%, transparent 70%)' }} />

        <div className="relative w-full max-w-lg ">
          {/* Header */}
          <div className="text-center mb-8">
            <Icon name="trophy" size={52} className="mb-3" />
            <h2 className="text-4xl font-extrabold text-white mb-1">Game Over!</h2>
            {myRank === 1
              ? <p className="text-amber-400 font-semibold">You won!</p>
              : myRank
              ? <p className="text-slate-400">You finished #{myRank}</p>
              : <p className="text-slate-400">Final standings</p>
            }
          </div>

          {/* Leaderboard Table */}
          <div className="rounded-2xl overflow-hidden mb-6"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
            {/* Table header */}
            <div className="grid grid-cols-12 px-5 py-3 text-[11px] font-semibold text-slate-500"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              <span className="col-span-1">#</span>
              <span className="col-span-7">Player</span>
              <span className="col-span-2 text-center">Solved</span>
              <span className="col-span-2 text-right">Score</span>
            </div>

            {leaderboard.length === 0 ? (
              <div className="text-center py-10 text-slate-500 text-sm">No scores recorded</div>
            ) : (
              leaderboard.map((entry, i) => {
                const isMe = (entry.player_id ?? entry.id) === playerId
                const medals = ['1', '2', '3']
                return (
                  <div key={entry.player_id ?? entry.id ?? i}
                    className="grid grid-cols-12 px-5 py-4 items-center transition-all"
                    style={{
                      background: isMe ? 'rgba(99,102,241,0.12)' : i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
                      borderBottom: i < leaderboard.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                      borderLeft: isMe ? '3px solid #6366f1' : '3px solid transparent',
                    }}>
                    <span className="col-span-1 text-lg">
                      {medals[i] ?? <span className="text-slate-500 text-sm font-mono">{i + 1}</span>}
                    </span>
                    <div className="col-span-7 flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                        style={{ background: isMe ? 'linear-gradient(135deg,#6366f1,#3b82f6)' : 'rgba(255,255,255,0.1)' }}>
                        {entry.username?.[0]?.toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold text-sm" style={{ color: isMe ? '#a5b4fc' : '#e2e8f0' }}>
                          {entry.username} {isMe && <span className="text-xs text-indigo-400">(you)</span>}
                        </div>
                        {i === 0 && <div className="text-[10px] text-amber-400">Winner</div>}
                      </div>
                    </div>
                    <div className="col-span-2 text-center text-sm font-medium text-slate-300">
                      {entry.questions_solved ?? 0}
                    </div>
                    <div className="col-span-2 text-right font-bold text-base"
                      style={{ color: isMe ? '#a5b4fc' : '#f1f5f9' }}>
                      {entry.score ?? 0}
                    </div>
                  </div>
                )
              })
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={() => nav('/home')}
              className="flex-1 py-3 rounded-xl font-semibold text-sm text-white transition-all"
              style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}>
              Back to Home
            </button>
            <button onClick={() => nav('/home')}
              className="flex-1 py-3 rounded-xl font-bold text-sm text-white transition-all"
              style={{ background: 'linear-gradient(135deg,#6366f1,#3b82f6)' }}>
              Play Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  const passedCount = testCaseDetails.filter(tc => tc.passed === true).length
  const totalTests = testCaseDetails.length
  const currentLang = LANGUAGES.find(l => l.value === lang) || LANGUAGES[0]

  return (
    <div className="h-screen flex overflow-hidden relative" style={{ background: '#000000', fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Animated Background */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-blue-500/20 rounded-full blur-[120px] " />
        <div className="absolute bottom-0 right-1/4 w-[700px] h-[700px] bg-cyan-500/15 rounded-full blur-[130px] " style={{ animationDelay: '3s' }} />
        <div className="absolute inset-0 opacity-[0.08]" style={{ 
          backgroundImage: 'linear-gradient(rgba(59, 130, 246, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.1) 1px, transparent 1px)', 
          backgroundSize: '50px 50px' 
        }} />
      </div>

      {/* ── Time Up Popup ─────────────────────────────────────────────────── */}
      {timeUp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(12px)' }}>
          <div className="rounded-2xl p-8 flex flex-col items-center gap-4 relative"
            style={{ background: 'linear-gradient(135deg,#1a1a2e,#16213e)', border: '1px solid rgba(248,113,113,0.4)', boxShadow: '0 0 60px rgba(248,113,113,0.3)', minWidth: 280 }}>
            <div className="absolute -inset-1 bg-gradient-to-r from-rose-600/20 to-cyan-600/20 rounded-2xl blur-xl" />
            <div className="relative">
              {/* Ringing clock emoji with shake animation */}
              <Icon name="clock" size={14} className="" />
            </div>
            <div className="text-2xl font-bold text-white relative">Time's Up!</div>
            <div className="text-sm text-slate-400 text-center relative">
              {answeredRef.current + 1 >= questionsPerRound * totalRounds
                ? 'Submitting your code...'
                : 'Moving to next question...'}
            </div>
            <div className="flex gap-1 mt-1 relative">
              {[0,1,2].map(i => (
                <div key={i} className="w-2 h-2 rounded-full bg-rose-400"
                  style={{ animation: `bounce 0.6s ease-in-out ${i * 0.15}s infinite` }} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Waiting for Others to Submit Popup ───────────────────────────── */}
      {waitingForOthers && !showCompletionPopup && !gameOver && (
        <div className="fixed inset-0 z-[85] flex items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(12px)' }}>
          <div className="relative w-full max-w-sm mx-4 rounded-2xl overflow-hidden "
            style={{
              background: 'linear-gradient(145deg,#0f0f1a,#1a1a2e)',
              border: '1px solid rgba(99,102,241,0.3)',
              boxShadow: '0 0 60px rgba(99,102,241,0.2), 0 20px 40px rgba(0,0,0,0.5)',
            }}>
            <div className="h-1 w-full" style={{ background: 'linear-gradient(90deg,#6366f1,#3b82f6,#06b6d4)' }} />
            <div className="p-7 text-center">
              <div className="text-5xl mb-3">⏳</div>
              <h2 className="text-xl font-extrabold text-white mb-1">Submitted!</h2>
              <p className="text-slate-400 text-sm mb-5">Waiting for other players to submit the current question…</p>

              {/* Submitted counter dots */}
              <div className="flex items-center justify-center gap-3 mb-5">
                <div className="flex gap-2">
                  {Array.from({ length: Math.max(waitingTotal, 2) }).map((_, i) => (
                    <div key={i}
                      className="w-4 h-4 rounded-full transition-all duration-500"
                      style={{
                        background: i < submittedCount
                          ? 'linear-gradient(135deg,#10b981,#059669)'
                          : 'rgba(255,255,255,0.1)',
                        boxShadow: i < submittedCount ? '0 0 10px rgba(16,185,129,0.6)' : 'none',
                      }} />
                  ))}
                </div>
                <span className="text-sm font-semibold text-slate-300">
                  {submittedCount}/{waitingTotal} submitted
                </span>
              </div>

              {/* Animated dots */}
              <div className="flex gap-1.5 justify-center">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-2 h-2 rounded-full bg-indigo-400"
                    style={{ animation: `bounce 1s ease-in-out ${i * 0.2}s infinite` }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── All Questions Completed Popup ─────────────────────────────────── */}
      {showCompletionPopup && !gameOver && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.88)', backdropFilter: 'blur(16px)' }}>
          <div className="relative w-full max-w-md mx-4 rounded-3xl overflow-hidden "
            style={{
              background: 'linear-gradient(145deg,#0f0f1a,#1a1a2e)',
              border: '1px solid rgba(99,102,241,0.35)',
              boxShadow: '0 0 80px rgba(99,102,241,0.25), 0 30px 60px rgba(0,0,0,0.6)',
            }}>
            {/* Glow top bar */}
            <div className="h-1 w-full" style={{ background: 'linear-gradient(90deg,#6366f1,#3b82f6,#06b6d4)' }} />

            <div className="p-8">
              {/* Header */}
              <div className="text-center mb-6">
                <Icon name="bolt" size={52} className="mb-3" />
                <h2 className="text-2xl font-extrabold text-white mb-2">You're Fast!</h2>
                <p className="text-slate-400 text-sm leading-relaxed">
                  You've completed all {questionsPerRound * totalRounds} question{questionsPerRound * totalRounds !== 1 ? 's' : ''}.
                  <br />Waiting for other players to finish…
                </p>

                {/* Progress counter */}
                {totalPlayerCount > 0 && (
                  <div className="mt-4 flex items-center justify-center gap-3">
                    <div className="flex gap-1.5">
                      {Array.from({ length: totalPlayerCount }).map((_, i) => (
                        <div key={i} className="w-3 h-3 rounded-full transition-all duration-500"
                          style={{
                            background: i < finishedCount
                              ? 'linear-gradient(135deg,#6366f1,#3b82f6)'
                              : 'rgba(255,255,255,0.12)',
                            boxShadow: i < finishedCount ? '0 0 8px rgba(99,102,241,0.6)' : 'none',
                          }} />
                      ))}
                    </div>
                    <span className="text-sm font-semibold text-slate-300">
                      {finishedCount}/{totalPlayerCount} done
                    </span>
                  </div>
                )}

                {/* Animated waiting dots */}
                <div className="flex gap-1.5 justify-center mt-4">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-2 h-2 rounded-full bg-indigo-400"
                      style={{ animation: `bounce 1s ease-in-out ${i * 0.2}s infinite` }} />
                  ))}
                </div>
              </div>

              {/* Live leaderboard */}
              <div className="rounded-2xl overflow-hidden mb-6"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <div className="px-4 py-2.5 text-[10px] font-bold text-slate-500 flex items-center gap-2"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <Icon name="trophy" size={14} className="" /> Live Standings
                </div>
                <div className="grid grid-cols-12 px-4 py-2 text-[10px] font-bold text-slate-500"
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  <span className="col-span-1">#</span>
                  <span className="col-span-7">Player</span>
                  <span className="col-span-2 text-center">Solved</span>
                  <span className="col-span-2 text-right">Score</span>
                </div>

                {leaderboard.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 text-sm">Scores loading…</div>
                ) : (
                  leaderboard.map((entry, i) => {
                    const isMe = (entry.player_id ?? entry.id) === playerId
                    const medals = ['1', '2', '3']
                    return (
                      <div key={entry.player_id ?? entry.id ?? i}
                        className="grid grid-cols-12 px-4 py-3 items-center"
                        style={{
                          background: isMe ? 'rgba(99,102,241,0.12)' : 'transparent',
                          borderBottom: i < leaderboard.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                          borderLeft: isMe ? '3px solid #6366f1' : '3px solid transparent',
                        }}>
                        <span className="col-span-1 text-base">
                          {medals[i] ?? <span className="text-slate-500 text-xs font-mono">{i + 1}</span>}
                        </span>
                        <div className="col-span-7 flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                            style={{ background: isMe ? 'linear-gradient(135deg,#6366f1,#3b82f6)' : 'rgba(255,255,255,0.1)' }}>
                            {entry.username?.[0]?.toUpperCase()}
                          </div>
                          <span className="text-sm font-semibold truncate" style={{ color: isMe ? '#a5b4fc' : '#e2e8f0' }}>
                            {entry.username} {isMe && <span className="text-xs text-indigo-400">(you)</span>}
                          </span>
                        </div>
                        <div className="col-span-2 text-center text-sm font-mono text-slate-300">
                          {entry.questions_solved ?? 0}
                        </div>
                        <div className="col-span-2 text-right text-sm font-bold"
                          style={{ color: isMe ? '#a5b4fc' : '#e2e8f0' }}>
                          {Math.round(entry.score ?? 0)}
                        </div>
                      </div>
                    )
                  })
                )}
              </div>

              {/* Leave button */}
              <button
                onClick={() => nav('/home')}
                className="w-full py-3 rounded-xl font-semibold text-sm text-slate-400 transition-all hover:text-white hover:bg-white/[0.06]"
                style={{ border: '1px solid rgba(255,255,255,0.08)' }}>
                Leave Game
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Input Warning Popup */}
      {showCustomWarning && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(12px)' }}>
          <div className="rounded-2xl p-6 max-w-sm w-full mx-4 relative" 
            style={{ 
              background: '#0A0A10',
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.5)'
            }}>
            <div className="absolute -inset-1 bg-gradient-to-r from-amber-600/20 to-orange-600/20 rounded-2xl blur-xl" />
            <div className="relative">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: 'rgba(245,158,11,0.15)' }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                    <line x1="12" y1="9" x2="12" y2="13"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Custom Input Active</h3>
                  <p className="text-xs text-slate-400">Action Required</p>
                </div>
              </div>
              <p className="text-sm text-slate-300 mb-6">
                Custom input is currently enabled. Uncheck the <span className="text-white font-medium">"Use custom input"</span> checkbox first before viewing test cases.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowCustomWarning(false)}
                  className="flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-300 "
                  style={{ 
                    background: 'rgba(255,255,255,0.05)', 
                    color: '#94a3b8',
                    border: '1px solid rgba(255,255,255,0.1)'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setUseCustomInput(false)
                    setShowCustomWarning(false)
                    setRightPanelTab('tests')
                  }}
                  className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 "
                  style={{
                    background: '#3b82f6',
                    color: 'white',
                    border: '1px solid rgba(59, 130, 246, 0.5)'
                  }}
                >
                  Uncheck & Continue
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* LEFT: Activity Bar with Icons */}
      <div className="w-14 flex flex-col items-center py-3 gap-1 shrink-0 relative" style={{ background: '#0A0A10', borderRight: '1px solid rgba(255,255,255,0.07)' }}>
        {/* Problem Icon */}
        <button
          onClick={() => setActivePanel(activePanel === 'problem' ? 'right' : 'problem')}
          className="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 relative group"
          style={{ 
            color: activePanel === 'problem' ? '#60a5fa' : '#64748b',
            background: activePanel === 'problem' ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            border: activePanel === 'problem' ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
            boxShadow: activePanel === 'problem' ? '0 0 20px rgba(59, 130, 246, 0.3)' : 'none',
          }}
          title="Problem"
        >
          {ACTIVITY_ICONS.problem}
        </button>
        
        {/* AI Code Analyzer Icon */}
        <button
          onClick={() => setActivePanel('ai-analyzer')}
          className="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 relative group"
          style={{ 
            color: activePanel === 'ai-analyzer' ? '#60a5fa' : '#64748b',
            background: activePanel === 'ai-analyzer' ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            border: activePanel === 'ai-analyzer' ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
            boxShadow: activePanel === 'ai-analyzer' ? '0 0 20px rgba(59, 130, 246, 0.3)' : 'none',
          }}
          title="AI Code Analyzer"
        >
          {ACTIVITY_ICONS.aiAnalyzer}
          {debugHint && debugHint.logic_correctness !== undefined && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center "
              style={{ 
                background: debugHint.logic_correctness >= 70 ? '#10b981' : debugHint.logic_correctness >= 40 ? '#f59e0b' : '#ef4444',
                color: 'white',
                boxShadow: debugHint.logic_correctness >= 70 ? '0 0 10px rgba(16, 185, 129, 0.5)' : debugHint.logic_correctness >= 40 ? '0 0 10px rgba(245, 158, 11, 0.5)' : '0 0 10px rgba(239, 68, 68, 0.5)',
              }}>
              {Math.round(debugHint.logic_correctness / 10)}
            </span>
          )}
        </button>

        {/* Complexity Analyzer Icon */}
        <button
          onClick={() => setActivePanel('complexity')}
          className="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 relative group"
          style={{ 
            color: activePanel === 'complexity' ? '#60a5fa' : '#64748b',
            background: activePanel === 'complexity' ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            border: activePanel === 'complexity' ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
            boxShadow: activePanel === 'complexity' ? '0 0 20px rgba(59, 130, 246, 0.3)' : 'none',
          }}
          title="Time & Space Complexity"
        >
          {ACTIVITY_ICONS.complexity}
        </button>
        
        {/* Leaderboard Icon */}
        <button
          onClick={() => setActivePanel('leaderboard')}
          className="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 relative group"
          style={{ 
            color: activePanel === 'leaderboard' ? '#60a5fa' : '#64748b',
            background: activePanel === 'leaderboard' ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
            border: activePanel === 'leaderboard' ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
            boxShadow: activePanel === 'leaderboard' ? '0 0 20px rgba(59, 130, 246, 0.3)' : 'none',
          }}
          title="Leaderboard"
        >
          {ACTIVITY_ICONS.leaderboard}
        </button>
        
        <div className="flex-1" />
        
        {/* Players Icon */}
        <button
          className="w-10 h-10 rounded-lg flex items-center justify-center transition-all duration-300 relative group"
          style={{ 
            color: '#64748b',
            background: 'transparent',
            border: '1px solid transparent',
          }}
          title="Players"
        >
          {ACTIVITY_ICONS.users}
        </button>
      </div>

      {/* AI Code Analyzer Panel - Conditional */}
      {activePanel === 'ai-analyzer' && (
        <div className="flex flex-col overflow-hidden relative" style={{ width: `${aiAnalyzerWidth}px`, background: '#0A0A10', borderRight: '1px solid rgba(255,255,255,0.07)' }}>
          
          {/* Resize Handle */}
          <div
            onMouseDown={(e) => {
              e.preventDefault()
              setIsResizingAiAnalyzer(true)
            }}
            className="absolute top-0 right-0 w-2 h-full cursor-ew-resize z-50 group"
            style={{ background: 'transparent', marginRight: '-4px' }}
          >
            <div className="absolute inset-y-0 right-1 w-1 transition-all duration-200" style={{ background: 'rgba(59, 130, 246, 0.3)' }} />
            <div className="absolute inset-y-0 right-1 w-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200" style={{ background: '#3b82f6', boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)' }} />
          </div>
          
          {/* Header */}
          <div className="px-4 py-3 shrink-0" style={{ background: '#101018', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center gap-2">
              <Icon name="message" size={20} className="" />
              <div>
                <div className="text-sm font-bold text-white">AI Code Analyzer</div>
                <div className="text-[10px] text-slate-500">Real-time feedback</div>
              </div>
            </div>
          </div>

        {/* AI Analysis Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!question ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'rgba(59, 130, 246,0.1)' }}>
                <Icon name="target" size={30} className="" />
              </div>
              <div className="text-sm text-slate-400">Generate a problem to start</div>
            </div>
          ) : !editorCode || editorCode === STARTER[lang] || editorCode === generateCodeTemplate(question, lang) ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'rgba(59, 130, 246,0.1)' }}>
                <Icon name="pencil" size={30} className="" />
              </div>
              <div className="text-sm text-slate-400 px-4">Start writing code to get AI analysis</div>
            </div>
          ) : (
            <>
              {/* Code Correctness */}
              <div className="rounded-xl p-4" style={{ background: 'rgba(59, 130, 246,0.1)', border: '1px solid rgba(59, 130, 246,0.3)' }}>
                <div className="flex items-center justify-between mb-3">
                  <div className="text-xs font-semibold text-blue-300">Code Analysis</div>
                  <button 
                    onClick={async () => {
                      if (!question || !editorCode) return

                      // If tests have already run, use those results directly
                      // instead of calling the pre-submission API (which gives 0%)
                      const ranTests = testCaseDetails.filter(tc => tc.passed !== null)
                      if (ranTests.length > 0) {
                        const passedCount = ranTests.filter(tc => tc.passed).length
                        const total = ranTests.length
                        const passRate = Math.round((passedCount / total) * 100)
                        if (passedCount === total) {
                          setDebugHint({
                            logic_correctness: 100,
                            analysis: `All ${total} test cases passed! Your solution is correct.`,
                            predicted_score: 100,
                            suggestions: _perfectSuggestions(),
                            is_pre_submission: false,
                          })
                        } else {
                          setDebugHint({
                            logic_correctness: passRate,
                            analysis: _dynamicAnalysis(passedCount, total),
                            predicted_score: passRate,
                            suggestions: _dynamicSuggestions(passedCount, total, ranTests.filter(tc => !tc.passed)),
                            is_pre_submission: false,
                          })
                        }
                        return
                      }

                      // No tests run yet — call pre-submission analysis
                      setLoadingHint(true)
                      try {
                        const { data } = await api.post('/analyze-code', {
                          code: editorCode,
                          language: lang,
                          problem_statement: question.description || question.problem_statement || '',
                          question_id: question.id
                        })
                        setDebugHint(data)
                      } catch (err) {
                        setDebugHint({ 
                          logic_correctness: 0, 
                          analysis: 'Analysis failed. Try again.',
                          predicted_score: 0,
                          suggestions: []
                        })
                      } finally {
                        setLoadingHint(false)
                      }
                    }}
                    disabled={loadingHint}
                    className="px-2 py-1 rounded text-[10px] font-medium transition-all "
                    style={{ background: 'rgba(59, 130, 246,0.2)', color: '#60a5fa' }}
                  >
                    {loadingHint ? 'Analyzing…' : 'Analyze'}
                  </button>
                </div>

                {debugHint && debugHint.logic_correctness !== undefined ? (
                  <>
                    {/* Correctness Percentage */}
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-slate-400">Code Correctness</span>
                        {debugHint.is_pre_submission ? (
                          <span className="text-xs font-semibold text-slate-400">Run tests to score</span>
                        ) : (
                          <span className="text-lg font-bold" 
                            style={{ 
                              color: debugHint.logic_correctness >= 70 ? '#34d399' 
                                : debugHint.logic_correctness >= 40 ? '#fbbf24' 
                                : '#f87171' 
                            }}
                          >
                            {debugHint.logic_correctness}%
                          </span>
                        )}
                      </div>
                      <div className="h-3 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                        <div 
                          className="h-full transition-all duration-500" 
                          style={{ 
                            width: debugHint.is_pre_submission ? '0%' : `${debugHint.logic_correctness}%`,
                            background: debugHint.logic_correctness >= 70 
                              ? 'linear-gradient(90deg, #10b981, #34d399)' 
                              : debugHint.logic_correctness >= 40 
                              ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' 
                              : 'linear-gradient(90deg, #ef4444, #f87171)'
                          }}
                        />
                      </div>
                    </div>

                    {/* Predicted Score */}
                    <div className="rounded-lg p-3 mb-3" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
                      <div className="text-[10px] text-emerald-400 font-semibold mb-1">Predicted Score</div>
                      <div className="flex items-baseline gap-2">
                        {debugHint.is_pre_submission ? (
                          <span className="text-sm text-slate-400">Run tests first</span>
                        ) : (
                          <>
                            <span className="text-2xl font-bold text-emerald-300">{debugHint.predicted_score ?? Math.round(debugHint.logic_correctness)}</span>
                            <span className="text-xs text-slate-400">/ 100 points</span>
                          </>
                        )}
                      </div>
                      {!debugHint.is_pre_submission && <div className="text-[10px] text-slate-500 mt-1">If you submit now</div>}
                    </div>

                    {/* AI Analysis */}
                    {debugHint.analysis && (
                      <div className="rounded-lg p-3 mb-3" style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)' }}>
                        <div className="text-[10px] text-blue-300 font-semibold mb-2">AI Feedback</div>
                        <div className="text-xs text-slate-300 leading-relaxed">{debugHint.analysis}</div>
                      </div>
                    )}

                    {/* Suggestions */}
                    {debugHint.suggestions && debugHint.suggestions.length > 0 && (
                      <div className="rounded-lg p-3" style={{ background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.2)' }}>
                        <div className="text-[10px] text-yellow-300 font-semibold mb-2 flex items-center gap-1">
                          <Icon name="bulb" size={14} className="" /> Hints to Improve
                        </div>
                        <ul className="space-y-1.5">
                          {debugHint.suggestions.slice(0, 3).map((suggestion, idx) => (
                            <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                              <span className="text-yellow-400 mt-0.5 text-[10px]">•</span>
                              <span className="flex-1">{suggestion}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-6">
                    <div className="text-xs text-slate-400 mb-2">Click "Analyze" to check your code</div>
                    <div className="text-[10px] text-slate-500">Get instant feedback before submitting</div>
                  </div>
                )}
              </div>

              {/* Quick Stats */}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg p-3 text-center" style={{ background: 'rgba(59, 130, 246,0.1)', border: '1px solid rgba(59, 130, 246,0.2)' }}>
                  <div className="text-xs text-blue-300 font-semibold">{editorCode.split('\n').length}</div>
                  <div className="text-[10px] text-slate-500">Lines</div>
                </div>
                <div className="rounded-lg p-3 text-center" style={{ background: 'rgba(59, 130, 246,0.1)', border: '1px solid rgba(59, 130, 246,0.2)' }}>
                  <div className="text-xs text-blue-300 font-semibold">{lang.toUpperCase()}</div>
                  <div className="text-[10px] text-slate-500">Language</div>
                </div>
              </div>

              {/* Test Results (if available) */}
              {testCaseDetails.length > 0 && (
                <div className="rounded-xl p-4" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <div className="text-xs font-semibold text-emerald-300 mb-3">Test Results</div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Tests Passed</span>
                    <span className="text-lg font-bold" style={{ color: passedCount === totalTests ? '#34d399' : '#fbbf24' }}>
                      {passedCount}/{totalTests}
                    </span>
                  </div>
                </div>
              )}

              {/* ── AI Feedback Chat ── */}
              <div className="rounded-xl overflow-hidden" style={{ background: '#101018', border: '1px solid rgba(59, 130, 246,0.3)' }}>
                {/* Chat header */}
                <div className="px-3 py-2.5 flex items-center justify-between" style={{ background: 'rgba(59, 130, 246,0.12)', borderBottom: '1px solid rgba(59, 130, 246,0.2)' }}>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded-full flex items-center justify-center text-[11px]" style={{ background: 'linear-gradient(135deg,#2563eb,#db2777)' }}><Icon name="message" size={11} className="text-white" /></div>
                    <span className="text-xs font-bold text-white">Ask AI Coach</span>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ background: 'rgba(59, 130, 246,0.25)', color: '#60a5fa' }}>NVIDIA</span>
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
                      <Icon name="message" size={24} className="mx-auto mb-2 text-slate-500" />
                      <div className="text-[11px] text-slate-400 mb-1">Ask anything about your code</div>
                      <div className="text-[10px] text-slate-500">e.g. "Why is my solution O(n²)?" or "How do I fix this bug?"</div>
                    </div>
                  )}
                  {grokMessages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      {msg.role === 'assistant' && (
                        <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] shrink-0 mr-2 mt-0.5" style={{ background: 'linear-gradient(135deg,#2563eb,#db2777)' }}><Icon name="message" size={11} className="text-white" /></div>
                      )}
                      <div
                        className="rounded-xl px-3 py-2 text-[11px] leading-relaxed max-w-[85%]"
                        style={msg.role === 'user'
                          ? { background: 'rgba(59, 130, 246,0.25)', color: '#e2e8f0', borderBottomRightRadius: '4px' }
                          : { background: 'rgba(255,255,255,0.05)', color: '#cbd5e1', borderBottomLeftRadius: '4px', border: '1px solid rgba(255,255,255,0.07)' }
                        }
                      >
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {grokLoading && (
                    <div className="flex justify-start">
                      <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] shrink-0 mr-2 mt-0.5" style={{ background: 'linear-gradient(135deg,#2563eb,#db2777)' }}><Icon name="message" size={11} className="text-white" /></div>
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
                        className="px-2 py-1 rounded-full text-[10px] transition-all active:scale-95 disabled:opacity-40"
                        style={{ background: 'rgba(59, 130, 246,0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246,0.25)' }}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                )}

                {/* Input box */}
                <div className="p-2.5 pt-0" style={{ borderTop: grokMessages.length > 0 ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
                  <div className="flex gap-2 items-end rounded-xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(59, 130, 246,0.25)' }}>
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
                      className="m-1.5 w-7 h-7 rounded-lg flex items-center justify-center transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
                      style={{ background: grokInput.trim() ? 'linear-gradient(135deg,#2563eb,#a855f7)' : 'rgba(59, 130, 246,0.2)' }}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                      </svg>
                    </button>
                  </div>
                  <div className="text-[9px] text-slate-500 mt-1 px-1">Shift+Enter for new line · Powered by NVIDIA NIM</div>
                </div>
              </div>
            </>
          )}
        </div>
        </div>
      )}

      {/* Complexity Analyzer Panel */}
      {activePanel === 'complexity' && (
        <div className="flex flex-col overflow-hidden relative" style={{ width: `${complexityWidth}px`, background: '#0A0A10', borderRight: '1px solid rgba(255,255,255,0.07)' }}>
          
          {/* Resize Handle */}
          <div
            onMouseDown={(e) => { e.preventDefault(); setIsResizingComplexity(true) }}
            className="absolute top-0 right-0 w-2 h-full cursor-ew-resize z-50 group"
            style={{ background: 'transparent', marginRight: '-4px' }}
          >
            <div className="absolute inset-y-0 right-1 w-1 transition-all duration-200" style={{ background: 'rgba(59, 130, 246,0.3)' }} />
            <div className="absolute inset-y-0 right-1 w-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200" style={{ background: '#3b82f6', boxShadow: '0 0 10px rgba(59, 130, 246,0.5)' }} />
          </div>

          {/* Header */}
          <div className="px-4 py-3 shrink-0 flex items-center justify-between" style={{ background: '#101018', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center gap-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              <div>
                <div className="text-sm font-bold text-white">Complexity Analyzer</div>
                <div className="text-[10px] text-slate-500">Time & Space analysis</div>
              </div>
            </div>
            <button
              onClick={async () => {
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
                  setComplexityData({ time_complexity: { best:'N/A', average:'N/A', worst:'N/A' }, space_complexity: { best:'N/A', average:'N/A', worst:'N/A' }, analysis:'Analysis failed.', suggestions:[], structured_suggestions:[], verdict:'unknown', verdict_explanation:'', is_optimal:false, detected_patterns:[], execution_stats:null })
                } finally { setLoadingComplexity(false) }
              }}
              disabled={loadingComplexity || !question || !editorCode}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: 'rgba(59, 130, 246,0.2)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246,0.4)' }}
            >
              {loadingComplexity
                ? <><span className="animate-spin inline-block">⏳</span> Analyzing…</>
                : <><Icon name="bolt" size={14} className="" /> Analyze</>}
            </button>
          </div>

          {/* Complexity Analysis Content */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {!question ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'rgba(59, 130, 246,0.1)' }}>
                  <Icon name="target" size={24} className="" />
                </div>
                <div className="text-sm text-slate-400">Generate a problem to start</div>
              </div>
            ) : !editorCode || editorCode === STARTER[lang] || editorCode === generateCodeTemplate(question, lang) ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'rgba(59, 130, 246,0.1)' }}>
                  <Icon name="pencil" size={24} className="" />
                </div>
                <div className="text-sm text-slate-400 px-4">Write some code, then click Analyze</div>
              </div>
            ) : !complexityData ? (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'rgba(59, 130, 246,0.1)' }}>
                  <Icon name="bolt" size={24} className="" />
                </div>
                <div className="text-sm text-slate-400 mb-1">Ready to analyze</div>
                <div className="text-[11px] text-slate-500">Click Analyze to check time & space complexity</div>
              </div>
            ) : (
              <>
                {/* ── Execution Statistics ── */}
                {complexityData.execution_stats && (
                  <div className="rounded-xl p-3" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                    <div className="flex items-center gap-1.5 mb-3">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                      </svg>
                      <span className="text-[11px] font-semibold text-slate-300">Execution Statistics</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
                        <div className="flex items-center justify-center gap-1 mb-1">
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                          <span className="text-[9px] text-slate-500">Memory</span>
                        </div>
                        <div className="text-sm font-bold text-blue-400">
                          {complexityData.execution_stats.memory_kb != null
                            ? complexityData.execution_stats.memory_kb >= 1024
                              ? `${(complexityData.execution_stats.memory_kb / 1024).toFixed(1)} MB`
                              : `${complexityData.execution_stats.memory_kb.toFixed(1)} KB`
                            : '—'}
                        </div>
                        <div className="text-[9px] text-slate-500">max 1.6 MB</div>
                      </div>
                      <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
                        <div className="flex items-center justify-center gap-1 mb-1">
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                          <span className="text-[9px] text-slate-500">CPU Time</span>
                        </div>
                        <div className="text-sm font-bold text-blue-400">
                          {complexityData.execution_stats.cpu_time_ms != null
                            ? `${Math.round(complexityData.execution_stats.cpu_time_ms)} ms`
                            : '—'}
                        </div>
                        <div className="text-[9px] text-slate-500">
                          max {complexityData.execution_stats.cpu_time_ms != null ? `${Math.round(complexityData.execution_stats.cpu_time_ms)} ms` : '—'}
                        </div>
                      </div>
                      <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
                        <div className="flex items-center justify-center gap-1 mb-1">
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                          <span className="text-[9px] text-slate-500">Wall Time</span>
                        </div>
                        <div className="text-sm font-bold text-blue-400">
                          {complexityData.execution_stats.wall_time_ms != null
                            ? `${Math.round(complexityData.execution_stats.wall_time_ms)} ms`
                            : '—'}
                        </div>
                        <div className="text-[9px] text-slate-500">
                          avg of {complexityData.execution_stats.total_tests ?? '—'} tests
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── Verdict Badge ── */}
                {complexityData.verdict && complexityData.verdict !== 'unknown' && (() => {
                  const verdictConfig = {
                    optimal:          { bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.35)', color: '#34d399', icon: 'check-circle', label: 'Optimal' },
                    acceptable:       { bg: 'rgba(251,191,36,0.10)', border: 'rgba(251,191,36,0.35)', color: '#fbbf24', icon: 'info', label: 'Acceptable' },
                    needs_improvement:{ bg: 'rgba(249,115,22,0.10)', border: 'rgba(249,115,22,0.35)', color: '#fb923c', icon: 'alert', label: 'Needs improvement' },
                    poor:             { bg: 'rgba(239,68,68,0.10)',  border: 'rgba(239,68,68,0.35)',  color: '#f87171', icon: 'x-circle', label: 'Poor' },
                  }
                  const cfg = verdictConfig[complexityData.verdict] || verdictConfig.acceptable
                  return (
                    <div className="rounded-xl p-3" style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-base">{cfg.icon}</span>
                        <span className="text-sm font-bold" style={{ color: cfg.color }}>{cfg.label}</span>
                      </div>
                      <p className="text-[11px] text-slate-300 leading-relaxed">{complexityData.verdict_explanation}</p>
                    </div>
                  )
                })()}

                {/* ── Time & Space Complexity Cards ── */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-xl p-3 text-center" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                    <div className="flex items-center justify-center gap-1 mb-2">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                      <span className="text-[10px] text-slate-400 font-medium">Time</span>
                    </div>
                    <div className="text-xl font-bold font-mono" style={{ color: '#60a5fa' }}>
                      {complexityData.time_complexity?.worst || 'N/A'}
                    </div>
                    <div className="text-[9px] text-slate-500 mt-1">worst case</div>
                  </div>
                  <div className="rounded-xl p-3 text-center" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                    <div className="flex items-center justify-center gap-1 mb-2">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                      <span className="text-[10px] text-slate-400 font-medium">Space</span>
                    </div>
                    <div className="text-xl font-bold font-mono" style={{ color: '#60a5fa' }}>
                      {complexityData.space_complexity?.worst || 'N/A'}
                    </div>
                    <div className="text-[9px] text-slate-500 mt-1">worst case</div>
                  </div>
                </div>

                {/* Best/Avg/Worst breakdown */}
                <div className="rounded-xl p-3 space-y-2" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                  <div className="grid grid-cols-3 gap-1 text-center">
                    <div>
                      <div className="text-[9px] text-slate-500 mb-0.5">Best</div>
                      <div className="text-[11px] font-mono font-bold text-emerald-400">{complexityData.time_complexity?.best}</div>
                      <div className="text-[9px] text-slate-500">time</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500 mb-0.5">Avg</div>
                      <div className="text-[11px] font-mono font-bold text-yellow-400">{complexityData.time_complexity?.average}</div>
                      <div className="text-[9px] text-slate-500">time</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500 mb-0.5">Worst</div>
                      <div className="text-[11px] font-mono font-bold text-rose-400">{complexityData.time_complexity?.worst}</div>
                      <div className="text-[9px] text-slate-500">time</div>
                    </div>
                  </div>
                  <div className="border-t border-white/5 pt-2 grid grid-cols-3 gap-1 text-center">
                    <div>
                      <div className="text-[11px] font-mono font-bold text-emerald-400">{complexityData.space_complexity?.best}</div>
                      <div className="text-[9px] text-slate-500">space</div>
                    </div>
                    <div>
                      <div className="text-[11px] font-mono font-bold text-yellow-400">{complexityData.space_complexity?.average}</div>
                      <div className="text-[9px] text-slate-500">space</div>
                    </div>
                    <div>
                      <div className="text-[11px] font-mono font-bold text-rose-400">{complexityData.space_complexity?.worst}</div>
                      <div className="text-[9px] text-slate-500">space</div>
                    </div>
                  </div>
                </div>

                {/* ── Complexity Visualization ── */}
                <div className="rounded-xl p-3" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                  <div className="flex items-center gap-1.5 mb-2">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
                    </svg>
                    <span className="text-[11px] font-semibold text-slate-300">Complexity Visualization</span>
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <ComplexityChart userComplexity={complexityData.time_complexity?.worst} />
                  </div>
                  <ChartLegend userComplexity={complexityData.time_complexity?.worst} />
                </div>

                {/* ── Complexity Analysis ── */}
                {complexityData.analysis && (
                  <div className="rounded-xl p-3" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                    <div className="flex items-center gap-1.5 mb-2">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
                      </svg>
                      <span className="text-[11px] font-semibold text-slate-300">Complexity Analysis</span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">{complexityData.analysis}</p>
                  </div>
                )}

                {/* ── Improvement Suggestions ── */}
                {complexityData.structured_suggestions && complexityData.structured_suggestions.length > 0 && (
                  <div className="rounded-xl p-3" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                    <div className="flex items-center gap-1.5 mb-3">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
                      </svg>
                      <span className="text-[11px] font-semibold text-slate-300">Improvement Suggestions</span>
                    </div>
                    <div className="space-y-2">
                      {complexityData.structured_suggestions.map((s, i) => {
                        const priorityStyle = {
                          high:   { bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.3)',   badge: 'rgba(239,68,68,0.2)',   badgeText: '#f87171',  label: 'high' },
                          medium: { bg: 'rgba(251,191,36,0.08)',  border: 'rgba(251,191,36,0.25)', badge: 'rgba(251,191,36,0.2)',  badgeText: '#fbbf24',  label: 'medium' },
                          low:    { bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.25)', badge: 'rgba(16,185,129,0.2)', badgeText: '#34d399',  label: 'low' },
                        }
                        const ps = priorityStyle[s.priority] || priorityStyle.medium
                        return (
                          <div key={i} className="rounded-lg p-2.5" style={{ background: ps.bg, border: `1px solid ${ps.border}` }}>
                            <div className="flex items-start justify-between gap-2 mb-1">
                              <span className="text-[11px] font-semibold text-white leading-tight">{s.title}</span>
                              <span className="shrink-0 px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ background: ps.badge, color: ps.badgeText }}>{ps.label}</span>
                            </div>
                            <p className="text-[10px] text-slate-400 leading-relaxed">{s.description}</p>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* ── Share Solution ── */}
                <div className="rounded-xl p-3" style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)' }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
                        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                      </svg>
                      <div>
                        <div className="text-[11px] font-semibold text-white">Copy summary</div>
                        <div className="text-[9px] text-slate-500">Copy the complexity result to share it</div>
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        const text = `Time: ${complexityData.time_complexity?.worst} | Space: ${complexityData.space_complexity?.worst}\n${complexityData.analysis || ''}`
                        navigator.clipboard?.writeText(text).catch(() => {})
                      }}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition-all active:scale-95"
                      style={{ background: 'rgba(59, 130, 246,0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246,0.3)' }}
                    >
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
                      Copy
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Leaderboard Panel */}
      {activePanel === 'leaderboard' && (
        <div className="flex flex-col overflow-hidden relative" style={{ width: `${leaderboardWidth}px`, background: '#0A0A10', borderRight: '1px solid rgba(255,255,255,0.07)' }}>
          
          {/* Resize Handle */}
          <div
            onMouseDown={(e) => {
              e.preventDefault()
              setIsResizingLeaderboard(true)
            }}
            className="absolute top-0 right-0 w-2 h-full cursor-ew-resize z-50 group"
            style={{ 
              background: 'transparent',
              marginRight: '-4px',
            }}
          >
            <div 
              className="absolute inset-y-0 right-1 w-1 transition-all duration-200"
              style={{
                background: 'rgba(59, 130, 246, 0.3)',
              }}
            />
            <div 
              className="absolute inset-y-0 right-1 w-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
              style={{
                background: '#3b82f6',
                boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)',
              }}
            />
          </div>
          
          {/* Header */}
          <div className="px-4 py-3 shrink-0" style={{ background: '#101018', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center gap-2">
              <Icon name="trophy" size={20} className="" />
              <div>
                <div className="text-sm font-bold text-white">Leaderboard</div>
                <div className="text-[10px] text-slate-500">Match rankings</div>
              </div>
            </div>
          </div>

          {/* Leaderboard Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {leaderboard.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'rgba(251,191,36,0.1)' }}>
                  <Icon name="bars" size={30} className="" />
                </div>
                <div className="text-sm text-slate-400">No scores yet</div>
                <div className="text-xs text-slate-500 mt-1">Start solving to see rankings</div>
              </div>
            ) : (
              <div className="space-y-2">
                {leaderboard.map((entry, i) => {
                  const isMe = (entry.player_id ?? entry.id) === playerId
                  const medals = ['1', '2', '3']
                  return (
                    <div key={entry.player_id ?? entry.id ?? i}
                      className="rounded-xl p-3 transition-all duration-300 "
                      style={{
                        background: isMe ? 'rgba(59, 130, 246,0.15)' : 'rgba(255,255,255,0.03)',
                        border: isMe ? '1px solid rgba(59, 130, 246,0.3)' : '1px solid rgba(255,255,255,0.05)',
                        boxShadow: isMe ? '0 0 20px rgba(59, 130, 246,0.2)' : 'none',
                      }}>
                      <div className="flex items-center gap-3">
                        {/* Rank */}
                        <div className="text-xl shrink-0" style={{ width: '24px' }}>
                          {medals[i] ?? <span className="text-slate-500 text-sm font-mono">{i + 1}</span>}
                        </div>
                        
                        {/* Avatar */}
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                          style={{ background: isMe ? 'linear-gradient(135deg,#3b82f6,#06b6d4)' : 'rgba(255,255,255,0.1)' }}>
                          {entry.username?.[0]?.toUpperCase()}
                        </div>
                        
                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-sm truncate" style={{ color: isMe ? '#a5b4fc' : '#e2e8f0' }}>
                            {entry.username}
                            {isMe && <span className="text-xs text-blue-400 ml-1">(you)</span>}
                          </div>
                          <div className="text-[10px] text-slate-500">
                            {entry.questions_solved ?? 0} solved
                          </div>
                        </div>
                        
                        {/* Score */}
                        <div className="text-right shrink-0">
                          <div className="font-bold text-base" style={{ color: isMe ? '#a5b4fc' : '#f1f5f9' }}>
                            {entry.score ?? 0}
                          </div>
                          <div className="text-[9px] text-slate-500">points</div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Footer Stats */}
          {leaderboard.length > 0 && (
            <div className="px-4 py-3 shrink-0" style={{ background: '#101018', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(59, 130, 246,0.1)', border: '1px solid rgba(59, 130, 246,0.2)' }}>
                  <div className="text-xs text-blue-300 font-semibold">{leaderboard.length}</div>
                  <div className="text-[9px] text-slate-500">Players</div>
                </div>
                <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)' }}>
                  <div className="text-xs text-emerald-300 font-semibold">
                    {leaderboard.find(e => (e.player_id ?? e.id) === playerId)?.questions_solved ?? 0}
                  </div>
                  <div className="text-[9px] text-slate-500">Your Solved</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* LEFT: Problem Panel */}
      {activePanel === 'problem' && (
        <div className="flex flex-col overflow-hidden relative" style={{ width: `${problemWidth}px`, background: '#0A0A10', borderRight: '1px solid rgba(255,255,255,0.07)' }}>
          
          {/* Resize Handle */}
          <div
            onMouseDown={(e) => {
              e.preventDefault()
              setIsResizingProblem(true)
            }}
            className="absolute top-0 right-0 w-2 h-full cursor-ew-resize z-50 group"
            style={{ background: 'transparent', marginRight: '-4px' }}
          >
            <div className="absolute inset-y-0 right-1 w-1 transition-all duration-200" style={{ background: 'rgba(59, 130, 246, 0.3)' }} />
            <div className="absolute inset-y-0 right-1 w-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200" style={{ background: '#3b82f6', boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)' }} />
          </div>
          
          {/* Header */}
          <div className="px-5 py-4 shrink-0 relative" style={{ background: '#101018', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white text-xs transition-all duration-300 " 
                  style={{ background: 'linear-gradient(135deg,#3b82f6,#06b6d4)' }}>
                  C
                </div>
                <span className="font-semibold text-sm bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">CompileX</span>
              </div>
              <div className="flex items-center gap-2">
                {totalRounds > 1 && (
                  <span className="text-xs px-2 py-1 rounded-md font-medium transition-all duration-300 " style={{ background: 'rgba(59, 130, 246,0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246,0.3)' }}>
                    R{currentRound}/{totalRounds}
                  </span>
                )}
                <span className="text-xs px-2 py-1 rounded-md font-medium transition-all duration-300 " style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' }}>
                  Q{totalQuestionsAnswered + 1}/{questionsPerRound * totalRounds}
                </span>
                <Timer startedAt={questionStartedAt || startedAt} timeLimit={timeLimit} onExpire={handleTimeUp} />
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Lobby:</span>
              <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(255,255,255,0.05)', color: '#94a3b8' }}>{code}</span>
            </div>
          </div>

          {/* Question content */}
          <div className="flex-1 overflow-y-auto custom-scrollbar" style={{ padding: '24px' }}>
            {!question ? (
              <div className="flex flex-col items-center justify-center h-full text-center ">
                <div className="relative mb-6">
                  <div className="absolute -inset-4 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-full blur-2xl-slow" />
                  <div className="relative w-20 h-20 rounded-2xl flex items-center justify-center transition-all duration-300 " style={{ background: 'rgba(59, 130, 246,0.1)' }}>
                    <Icon name={lobby?.created_by && user?.id && lobby.created_by === user.id ? 'target' : 'clock'} size={36} className="text-blue-400" />
                  </div>
                </div>
                <h3 className="text-xl font-bold text-white mb-2 ">
                  {lobby?.created_by && user?.id && lobby.created_by === user.id ? 'Ready to Code?' : 'Waiting for Host…'}
                </h3>
                <p className="text-slate-400 text-sm mb-8 max-w-xs " style={{ animationDelay: '0.1s' }}>
                  {lobby?.created_by && user?.id && lobby.created_by === user.id
                    ? 'Generate a problem to begin the challenge'
                    : 'The host is generating the first question. Hang tight!'}
                </p>
                
                {lobby?.created_by && user?.id && lobby.created_by === user.id && (
                  <div className="w-full max-w-sm relative">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-2xl blur-xl" />
                    <div className="relative p-5 rounded-xl transition-all duration-300 " style={{ background: '#101018', border: '1px solid rgba(255,255,255,0.07)', animationDelay: '0.2s' }}>
                      <div className="mb-4">
                        <label className="block text-xs text-slate-400 mb-2 text-center">Difficulty</label>
                        <div className="flex gap-2">
                          {['easy', 'medium', 'hard'].map(d => (
                            <button key={d}
                              onClick={() => setDifficulty(d)}
                              className="flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all duration-300 capitalize "
                              style={{
                                background: difficulty === d ? DIFFICULTY_COLORS[d].bg : 'rgba(255,255,255,0.03)',
                                color: difficulty === d ? DIFFICULTY_COLORS[d].text : '#64748b',
                                border: `1px solid ${difficulty === d ? DIFFICULTY_COLORS[d].border : 'rgba(255,255,255,0.06)'}`,
                              }}>
                              {d}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="mb-4">
                        <label className="block text-xs text-slate-400 mb-2 text-center">Topic (optional)</label>
                        <input
                          type="text"
                          value={topic}
                          onChange={e => setTopic(e.target.value)}
                          placeholder="e.g., arrays, strings, dp"
                          className="w-full px-3 py-2 rounded-lg text-sm text-white bg-[#0A0A10] border border-white/[0.07] focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 placeholder-slate-600 transition-all duration-300"
                        />
                      </div>
                      <button
                        onClick={generateQuestion}
                        disabled={generating}
                        className="relative w-full py-3 rounded-lg text-sm font-semibold text-white transition-all duration-300 flex items-center justify-center gap-2 overflow-hidden group"
                        style={{ opacity: generating ? 0.5 : 1 }}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600" />
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-500" />
                        <span className="relative z-10 flex items-center gap-2">
                          {generating ? (
                            <>
                              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
                              Generating...
                            </>
                          ) : (
                            <>
                              Generate problem
                            </>
                          )}
                        </span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="">
                <div className="mb-6">
                  <div className="flex items-start justify-between mb-3">
                    <h1 className="text-2xl font-bold text-white leading-tight pr-4 ">{question.title}</h1>
                    <span className="shrink-0 px-3 py-1 rounded-full text-xs font-semibold capitalize transition-all "
                      style={{
                        background: DIFFICULTY_COLORS[question.difficulty]?.bg || 'rgba(255,255,255,0.1)',
                        color: DIFFICULTY_COLORS[question.difficulty]?.text || '#94a3b8',
                        border: `1px solid ${DIFFICULTY_COLORS[question.difficulty]?.border || 'transparent'}`,
                      }}>
                      {question.difficulty}
                    </span>
                  </div>
                  {question.topic && (
                    <span className="inline-block px-2 py-1 rounded text-xs font-medium transition-all " style={{ background: 'rgba(59, 130, 246,0.15)', color: '#60a5fa' }}>
                      #{question.topic}
                    </span>
                  )}
                </div>

                <div className="" style={{ fontSize: '14px', lineHeight: '1.8', animationDelay: '0.1s' }}>
                  {renderMarkdown(question.description)}
                </div>

                {/* Diagram for tree/graph questions */}
                {question.diagram && (
                  <div className="mt-6 " style={{ animationDelay: '0.2s' }}>
                    <div className="text-xs font-semibold text-blue-300 mb-3 flex items-center gap-2">
                      <span style={{ 
                        width: '3px', 
                        height: '14px', 
                        background: '#60a5fa',
                        borderRadius: '2px',
                      }} />
                      Visual Diagram
                    </div>
                    <div className="rounded-xl overflow-hidden border" style={{ 
                      background: 'rgba(255,255,255,0.02)', 
                      border: '1px solid rgba(59, 130, 246,0.2)',
                      boxShadow: '0 4px 20px rgba(59, 130, 246,0.1)'
                    }}>
                      <img 
                        src={question.diagram} 
                        alt="Problem diagram" 
                        className="w-full h-auto"
                        style={{ maxHeight: '400px', objectFit: 'contain' }}
                      />
                    </div>
                  </div>
                )}

                {lobby?.created_by && user?.id && lobby.created_by === user.id && (
                  <div className="mt-6 pt-5" style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}>
                    <div className="flex gap-2 mb-2 items-center">
                      <select
                        value={difficulty}
                        onChange={e => setDifficulty(e.target.value)}
                        className="px-3 rounded-lg text-xs font-medium border focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all duration-300 cursor-pointer h-9 shrink-0"
                        style={{
                          background: '#101018',
                          width: '90px',
                          border: difficulty === 'easy' ? '1px solid rgba(52,211,153,0.5)' : difficulty === 'hard' ? '1px solid rgba(248,113,113,0.5)' : '1px solid rgba(251,191,36,0.5)',
                          color: difficulty === 'easy' ? '#34d399' : difficulty === 'hard' ? '#f87171' : '#fbbf24',
                        }}
                      >
                        <option value="easy" style={{ background: '#101018', color: '#34d399' }}>Easy</option>
                        <option value="medium" style={{ background: '#101018', color: '#fbbf24' }}>Medium</option>
                        <option value="hard" style={{ background: '#101018', color: '#f87171' }}>Hard</option>
                      </select>
                      <input
                        type="text"
                        value={topic}
                        onChange={e => setTopic(e.target.value)}
                        placeholder="New topic..."
                        className="flex-1 px-3 rounded-lg text-sm text-white bg-[#101018] border border-white/[0.07] focus:outline-none focus:border-blue-500/50 focus:ring-2 focus:ring-blue-500/20 placeholder-slate-600 h-9 transition-all duration-300"
                        onKeyDown={e => { if (e.key === 'Enter' && !generating) generateQuestion() }}
                      />
                      <button
                        onClick={generateQuestion}
                        disabled={generating}
                        className="relative px-4 rounded-lg text-sm font-medium text-white transition-all duration-300 shrink-0 h-9 overflow-hidden group"
                        style={{ opacity: generating ? 0.5 : 1 }}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-cyan-600" />
                        <span className="relative z-10">{generating ? '…' : 'Swap'}</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="px-4 py-3 shrink-0 flex items-center justify-between relative" style={{ background: '#101018', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
            {lobby?.created_by && user?.id && lobby.created_by === user.id && (
              <button onClick={endGame} className="text-xs font-medium text-rose-400 hover:text-rose-300 transition-colors duration-300">
                End Game
              </button>
            )}
            <div className="flex items-center gap-2 ml-auto">
              <div className="text-right">
                <div className="text-xs font-semibold text-white">{user?.username}</div>
                <div className="text-[10px] text-slate-500">Player</div>
              </div>
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold" 
                style={{ background: 'linear-gradient(135deg,#3b82f6,#06b6d4)' }}>
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* RIGHT: Editor + Panel */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Editor Header */}
        <div className="h-11 flex items-center px-4 gap-4 shrink-0 relative" style={{ background: '#101018', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
          <div className="flex items-center gap-1">
            {LANGUAGES.map(l => (
              <button
                key={l.value}
                onClick={() => changeLang(l.value)}
                className="px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-300 "
                style={{
                  background: lang === l.value ? 'rgba(59, 130, 246,0.2)' : 'transparent',
                  color: lang === l.value ? '#60a5fa' : '#64748b',
                  border: lang === l.value ? '1px solid rgba(59, 130, 246,0.3)' : '1px solid transparent',
                }}
              >
                {l.label}
              </button>
            ))}
          </div>

          <div className="flex-1" />

          <div className="flex items-center gap-2">
            <button
              onClick={runCode}
              disabled={runningCustom || !question}
              className="px-4 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 flex items-center gap-1.5 "
              style={{
                background: useCustomInput ? 'rgba(59, 130, 246,0.2)' : 'rgba(255,255,255,0.06)',
                color: useCustomInput ? '#60a5fa' : '#94a3b8',
                border: useCustomInput ? '1px solid rgba(59, 130, 246,0.3)' : '1px solid rgba(255,255,255,0.1)',
                opacity: (!question || runningCustom) ? 0.5 : 1,
              }}
              title={useCustomInput ? 'Run with custom input' : 'Run with test cases'}
            >
              <svg width="10" height="10" viewBox="0 0 10 12" fill="currentColor"><path d="M0 0L10 6L0 12z"/></svg>
              {runningCustom ? 'Running...' : useCustomInput ? 'Run (Custom)' : 'Run (Test)'}
            </button>
            <button
              onClick={submitCode}
              disabled={submitting || !question}
              className="relative px-5 py-1.5 rounded-lg text-xs font-semibold text-white transition-all duration-300 flex items-center gap-1.5 overflow-hidden group"
              style={{
                opacity: (!question || submitting) ? 0.5 : 1,
              }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-emerald-600 to-green-600" />
              <div className="absolute inset-0 bg-gradient-to-r from-emerald-600 to-green-600 opacity-0 group-hover:opacity-100 blur-xl transition-opacity duration-500" />
              <span className="relative z-10 flex items-center gap-1.5">
                {submitting && <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>}
                {submitting ? 'Submitting...' : 'Submit'}
              </span>
            </button>
          </div>
          
          {/* Logic Analysis Display */}
          {result && result.logic_analysis && (
            <div className="ml-4 px-4 py-2 rounded-lg flex items-center gap-3 " 
              style={{ 
                background: result.logic_analysis.logic_correctness >= 70 
                  ? 'rgba(16,185,129,0.15)' 
                  : result.logic_analysis.logic_correctness >= 40 
                  ? 'rgba(251,191,36,0.15)' 
                  : 'rgba(239,68,68,0.15)',
                border: `1px solid ${result.logic_analysis.logic_correctness >= 70 
                  ? 'rgba(16,185,129,0.3)' 
                  : result.logic_analysis.logic_correctness >= 40 
                  ? 'rgba(251,191,36,0.3)' 
                  : 'rgba(239,68,68,0.3)'}`,
              }}
            >
              <div className="flex items-center gap-2">
                <Icon name="message" size={18} className="" />
                <div>
                  <div className="text-xs font-semibold" 
                    style={{ 
                      color: result.logic_analysis.logic_correctness >= 70 
                        ? '#34d399' 
                        : result.logic_analysis.logic_correctness >= 40 
                        ? '#fbbf24' 
                        : '#f87171' 
                    }}
                  >
                    Logic: {result.logic_analysis.logic_correctness}% Correct
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Score: {result.score} pts
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Monaco Editor */}
        <div style={{ flex: '1 1 0', minHeight: 0, overflow: 'hidden', background: '#1e1e1e' }}>
          <Editor
            height="100%"
            language={currentLang.monaco}
            value={editorCode}
            onChange={v => setEditorCode(v || '')}
            theme="vs-dark"
            beforeMount={(monaco) => {
              // Define VS Code-like dark theme
              monaco.editor.defineTheme('vsCodeDark', {
                base: 'vs-dark',
                inherit: true,
                rules: [
                  { token: 'comment', foreground: '6A9955' },
                  { token: 'keyword', foreground: 'C586C0' },
                  { token: 'string', foreground: 'CE9178' },
                  { token: 'number', foreground: 'B5CEA8' },
                  { token: 'function', foreground: 'DCDCAA' },
                  { token: 'variable', foreground: '9CDCFE' },
                  { token: 'type', foreground: '4EC9B0' },
                  { token: 'class', foreground: '4EC9B0' },
                  { token: 'operator', foreground: 'D4D4D4' },
                  { token: 'delimiter', foreground: 'D4D4D4' },
                  { token: 'identifier', foreground: '9CDCFE' },
                ],
                colors: {
                  'editor.background': '#1e1e1e',
                  'editor.foreground': '#D4D4D4',
                  'editor.lineHighlightBackground': '#2a2d2e',
                  'editor.selectionBackground': '#264f78',
                  'editorCursor.foreground': '#AEAFAD',
                  'editorLineNumber.foreground': '#858585',
                  'editorLineNumber.activeForeground': '#c6c6c6',
                  'editor.selectionHighlightBackground': '#3a3d41',
                  'editorIndentGuide.background': '#404040',
                  'editorIndentGuide.activeBackground': '#707070',
                  'editorWhitespace.foreground': '#404040',
                }
              })
            }}
            onMount={(editor, monaco) => {
              monaco.editor.setTheme('vsCodeDark')
              attachProtectedRegion(editor, monaco)
            }}
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              padding: { top: 16, bottom: 16 },
              fontFamily: "'Consolas','Courier New',monospace",
              fontLigatures: false,
              lineHeight: 19,
              renderLineHighlight: 'all',
              cursorBlinking: 'blink',
              cursorSmoothCaretAnimation: 'off',
              smoothScrolling: true,
              automaticLayout: true,
              tabSize: 4,
              wordWrap: 'on',
              bracketPairColorization: { enabled: true },
              guides: {
                bracketPairs: true,
                indentation: true,
              },
              suggest: {
                showKeywords: true,
                showSnippets: true,
              },
            }}
          />
        </div>

        {/* Bottom Panel */}
        <div className="shrink-0 flex flex-col relative transition-all duration-300" style={{ height: bottomPanelMinimized ? '40px' : '300px', background: '#101018', borderTop: '2px solid rgba(59, 130, 246,0.3)' }}>

          {/* Tabs Header */}
          <div className="flex items-center justify-between px-2 shrink-0 h-10" style={{ borderBottom: bottomPanelMinimized ? 'none' : '1px solid rgba(255,255,255,0.07)' }}>
            <div className="flex items-center gap-1">
              <button
                onClick={() => {
                  if (useCustomInput && rightPanelTab !== 'tests') {
                    setShowCustomWarning(true)
                  } else {
                    setRightPanelTab('tests')
                  }
                }}
                className="px-3 py-2 text-xs font-semibold transition-all duration-300 flex items-center gap-2 relative"
                style={{ color: rightPanelTab === 'tests' ? '#60a5fa' : '#64748b' }}
              >
                {rightPanelTab === 'tests' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ background: '#3b82f6' }} />
                )}
                {ACTIVITY_ICONS.test}
                Test Cases
                {testCaseDetails.length > 0 && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" 
                    style={{ background: passedCount === totalTests ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)', color: passedCount === totalTests ? '#34d399' : '#fbbf24' }}>
                    {passedCount}/{totalTests}
                  </span>
                )}
              </button>
              <button
                onClick={() => setRightPanelTab('custom')}
                className="px-3 py-2 text-xs font-semibold transition-all duration-300 flex items-center gap-2 relative"
                style={{ color: rightPanelTab === 'custom' ? '#60a5fa' : '#64748b' }}
              >
                {rightPanelTab === 'custom' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ background: '#3b82f6' }} />
                )}
                {ACTIVITY_ICONS.custom}
                Custom
                {useCustomInput && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" style={{ background: 'rgba(59, 130, 246,0.2)', color: '#60a5fa' }}>
                    ON
                  </span>
                )}
              </button>
              <button
                onClick={() => setRightPanelTab('console')}
                className="px-3 py-2 text-xs font-semibold transition-all duration-300 flex items-center gap-2 relative"
                style={{ color: rightPanelTab === 'console' ? '#60a5fa' : '#64748b' }}
              >
                {rightPanelTab === 'console' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ background: '#3b82f6' }} />
                )}
                {ACTIVITY_ICONS.console}
                Console
              </button>
              {result && result.logic_analysis && (
                <button
                  onClick={() => setRightPanelTab('logic')}
                  className="px-3 py-2 text-xs font-semibold transition-all duration-300 flex items-center gap-2 relative"
                  style={{ color: rightPanelTab === 'logic' ? '#60a5fa' : '#64748b' }}
                >
                  {rightPanelTab === 'logic' && (
                    <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ background: '#3b82f6' }} />
                  )}
                  <Icon name="message" size={14} className="" />
                  Logic Analysis
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold" 
                    style={{ 
                      background: result.logic_analysis.logic_correctness >= 70 
                        ? 'rgba(16,185,129,0.2)' 
                        : result.logic_analysis.logic_correctness >= 40 
                        ? 'rgba(251,191,36,0.2)' 
                        : 'rgba(239,68,68,0.2)',
                      color: result.logic_analysis.logic_correctness >= 70 
                        ? '#34d399' 
                        : result.logic_analysis.logic_correctness >= 40 
                        ? '#fbbf24' 
                      : '#f87171'
                  }}
                >
                  {result.logic_analysis.logic_correctness}%
                </span>
              </button>
            )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setEditorCode(question ? generateCodeTemplate(question, lang) : STARTER[lang])}
                className="px-3 py-1.5 rounded text-slate-500 hover:text-white transition-colors duration-300 text-xs"
                title="Reset code"
                >
                Reset
              </button>
              <button
                onClick={() => setBottomPanelMinimized(!bottomPanelMinimized)}
                className="px-3 py-1.5 rounded text-slate-500 hover:text-blue-400 transition-all duration-300 text-xs flex items-center gap-1 "
                title={bottomPanelMinimized ? "Maximize panel" : "Minimize panel"}
              >
                <svg 
                  width="16" 
                  height="16" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2"
                  className="transition-transform duration-300"
                  style={{ transform: bottomPanelMinimized ? 'rotate(180deg)' : 'rotate(0deg)' }}
                >
                  <polyline points="18 15 12 9 6 15"/>
                </svg>
              </button>
            </div>
          </div>

          {!bottomPanelMinimized && (
            <div className="flex-1 overflow-hidden flex">

            {/* Test Cases */}
            {rightPanelTab === 'tests' && (
              <div className="flex w-full">
                <div className="w-36 shrink-0 overflow-y-auto p-3 flex flex-col gap-1" style={{ borderRight: '1px solid rgba(255,255,255,0.06)' }}>
                  {testCaseDetails.length === 0 ? (
                    <div className="text-xs text-slate-500 italic text-center py-8">No test cases</div>
                  ) : (
                    <>
                      {testCaseDetails.map((tc, i) => {
                        const icon = tc.passed === null ? '⚠' : tc.passed ? '✓' : '✗'
                        const c = tc.passed === null
                          ? { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', text: '#fbbf24' }
                          : tc.passed
                          ? { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', text: '#34d399' }
                          : { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', text: '#f87171' }
                        return (
                          <button
                            key={i}
                            onClick={() => { setSelectedTestCase(i); setTestCaseHint(null) }}
                            className="w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 focus:outline-none"
                            style={{
                              background: selectedTestCase === i ? 'rgba(99,102,241,0.15)' : c.bg,
                              color: selectedTestCase === i ? '#e2e8f0' : c.text,
                              border: `1px solid ${selectedTestCase === i ? 'rgba(99,102,241,0.3)' : c.border}`,
                              outline: 'none',
                            }}
                          >
                            <span className="font-bold">{icon}</span>
                            <span>Case {i + 1}</span>
                          </button>
                        )
                      })}
                    </>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                  {testCaseDetails.length > 0 && testCaseDetails[selectedTestCase] ? (
                    <div className="flex flex-col gap-4">
                      {testCaseDetails[selectedTestCase].hidden ? (
                        <div className="flex flex-col items-center justify-center py-10 text-slate-500">
                          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mb-3 opacity-50">
                            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
                            <circle cx="12" cy="12" r="3"/>
                            <line x1="3" y1="3" x2="21" y2="21"/>
                          </svg>
                          <div className="font-semibold text-sm mb-1">Hidden Test Case</div>
                          <div className="text-xs text-center opacity-70 mb-4 max-w-[250px]">
                            The input and expected output for this test case are hidden. Solve the problem for all edge cases to pass!
                          </div>
                          
                          {testCaseDetails[selectedTestCase].passed !== null && (
                            <div className="w-full max-w-sm rounded-lg p-4" style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.05)' }}>
                              <div className="text-[11px] font-semibold mb-2 text-center"
                                style={{ color: testCaseDetails[selectedTestCase].passed ? '#34d399' : '#f87171' }}>
                                {testCaseDetails[selectedTestCase].passed ? '✓ Test Passed' : '✗ Test Failed'}
                              </div>
                              {!testCaseDetails[selectedTestCase].passed && (
                                <div className="mt-3 flex justify-center">
                                  <button onClick={getDebugHint} disabled={loadingHint}
                                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                                    style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.3)' }}>
                                    {loadingHint ? '⏳ Analyzing...' : 'Get Debug Hint'}
                                  </button>
                                </div>
                              )}
                              {testCaseHint && !testCaseDetails[selectedTestCase].passed && (
                                <div className="mt-3 rounded-xl p-4 text-xs space-y-2"
                                  style={{ background: 'rgba(251,191,36,0.06)', border: '1px solid rgba(251,191,36,0.2)' }}>
                                  <div className="flex items-center gap-2 font-bold" style={{ color: '#fbbf24' }}>
                                    AI mentor
                                    <span className="font-normal text-slate-400">- {testCaseHint.status}</span>
                                  </div>
                                  {testCaseHint.line && (
                                    <div style={{ color: '#f87171' }}>Line: {testCaseHint.line}</div>
                                  )}
                                  <div style={{ color: '#e2e8f0' }}>{testCaseHint.message}</div>
                                  <div className="pt-1 font-semibold" style={{ color: '#a5b4fc' }}>
                                    Hint: {testCaseHint.hint}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <>
                          <div>
                            <div className="text-[11px] font-semibold text-slate-400 mb-2">Input</div>
                        <div className="rounded-lg p-3 font-mono text-sm whitespace-pre-wrap" 
                          style={{ background: 'rgba(30,30,50,0.8)', color: '#e2e8f0', border: '1px solid rgba(255,255,255,0.08)' }}>
                          {testCaseDetails[selectedTestCase].input || '(empty)'}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] font-semibold text-slate-400 mb-2">Expected Output</div>
                        <div className="rounded-lg p-3 font-mono text-sm whitespace-pre-wrap" 
                          style={{ background: 'rgba(30,30,50,0.8)', color: '#34d399', border: '1px solid rgba(16,185,129,0.2)' }}>
                          {testCaseDetails[selectedTestCase].expected_output || '(empty)'}
                        </div>
                      </div>
                      {testCaseDetails[selectedTestCase].passed !== null && (
                        <div>
                          <div className="text-[11px] font-semibold mb-2"
                            style={{ color: testCaseDetails[selectedTestCase].error ? '#f87171' : testCaseDetails[selectedTestCase].passed ? '#34d399' : '#f87171' }}>
                            Your Output
                          </div>
                          <div className="rounded-lg p-3 font-mono text-sm whitespace-pre-wrap" 
                            style={{
                              background: testCaseDetails[selectedTestCase].error
                                ? 'rgba(239,68,68,0.1)'
                                : testCaseDetails[selectedTestCase].passed
                                ? 'rgba(16,185,129,0.1)'
                                : 'rgba(239,68,68,0.1)',
                              color: testCaseDetails[selectedTestCase].error
                                ? '#f87171'
                                : testCaseDetails[selectedTestCase].passed
                                ? '#34d399'
                                : '#f87171',
                              border: `1px solid ${testCaseDetails[selectedTestCase].error || !testCaseDetails[selectedTestCase].passed ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`,
                            }}>
                            {testCaseDetails[selectedTestCase].error || testCaseDetails[selectedTestCase].actual_output || '(no output)'}
                          </div>
                        </div>
                      )}
                      {testCaseDetails[selectedTestCase].passed !== null ? (
                        <div>
                          <div className="text-[11px] font-semibold mb-2"
                            style={{ color: testCaseDetails[selectedTestCase].passed ? '#34d399' : '#f87171' }}>
                            {testCaseDetails[selectedTestCase].passed ? '✓ Test Passed' : '✗ Test Failed'}
                          </div>
                          {/* Debug Hint Button — only show on failed */}
                          {!testCaseDetails[selectedTestCase].passed && (
                            <div className="mt-3">
                              <button onClick={getDebugHint} disabled={loadingHint}
                                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                                style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.3)' }}>
                                {loadingHint ? 'Analyzing…' : 'Get debug hint'}
                              </button>
                              {testCaseHint && (
                                <div className="mt-3 rounded-xl p-4 text-xs space-y-2"
                                  style={{ background: 'rgba(251,191,36,0.06)', border: '1px solid rgba(251,191,36,0.2)' }}>
                                  <div className="flex items-center gap-2 font-bold" style={{ color: '#fbbf24' }}>
                                    AI mentor
                                    <span className="font-normal text-slate-400">— {testCaseHint.status}</span>
                                  </div>
                                  {testCaseHint.line && (
                                    <div style={{ color: '#f87171' }}>Line: {testCaseHint.line}</div>
                                  )}
                                  <div style={{ color: '#e2e8f0' }}>{testCaseHint.message}</div>
                                  <div className="pt-1 font-semibold" style={{ color: '#a5b4fc' }}>
                                    Hint: {testCaseHint.hint}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div>
                          <div className="text-[11px] text-slate-500 italic">Run or submit your code to see results</div>
                        </div>
                      )}
                        </>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                      <div className="text-slate-500 text-sm">Generate a question to see test cases</div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Custom Input */}
            {rightPanelTab === 'custom' && (
              <div className="flex-1 overflow-y-auto p-4">
                <div className="flex items-center justify-between mb-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useCustomInput}
                      onChange={(e) => {
                        setUseCustomInput(e.target.checked)
                        if (e.target.checked) {
                          setRightPanelTab('custom')
                        }
                      }}
                      className="w-4 h-4 rounded"
                      style={{ accentColor: '#6366f1' }}
                    />
                    <span className="text-xs font-medium text-slate-300">Use custom input for Run</span>
                  </label>
                </div>
                <div className="mb-4">
                  <label className="text-[11px] font-semibold mb-2 block"
                    style={{ color: useCustomInput ? '#94a3b8' : '#64748b' }}>
                    Custom Input
                  </label>
                  <textarea
                    value={customInput}
                    onChange={e => setCustomInput(e.target.value)}
                    placeholder={useCustomInput ? "Enter your custom test input here..." : "Check 'Use custom input' to enable editing..."}
                    disabled={!useCustomInput}
                    className="w-full h-28 rounded-lg p-3 text-sm font-mono resize-none transition"
                    style={{ 
                      background: useCustomInput ? 'rgba(30,30,50,0.8)' : 'rgba(20,20,32,0.8)',
                      color: useCustomInput ? '#e2e8f0' : '#64748b',
                      border: useCustomInput ? '1px solid rgba(99,102,241,0.3)' : '1px solid rgba(255,255,255,0.06)',
                      cursor: useCustomInput ? 'text' : 'not-allowed',
                      outline: 'none',
                    }}
                  />
                </div>
                <button
                  onClick={runCode}
                  disabled={runningCustom || !question || !useCustomInput}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-white transition-all flex items-center gap-2"
                  style={{
                    background: runningCustom ? '#4b5563' : 'linear-gradient(135deg,#6366f1,#3b82f6)',
                    opacity: (!question || runningCustom || !useCustomInput) ? 0.5 : 1,
                    cursor: (!useCustomInput || !question) ? 'not-allowed' : 'pointer',
                  }}
                >
                  {runningCustom ? (
                    <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
                  ) : (
                    <svg width="12" height="12" viewBox="0 0 10 12" fill="white"><path d="M0 0L10 6L0 12z"/></svg>
                  )}
                  {runningCustom ? 'Running...' : 'Run Code'}
                </button>
              </div>
            )}

            {/* Console */}
            {rightPanelTab === 'console' && (
              <div className="flex-1 overflow-y-auto p-4">
                {consoleOutput.length > 0 ? (
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold text-slate-400">Output</span>
                        {consoleOutput[0]?.runType && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium"
                            style={{
                              background: consoleOutput[0].runType === 'custom' ? 'rgba(59, 130, 246,0.2)' : 'rgba(34,211,238,0.2)',
                              color: consoleOutput[0].runType === 'custom' ? '#60a5fa' : '#22d3ee',
                            }}>
                            {consoleOutput[0].runType === 'custom' ? 'Custom Input' : 'Test Cases'}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500">{consoleOutput.length} result(s)</span>
                    </div>
                    {consoleOutput.map((res, i) => (
                      <div key={i} className="rounded-lg overflow-hidden" 
                        style={{
                          border: `1px solid ${res.error ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`,
                        }}>
                        <div className="px-3 py-2 flex items-center gap-2" 
                          style={{ background: res.error ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)' }}>
                          <span className="text-xs font-semibold" style={{ color: res.error ? '#f87171' : '#34d399' }}>
                            {res.error ? 'Error' : `Test ${i + 1}`}
                          </span>
                        </div>
                        {res.input && (
                          <div className="px-3 py-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                            <div className="text-[10px] text-slate-500 mb-1">Input</div>
                            <div className="text-xs font-mono text-slate-300 whitespace-pre-wrap">{res.input}</div>
                          </div>
                        )}
                        <div className="px-3 py-3">
                          <div className="text-[10px] text-slate-500 mb-1">Output</div>
                          <div className="text-sm font-mono whitespace-pre-wrap" style={{ color: res.error ? '#f87171' : '#34d399' }}>
                            {res.error || res.output || '(no output)'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3" style={{ background: 'rgba(99,102,241,0.1)' }}>
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
                        <polyline points="4 17 10 11 4 5"/>
                        <line x1="12" y1="19" x2="20" y2="19"/>
                      </svg>
                    </div>
                    <div className="text-slate-400 text-sm mb-1">Console Output</div>
                    <div className="text-slate-500 text-xs">Run your code with custom input to see results here</div>
                  </div>
                )}
              </div>
            )}

            {/* Logic Analysis */}
            {rightPanelTab === 'logic' && result && result.logic_analysis && (
              <div className="flex-1 overflow-y-auto p-4">
                <div className="space-y-4">
                  {/* Overall Score */}
                  <div className="rounded-xl p-4" 
                    style={{ 
                      background: result.logic_analysis.logic_correctness >= 70 
                        ? 'rgba(16,185,129,0.1)' 
                        : result.logic_analysis.logic_correctness >= 40 
                        ? 'rgba(251,191,36,0.1)' 
                        : 'rgba(239,68,68,0.1)',
                      border: `1px solid ${result.logic_analysis.logic_correctness >= 70 
                        ? 'rgba(16,185,129,0.3)' 
                        : result.logic_analysis.logic_correctness >= 40 
                        ? 'rgba(251,191,36,0.3)' 
                        : 'rgba(239,68,68,0.3)'}`,
                    }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Icon name="message" size={24} className="" />
                        <div>
                          <div className="text-sm font-bold text-white">AI Logic Analysis</div>
                          <div className="text-xs text-slate-400">Partial credit awarded</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold" 
                          style={{ 
                            color: result.logic_analysis.logic_correctness >= 70 
                              ? '#34d399' 
                              : result.logic_analysis.logic_correctness >= 40 
                              ? '#fbbf24' 
                              : '#f87171' 
                          }}
                        >
                          {result.logic_analysis.logic_correctness}%
                        </div>
                        <div className="text-xs text-slate-400">Logic Correct</div>
                      </div>
                    </div>
                    <div className="text-xs text-slate-300 leading-relaxed">
                      {result.logic_analysis.analysis}
                    </div>
                  </div>

                  {/* Score Breakdown */}
                  <div className="rounded-xl p-4" style={{ background: 'rgba(59, 130, 246,0.1)', border: '1px solid rgba(59, 130, 246,0.3)' }}>
                    <div className="text-xs font-semibold text-blue-300 mb-3">Score Breakdown</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Tests Passed</span>
                        <span className="font-semibold text-white">{result.passed_tests}/{result.total_tests}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Final Score</span>
                        <span className="font-bold text-emerald-400">{result.score} points</span>
                      </div>
                    </div>
                  </div>

                  {/* Detailed Breakdown */}
                  {result.logic_analysis.breakdown && (
                    <div className="rounded-xl p-4" style={{ background: 'rgba(30,30,50,0.6)', border: '1px solid rgba(255,255,255,0.08)' }}>
                      <div className="text-xs font-semibold text-slate-300 mb-3">Detailed Analysis</div>
                      <div className="space-y-3">
                        {Object.entries(result.logic_analysis.breakdown).map(([key, value]) => (
                          <div key={key}>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-slate-400 capitalize">{key.replace(/_/g, ' ')}</span>
                              <span className="text-xs font-semibold" 
                                style={{ 
                                  color: value >= 70 ? '#34d399' : value >= 40 ? '#fbbf24' : '#f87171' 
                                }}
                              >
                                {value}%
                              </span>
                            </div>
                            <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.05)' }}>
                              <div 
                                className="h-full transition-all duration-500" 
                                style={{ 
                                  width: `${value}%`,
                                  background: value >= 70 
                                    ? 'linear-gradient(90deg, #10b981, #34d399)' 
                                    : value >= 40 
                                    ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' 
                                    : 'linear-gradient(90deg, #ef4444, #f87171)'
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Suggestions */}
                  {result.logic_analysis.suggestions && result.logic_analysis.suggestions.length > 0 && (
                    <div className="rounded-xl p-4" style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.3)' }}>
                      <div className="text-xs font-semibold text-blue-300 mb-3 flex items-center gap-2">
                        <Icon name="bulb" size={14} className="" /> Suggestions for Improvement
                      </div>
                      <ul className="space-y-2">
                        {result.logic_analysis.suggestions.map((suggestion, idx) => (
                          <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                            <span className="text-blue-400 mt-0.5">•</span>
                            <span>{suggestion}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          )}
        </div>

        {/* Status Bar */}
        <div className="h-6 flex items-center px-3 text-[11px] shrink-0" style={{ background: '#1e1e2e', borderTop: '1px solid rgba(255,255,255,0.06)', color: '#64748b' }}>
          <div className="flex items-center gap-4">
            <span>{currentLang.label}</span>
            <span>UTF-8</span>
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-4">
            {result && (
              result.error
                ? <span className="flex items-center gap-1 text-xs" style={{ color: '#f87171' }}>
                    ✗ {result.error}
                  </span>
                : <span className="flex items-center gap-1 text-xs" style={{ color: result.status === 'passed' ? '#34d399' : '#f87171' }}>
                    {result.status === 'passed' ? '✓' : '✗'} {result.passed_tests}/{result.total_tests} passed
                  </span>
            )}
            <span>{lobby?.name || 'CompileX'}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
