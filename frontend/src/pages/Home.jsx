import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import Logo from '../components/Logo'

const STATS = [
  { value: '50K+', label: 'coder hours completed' },
  { value: '10K+', label: 'active coders' },
  { value: '500+', label: 'daily matches' },
  { value: '40+', label: 'programming languages' },
]

const FEATURES = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    title: 'Real-Time Coding Battles',
    desc: 'Compete live with multiple players in simultaneous coding challenges'
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    title: 'AI-Generated Challenges',
    desc: 'Unique problems generated on-demand using advanced AI technology'
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    title: 'Live Leaderboard',
    desc: 'Watch rankings update in real-time during matches'
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    title: 'Timed Challenges',
    desc: 'Test your speed with countdown timers and pressure rounds'
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
    title: 'Multi-Language Support',
    desc: 'Python, JavaScript, C++, Java, C and 35+ more languages'
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    title: 'Multiplayer Rooms',
    desc: 'Create private rooms for team interviews and group practice'
  },
]

const GAME_MODES = [
  { value: 'multiplayer', title: 'Arena Match', desc: 'Multiplayer competition', icon: '👥' },
  { value: '1v1', title: '1v1 Duel', desc: 'Head-to-head', icon: '⚔️' },
  { value: 'tournament', title: 'Tournament', desc: 'Bracket elimination', icon: '🏆' },
]

const TESTIMONIALS = [
  { quote: "CompileX helped me land my dream job at Google. The real-time practice was invaluable.", name: "Manmohit", role: "Software Engineer at Google" },
  { quote: "Best platform for practicing coding under pressure. The AI questions are top-notch.", name: "Ikjot", role: "CS Student at MIT" },
  { quote: "We've used CompileX for 50+ interviews. The quality of candidates improved dramatically.", name: "Kabir", role: "Tech Lead at Amazon" },
]

// Scroll reveal hook
function useScrollReveal() {
  const ref = useRef(null)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.1, rootMargin: '50px' }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  return [ref, isVisible]
}

// Typewriter hook for code animation with realistic typing
function useTypewriter(text, speed = 30) {
  const [displayText, setDisplayText] = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (currentIndex < text.length) {
      // Variable speed for more realistic typing
      const char = text[currentIndex]
      const randomSpeed = char === '\n' ? speed * 3 : speed + Math.random() * 20
      
      const timeout = setTimeout(() => {
        setDisplayText(prev => prev + text[currentIndex])
        setCurrentIndex(prev => prev + 1)
      }, randomSpeed)
      return () => clearTimeout(timeout)
    }
  }, [currentIndex, text, speed])

  return { displayText, isComplete: currentIndex >= text.length }
}

// Code Snippet Component with Advanced Typewriter and Syntax Highlighting - OPTIMIZED
function CodeSnippet() {
  const codeExamples = useMemo(() => [
    {
      file: 'two_sum.py',
      lang: 'Python',
      code: `def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        comp = target - num
        if comp in seen:
            return [seen[comp], i]
        seen[num] = i
    return []`
    },
    {
      file: 'binary_search.cpp',
      lang: 'C++',
      code: `int binarySearch(vector<int>& arr, int x) {
    int lo = 0, hi = arr.size() - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] == x) return mid;
        if (arr[mid] < x) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}`
    },
    {
      file: 'fibonacci.js',
      lang: 'JavaScript',
      code: `function fibonacci(n) {
    if (n <= 1) return n;
    let a = 0, b = 1;
    for (let i = 2; i <= n; i++) {
        let temp = a + b;
        a = b;
        b = temp;
    }
    return b;
}`
    }
  ], [])

  const [currentExample, setCurrentExample] = useState(0)
  const [displayCode, setDisplayCode] = useState('')
  const [charIndex, setCharIndex] = useState(0)
  const [isTyping, setIsTyping] = useState(true)

  const example = codeExamples[currentExample]
  const fullCode = example.code

  useEffect(() => {
    if (isTyping && charIndex < fullCode.length) {
      const currentChar = fullCode[charIndex]
      
      // Check if we just typed a newline
      if (currentChar === '\n') {
        // Look ahead to count leading spaces on the next line
        let spacesToAdd = 0
        let lookAhead = charIndex + 1
        while (lookAhead < fullCode.length && fullCode[lookAhead] === ' ') {
          spacesToAdd++
          lookAhead++
        }
        
        // Add newline + all leading spaces instantly
        const timeout = setTimeout(() => {
          setDisplayCode(fullCode.substring(0, charIndex + 1 + spacesToAdd))
          setCharIndex(prev => prev + 1 + spacesToAdd)
        }, 80)
        return () => clearTimeout(timeout)
      }
      
      // Skip spaces at the beginning of lines (already added)
      if (currentChar === ' ' && charIndex > 0 && fullCode[charIndex - 1] === '\n') {
        // This space was already added, skip it
        setCharIndex(prev => prev + 1)
        return
      }
      
      // Normal typing for other characters
      const timeout = setTimeout(() => {
        setDisplayCode(fullCode.substring(0, charIndex + 1))
        setCharIndex(prev => prev + 1)
      }, 80)
      return () => clearTimeout(timeout)
    } else if (isTyping && charIndex >= fullCode.length) {
      // Pause before erasing
      const timeout = setTimeout(() => {
        setIsTyping(false)
      }, 3500)
      return () => clearTimeout(timeout)
    } else if (!isTyping && displayCode.length > 0) {
      // Erasing phase - moderate speed
      const timeout = setTimeout(() => {
        setDisplayCode(prev => prev.slice(0, -1))
      }, 20)
      return () => clearTimeout(timeout)
    } else if (!isTyping && displayCode.length === 0) {
      // Move to next example
      setCurrentExample((prev) => (prev + 1) % codeExamples.length)
      setCharIndex(0)
      setIsTyping(true)
    }
  }, [charIndex, displayCode, isTyping, fullCode, codeExamples.length])

  // Optimized syntax highlighting - render as React elements
  const highlightedCode = useMemo(() => {
    const keywords = ['def', 'return', 'for', 'in', 'if', 'while', 'function', 'const', 'let', 'class', 'vector', 'int', 'auto', 'this', 'new']
    const lines = displayCode.split('\n')
    
    return lines.map((line, lineIdx) => {
      const isLastLine = lineIdx === lines.length - 1
      const parts = []
      let remaining = line
      let key = 0
      
      // Process line character by character to preserve exact formatting
      while (remaining.length > 0) {
        let matched = false
        
        // Check for keywords
        for (const keyword of keywords) {
          if (remaining.startsWith(keyword)) {
            // Check if it's a whole word (not part of another word)
            const nextChar = remaining[keyword.length]
            if (!nextChar || /[^a-zA-Z0-9_]/.test(nextChar)) {
              parts.push(
                <span key={key++} className="text-blue-400 font-semibold">{keyword}</span>
              )
              remaining = remaining.slice(keyword.length)
              matched = true
              break
            }
          }
        }
        
        if (!matched) {
          // Check for numbers
          const numMatch = remaining.match(/^\d+/)
          if (numMatch) {
            parts.push(
              <span key={key++} className="text-emerald-400">{numMatch[0]}</span>
            )
            remaining = remaining.slice(numMatch[0].length)
          } else {
            // Regular character
            parts.push(<span key={key++}>{remaining[0]}</span>)
            remaining = remaining.slice(1)
          }
        }
      }
      
      return (
        <div key={lineIdx}>
          {parts}
          {isLastLine && (
            <span className="inline-block w-[2px] h-[18px] bg-blue-400 ml-[1px] animate-blink align-text-bottom" />
          )}
        </div>
      )
    })
  }, [displayCode])

  const lines = displayCode.split('\n')

  return (
    <div className="code-card max-w-2xl mx-auto animate-scale-in group hover:scale-[1.02] transition-all duration-500 relative animate-float gpu-accelerated" style={{ animationDelay: '0.4s' }}>
      {/* Glow effect */}
      <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/20 via-cyan-500/20 to-blue-500/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-pulse-slow" />
      
      <div className="relative bg-black rounded-2xl overflow-hidden border border-blue-500/20">
        <div className="code-header px-4 py-3 flex items-center gap-2 border-b border-white/10 bg-black">
          <div className="code-dot red transition-transform duration-300 group-hover:scale-125" />
          <div className="code-dot yellow transition-transform duration-300 group-hover:scale-125" />
          <div className="code-dot green transition-transform duration-300 group-hover:scale-125" />
          <span className="ml-3 text-xs text-slate-400 font-mono transition-colors duration-300 group-hover:text-slate-300">
            {example.file}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-medium">
              {example.lang}
            </span>
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-emerald-400 font-medium">Live</span>
            </div>
          </div>
        </div>
        
        <div className="relative">
          {/* Line numbers */}
          <div className="absolute left-0 top-0 px-3 py-4 text-xs text-slate-600 font-mono select-none pointer-events-none bg-black border-r border-white/10">
            {lines.map((_, i) => (
              <div key={i} className="leading-[1.6] h-[22.4px]">{i + 1}</div>
            ))}
          </div>

          {/* Code content */}
          <div className="pl-12 pr-4 py-4 min-h-[280px]">
            <pre className="text-sm text-slate-300 font-mono leading-[1.6] whitespace-pre-wrap break-words">
              {highlightedCode}
            </pre>
          </div>
        </div>

        {/* Status bar */}
        <div className="px-4 py-2 border-t border-white/10 flex items-center justify-between text-[10px] text-slate-500 font-mono bg-black">
          <div className="flex items-center gap-3">
            <span>UTF-8</span>
            <span>Ln {lines.length}</span>
            <span>Col {lines[lines.length - 1]?.length || 0}</span>
          </div>
          <div className="flex items-center gap-2">
            {codeExamples.map((_, idx) => (
              <div
                key={idx}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  idx === currentExample ? 'bg-blue-400 w-4' : 'bg-slate-600 w-1.5'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Features Section Component
function FeaturesSection({ features }) {
  const [ref, isVisible] = useScrollReveal()

  return (
    <section id="features" className="py-20 px-6" ref={ref}>
      <div className="max-w-7xl mx-auto">
        <div className={`text-center mb-12 transition-all duration-700 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent mb-3">Platform Features</h2>
          <p className="text-slate-400 max-w-xl mx-auto">Everything you need for competitive programming practice</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={index}
              className={`glass-card p-6 bg-slate-900/40 backdrop-blur-sm transition-all duration-500 hover:-translate-y-2 hover:shadow-xl hover:shadow-blue-900/30 cursor-default border border-blue-500/20 hover:border-blue-500/40 ${
                isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
              }`}
              style={{ transitionDelay: `${index * 100}ms` }}
            >
              <div className="feature-icon mb-4 text-blue-400 transition-all duration-300 hover:scale-110 hover:rotate-6">{feature.icon}</div>
              <h3 className="text-lg font-semibold text-white mb-2 transition-colors duration-300 hover:text-blue-300">{feature.title}</h3>
              <p className="text-slate-400 text-sm">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// Game Modes Section Component
function GameModesSection({ modes }) {
  const [ref, isVisible] = useScrollReveal()

  return (
    <section id="modes" className="py-20 px-6 bg-gradient-to-b from-blue-900/10 to-transparent" ref={ref}>
      <div className="max-w-7xl mx-auto">
        <div className={`text-center mb-12 transition-all duration-700 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent mb-3">How It Works</h2>
          <p className="text-slate-400 max-w-xl mx-auto">Choose your battle format</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {modes.map((mode, index) => (
            <div
              key={index}
              className={`glass-panel p-8 bg-slate-900/40 backdrop-blur-sm text-center transition-all duration-500 hover:-translate-y-3 hover:shadow-2xl hover:shadow-blue-900/40 cursor-pointer border border-blue-500/20 hover:border-blue-500/40 group ${
                isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-90'
              }`}
              style={{ transitionDelay: `${index * 150}ms` }}
            >
              <div className="text-4xl mb-4 transition-transform duration-500 group-hover:scale-125 group-hover:rotate-12">{mode.icon}</div>
              <h3 className="text-xl font-semibold text-white mb-2 transition-colors duration-300 group-hover:text-blue-300">{mode.title}</h3>
              <p className="text-slate-400 text-sm">{mode.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// Testimonials Section Component
function TestimonialsSection({ testimonials }) {
  const [ref, isVisible] = useScrollReveal()

  return (
    <section id="testimonials" className="py-20 px-6" ref={ref}>
      <div className="max-w-7xl mx-auto">
        <div className={`text-center mb-12 transition-all duration-700 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent mb-3">What Coders Say</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {testimonials.map((t, index) => (
            <div
              key={index}
              className={`testimonial-card bg-slate-900/40 backdrop-blur-sm transition-all duration-500 hover:-translate-y-2 hover:shadow-xl hover:shadow-blue-900/30 cursor-default border border-blue-500/20 hover:border-blue-500/40 ${
                isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'
              }`}
              style={{ transitionDelay: `${index * 120}ms` }}
            >
              <p className="text-slate-300 mb-4">"{t.quote}"</p>
              <div>
                <div className="font-semibold text-white">{t.name}</div>
                <div className="text-sm text-slate-500">{t.role}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const HOME_STYLES = `
  @keyframes slideUp {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-30px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
  }
  @keyframes gradient {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
  }
  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }
  @keyframes pulseSlow {
    0%, 100% { opacity: 0.5; transform: scale(1); }
    50% { opacity: 0.8; transform: scale(1.05); }
  }
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
  }
  @keyframes orb1 {
    0%, 100% { transform: translate(0,0) scale(1); opacity: 0.15; }
    33% { transform: translate(60px,-40px) scale(1.1); opacity: 0.25; }
    66% { transform: translate(-40px,30px) scale(0.95); opacity: 0.18; }
  }
  @keyframes orb2 {
    0%, 100% { transform: translate(0,0) scale(1); opacity: 0.12; }
    33% { transform: translate(-50px,60px) scale(1.15); opacity: 0.22; }
    66% { transform: translate(70px,-30px) scale(0.9); opacity: 0.15; }
  }
  @keyframes orb3 {
    0%, 100% { transform: translate(0,0) scale(1); opacity: 0.1; }
    50% { transform: translate(40px,50px) scale(1.2); opacity: 0.2; }
  }
  @keyframes codeFloat {
    0%, 100% { transform: translateY(0px) translateX(0px) rotate(0deg); }
    25% { transform: translateY(-20px) translateX(15px) rotate(5deg); }
    50% { transform: translateY(-10px) translateX(-10px) rotate(-3deg); }
    75% { transform: translateY(-25px) translateX(20px) rotate(8deg); }
  }
  @keyframes codeFloat2 {
    0%, 100% { transform: translateY(0px) translateX(0px) rotate(0deg); }
    30% { transform: translateY(-15px) translateX(-20px) rotate(-6deg); }
    60% { transform: translateY(-25px) translateX(15px) rotate(4deg); }
  }
  @keyframes codeDrift {
    0%, 100% { transform: translateY(0px) translateX(0px) rotate(0deg); }
    20% { transform: translateY(-18px) translateX(10px) rotate(3deg); }
    40% { transform: translateY(-8px) translateX(-15px) rotate(-5deg); }
    60% { transform: translateY(-22px) translateX(20px) rotate(7deg); }
    80% { transform: translateY(-12px) translateX(-5px) rotate(-2deg); }
  }
  .animate-fade-in { animation: fadeIn 0.6s ease-out; }
  .animate-scale-in { animation: scaleIn 0.6s ease-out; }
  .animate-blink { animation: blink 1s step-end infinite; }
  .animate-pulse-slow { animation: pulseSlow 4s ease-in-out infinite; }
  .animate-float { animation: float 3s ease-in-out infinite; }
  .animate-gradient {
    background: linear-gradient(270deg, #A387FF, #B8A0FF, #5AA2FF);
    background-size: 300% 300%;
    animation: gradient 5s ease infinite;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
`

export default function Home() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  
  const [joinCode, setJoinCode] = useState('')
  const [lobbyName, setLobbyName] = useState('')
  const [maxPlayers, setMaxPlayers] = useState(10)
  const [timeLimit, setTimeLimit] = useState(1800)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState('create')

  const [gameMode, setGameMode] = useState('multiplayer')
  const [isPublic, setIsPublic] = useState(false)
  const [publicLobbies, setPublicLobbies] = useState([])
  const [loadingPublic, setLoadingPublic] = useState(false)
  const [homeDifficulty, setHomeDifficulty] = useState('medium')

  // Pre-compute random positions once — avoids jitter on re-render
  const codeSymbolPositions = useMemo(() => {
    const symbols = [
      'function()', '{ }', '[ ]', '< />', '=>', 'return []',
      '&&', '||', 'null', '!==', '++', 'async',
      'O(log n)', '( )', 'dp[i][j]', 'while(true)',
      '--', 'const', 'void', 'break',
    ]
    const colors = ['#8B6CFF','#3B8CFF','#5AA2FF','#5AA2FF','#3B8CFF',
                    '#B8A0FF','#f87171','#fb923c','#3DE0FF','#3DE0FF',
                    '#34d399','#A387FF','#4ade80','#fbbf24','#B8A0FF']
    const anims = ['codeFloat', 'codeFloat2', 'codeDrift']

    // Divide the space into a 5×4 grid of cells, pick one random point per cell
    const cols = 5, rows = 4
    const cellW = 90 / cols  // % width per cell
    const cellH = 88 / rows  // % height per cell

    // Shuffle symbols so assignment is random
    const shuffled = [...symbols].sort(() => Math.random() - 0.5)

    return shuffled.slice(0, cols * rows).map((sym, i) => {
      const col = i % cols
      const row = Math.floor(i / cols)
      // Random point within the cell with padding
      const left = col * cellW + Math.random() * (cellW - 10) + 2
      const top  = row * cellH + Math.random() * (cellH - 8)  + 4
      return {
        sym,
        left:    `${left.toFixed(1)}%`,
        top:     `${top.toFixed(1)}%`,
        color:   colors[Math.floor(Math.random() * colors.length)],
        size:    Math.floor(Math.random() * 8 + 14),         // 14–22px
        opacity: +(Math.random() * 0.10 + 0.12).toFixed(2), // 0.12–0.22
        dur:     `${(Math.random() * 5 + 6).toFixed(1)}s`,  // 6–11s
        delay:   `${(Math.random() * 5).toFixed(1)}s`,      // 0–5s
        anim:    anims[Math.floor(Math.random() * anims.length)],
      }
    })
  }, [])

  useEffect(() => {
    if (tab === 'browse') fetchPublicLobbies()
  }, [tab])

  async function fetchPublicLobbies() {
    setLoadingPublic(true)
    try {
      const { data } = await api.get('/lobbies/public')
      setPublicLobbies(data)
    } catch { }
    finally { setLoadingPublic(false) }
  }

  async function createLobby(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data: lobby } = await api.post('/lobbies', {
        name: lobbyName || `${user.username}'s Arena`,
        max_players: Number(maxPlayers),
        time_limit: Number(timeLimit),
        game_mode: gameMode,
        is_public: isPublic,
        match_config: {
          num_rounds: 1,
          questions_per_round: 1,
          difficulty: homeDifficulty,
          time_per_question: Number(timeLimit),
        },
      })
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      navigate(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create')
    } finally {
      setLoading(false)
    }
  }

  async function joinLobby(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data: lobby } = await api.get(`/lobbies/${joinCode.toUpperCase()}`)
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      navigate(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Arena not found')
    } finally {
      setLoading(false)
    }
  }

  async function joinPublicLobby(lobby) {
    setError('')
    setLoading(true)
    try {
      const { data: player } = await api.post(`/lobbies/${lobby.id}/join`, {})
      navigate(`/lobby/${lobby.code}`, { state: { lobby, player_id: player.player_id } })
    } catch (err) {
      setError(err.response?.data?.detail || 'Join failed')
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { key: 'create', label: 'Create' },
    { key: 'join', label: 'Join' },
    { key: 'browse', label: 'Browse' },
    { key: 'practice', label: 'Practice' },
  ]

  return (
    <div className="min-h-screen gradient-bg">
      <style>{HOME_STYLES}</style>
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-blue-900/20 via-slate-900/20 to-pink-900/20 backdrop-blur-xl border-b border-blue-500/20 animate-slide-down">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 group cursor-pointer">
            <Logo size={40} className="transition-all duration-300 group-hover:scale-110 group-hover:rotate-12" />
            <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent transition-all duration-300 group-hover:tracking-wide">CompileX</span>
          </div>
          
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-slate-400 hover:text-blue-300 transition-all duration-300 hover:scale-105 relative after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5 after:bg-gradient-to-r after:from-blue-500 after:to-cyan-500 after:transition-all after:duration-300 hover:after:w-full">Features</a>
            <a href="#modes" className="text-sm text-slate-400 hover:text-blue-300 transition-all duration-300 hover:scale-105 relative after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5 after:bg-gradient-to-r after:from-blue-500 after:to-cyan-500 after:transition-all after:duration-300 hover:after:w-full">Game Modes</a>
            <a href="#testimonials" className="text-sm text-slate-400 hover:text-blue-300 transition-all duration-300 hover:scale-105 relative after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5 after:bg-gradient-to-r after:from-blue-500 after:to-cyan-500 after:transition-all after:duration-300 hover:after:w-full">Testimonials</a>
          </div>

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-900/30 backdrop-blur-sm rounded-full border border-blue-500/20 transition-all duration-300 hover:scale-105 hover:bg-blue-900/50 hover:border-blue-500/40">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-sm text-white">{user.username}</span>
                </div>
                <button onClick={() => navigate('/dashboard')} className="text-sm text-slate-400 hover:text-blue-300 transition-all duration-300 hover:scale-105">Dashboard</button>
                <button onClick={logout} className="text-sm text-slate-400 hover:text-pink-300 transition-all duration-300 hover:scale-105">Sign out</button>
              </>
            ) : (
              <>
                <button onClick={() => navigate('/login')} className="text-sm text-slate-400 hover:text-blue-300 transition-all duration-300 hover:scale-105">Sign In</button>
                <button onClick={() => navigate('/dashboard')} className="btn-primary text-sm px-5 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-blue-500/50">Get Started</button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-32 pb-20 px-6 relative overflow-hidden">
        {/* Animated background elements */}
        <div className="absolute inset-0 pointer-events-none">
          {/* Moving orbs - purple/pink theme */}
          <div className="absolute top-[-100px] left-[10%] w-[700px] h-[700px] rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(59,140,255,0.18) 0%, transparent 70%)', animation: 'orb1 12s ease-in-out infinite', willChange: 'transform' }} />
          <div className="absolute top-[20%] right-[-100px] w-[600px] h-[600px] rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(23,205,239,0.15) 0%, transparent 70%)', animation: 'orb2 15s ease-in-out infinite', willChange: 'transform' }} />
          <div className="absolute bottom-[-50px] left-[30%] w-[500px] h-[500px] rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(163,135,255,0.12) 0%, transparent 70%)', animation: 'orb3 10s ease-in-out infinite', willChange: 'transform' }} />

          {/* Static grid — no animation, no repaint */}
          <div className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: 'linear-gradient(rgba(59,140,255,0.8) 1px, transparent 1px), linear-gradient(90deg, rgba(59,140,255,0.8) 1px, transparent 1px)',
              backgroundSize: '60px 60px',
            }} />

          {/* Enhanced floating code symbols — large background layer */}
          {codeSymbolPositions.map((item, i) => (
            <div 
              key={i} 
              className="absolute font-mono font-bold select-none"
              style={{
                fontSize: item.size + 'px',
                left: item.left,
                top: item.top,
                color: item.color,
                opacity: item.opacity,
                textShadow: `0 0 14px ${item.color}60`,
                animation: `${item.anim} ${item.dur} ease-in-out ${item.delay} infinite`,
                willChange: 'transform',
              }}>
              {item.sym}
            </div>
          ))}

          {/* Corner accents */}
          <div className="absolute top-0 left-0 w-64 h-64 opacity-20"
            style={{ background: 'conic-gradient(from 180deg at 0% 0%, #3B8CFF, transparent 40%)' }} />
          <div className="absolute top-0 right-0 w-64 h-64 opacity-20"
            style={{ background: 'conic-gradient(from 270deg at 100% 0%, #17CDEF, transparent 40%)' }} />

          {/* Bottom fade */}
          <div className="absolute bottom-0 left-0 right-0 h-32"
            style={{ background: 'linear-gradient(to bottom, transparent, #0F0F0F)' }} />
        </div>

        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-8 animate-fade-in">
            <span className="badge animate-scale-in hover:scale-110 transition-all duration-300 cursor-default inline-flex items-center gap-2 bg-blue-900/30 backdrop-blur-sm border-blue-500/30">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              Join 10,000+ Active Coders
            </span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold text-white text-center mb-6 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <span className="inline-block hover:scale-105 transition-transform duration-300">Code.</span>{' '}
            <span className="inline-block hover:scale-105 transition-transform duration-300">Compete.</span>
            <span className="block mt-2">
              <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent inline-block hover:scale-105 transition-transform duration-300 animate-gradient" style={{ backgroundSize: '200% auto' }}>Conquer.</span>
            </span>
          </h1>
          
          <p className="text-lg text-slate-400 text-center max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up" style={{ animationDelay: '0.2s' }}>
            Real-time multiplayer coding platform with AI-generated challenges. 
            Compete against developers worldwide and level up your skills.
          </p>

          <div className="flex items-center justify-center gap-4 mb-16 animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <button onClick={() => user ? navigate('/dashboard') : navigate('/login')} className="btn-primary px-8 py-3.5 text-base bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 transition-all duration-300 hover:scale-105 hover:shadow-2xl hover:shadow-blue-500/50 hover:-translate-y-1 active:scale-95 relative overflow-hidden group">
              <span className="relative z-10 flex items-center gap-2">
                {user ? (
                  <>
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    Launch Arena
                  </>
                ) : (
                  'Start Coding Free'
                )}
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </button>
            <button className="btn-secondary px-8 py-3.5 text-base border-blue-500/30 hover:border-blue-500/50 hover:bg-blue-900/20 transition-all duration-300 hover:scale-105 hover:-translate-y-1 active:scale-95">
              Learn More
            </button>
          </div>

          {/* Code Snippet */}
          <CodeSnippet />
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 px-6 border-y border-blue-500/20 bg-gradient-to-r from-blue-500/5 via-transparent to-cyan-500/5">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {STATS.map((stat, index) => (
              <div key={index} className="text-center group cursor-default animate-fade-in" style={{ animationDelay: `${index * 0.1}s` }}>
                <div className="stat-number text-white transition-all duration-300 group-hover:scale-110 group-hover:bg-gradient-to-r group-hover:from-blue-400 group-hover:to-cyan-400 group-hover:bg-clip-text group-hover:text-transparent">{stat.value}</div>
                <div className="stat-label transition-colors duration-300 group-hover:text-slate-300">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <FeaturesSection features={FEATURES} />

      {/* Game Modes */}
      <GameModesSection modes={GAME_MODES} />

      {/* Testimonials */}
      <TestimonialsSection testimonials={TESTIMONIALS} />

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-blue-500/20 bg-gradient-to-r from-blue-900/10 to-pink-900/10">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-sm text-slate-500">
          <div>CompileX © 2024. All rights reserved.</div>
          <div className="flex items-center gap-6">
            <span className="hover:text-blue-400 transition-colors duration-300 cursor-pointer">Privacy</span>
            <span className="hover:text-blue-400 transition-colors duration-300 cursor-pointer">Terms</span>
            <span className="hover:text-blue-400 transition-colors duration-300 cursor-pointer">Contact</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
