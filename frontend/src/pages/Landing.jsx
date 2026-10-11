import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Logo from '../components/Logo'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import AnimatedGlobe3D from '../components/AnimatedGlobe3D'
import LearnMore from '../components/LearnMore'
import Icon from '../components/Icons'

// ---------------------------------------------------------------------------
// Typewriter hook for hero title - types full sentence character by character
// ---------------------------------------------------------------------------
function useHeroTypewriter() {
  const sentence = "Code. Compete. Conquer."
  
  const [displayText, setDisplayText] = useState('')
  const [charIndex, setCharIndex] = useState(0)
  const [isErasing, setIsErasing] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [hasCompletedOnce, setHasCompletedOnce] = useState(false)
  
  useEffect(() => {
    if (!isErasing && charIndex < sentence.length) {
      // Typing phase - add characters one by one
      const timeout = setTimeout(() => {
        setDisplayText(sentence.substring(0, charIndex + 1))
        setCharIndex(prev => prev + 1)
      }, 80) // 80ms per character
      return () => clearTimeout(timeout)
    } else if (!isErasing && charIndex >= sentence.length) {
      // Fully typed: stay that way.
      if (!isComplete) {
        setIsComplete(true)
        setHasCompletedOnce(true)
      }
    } else if (isErasing && displayText.length > 0) {
      // Erasing phase - backspace animation
      const timeout = setTimeout(() => {
        setDisplayText(prev => prev.slice(0, -1))
        setCharIndex(prev => prev - 1)
      }, 40) // 40ms per backspace (faster than typing)
      return () => clearTimeout(timeout)
    } else if (isErasing && displayText.length === 0) {
      // All erased, restart typing
      setIsErasing(false)
      setCharIndex(0)
      setIsComplete(false)
    }
  }, [charIndex, displayText.length, isErasing, isComplete, sentence])
  
  return { displayText, isComplete, hasCompletedOnce, isTyping: !isErasing }
}

// ---------------------------------------------------------------------------
// Scroll reveal hook - OPTIMIZED: Disconnect after reveal
// ---------------------------------------------------------------------------
// Sections are always visible; nothing waits for a scroll to appear.
function useScrollReveal() {
  return [useRef(null), true]
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

const SNIPPETS = [
  {
    file: 'max_subarray.py',
    lang: 'python',
    lines: [
      "# Kadane's Algorithm",
      "def maxSubarray(nums):",
      "    best = curr = nums[0]",
      "    for x in nums[1:]:",
      "        curr = max(x, curr + x)",
      "        best = max(best, curr)",
      "    return best",
    ],
  },
  {
    file: 'quicksort.js',
    lang: 'javascript',
    lines: [
      "function quickSort(arr) {",
      "  if (arr.length <= 1) return arr;",
      "  const pivot = arr[0];",
      "  const left = arr.slice(1).filter(x => x < pivot);",
      "  const right = arr.slice(1).filter(x => x >= pivot);",
      "  return [...quickSort(left), pivot, ...quickSort(right)];",
      "}",
    ],
  },
  {
    file: 'binary_search.cpp',
    lang: 'cpp',
    lines: [
      "int binarySearch(vector<int>& arr, int target) {",
      "    int lo = 0, hi = arr.size() - 1;",
      "    while (lo <= hi) {",
      "        int mid = lo + (hi - lo) / 2;",
      "        if (arr[mid] == target) return mid;",
      "        else if (arr[mid] < target) lo = mid + 1;",
      "        else hi = mid - 1;",
      "    }",
      "    return -1;",
      "}",
    ],
  },
  {
    file: 'fibonacci.java',
    lang: 'java',
    lines: [
      "public int fibonacci(int n) {",
      "    if (n <= 1) return n;",
      "    int a = 0, b = 1;",
      "    for (int i = 2; i <= n; i++) {",
      "        int temp = a + b;",
      "        a = b;",
      "        b = temp;",
      "    }",
      "    return b;",
      "}",
    ],
  },
  {
    file: 'reverse_string.c',
    lang: 'c',
    lines: [
      "void reverseString(char* str) {",
      "    int left = 0;",
      "    int right = strlen(str) - 1;",
      "    while (left < right) {",
      "        char temp = str[left];",
      "        str[left++] = str[right];",
      "        str[right--] = temp;",
      "    }",
      "}",
    ],
  },
]

const STATS = [
  { value: '50K+', label: 'Coder Hours Completed' },
  { value: '10K+', label: 'Active Coders' },
  { value: '500+', label: 'Daily Matches' },
  { value: '40+',  label: 'Programming Languages' },
]

const FEATURES = [
  { icon: 'bolt', title: 'Real-Time Coding Battles',  desc: 'Compete live with multiple players in simultaneous coding challenges' },
  { icon: 'message', title: 'AI-Generated Challenges',   desc: 'Unique problems generated on-demand using advanced AI technology' },
  { icon: 'bars', title: 'Live Leaderboard',          desc: 'Watch rankings update in real-time during matches' },
  { icon: 'clock', title: 'Timed Challenges',          desc: 'Test your speed with countdown timers and pressure rounds' },
  { icon: 'code', title: 'Multi-Language Support',   desc: 'Python, JavaScript, C++, Java, C and 35+ more languages' },
  { icon: 'users', title: 'Multiplayer Rooms',         desc: 'Create private rooms for team interviews and group practice' },
]

const GAME_MODES = [
  { icon: 'duel', title: 'Arena Match', desc: 'Multiplayer competition' },
  { icon: 'target', title: '1v1 Duel',    desc: 'Head-to-head' },
  { icon: 'trophy', title: 'Tournament',  desc: 'Bracket elimination' },
]

const TESTIMONIALS = [
  { name: 'Kabir',     role: 'Software Engineer at Google', text: 'CompileX helped me land my dream job at Google. The real-time practice was invaluable.' },
  { name: 'Ikjot',     role: 'CS Student at MIT',           text: 'Best platform for practicing coding under pressure. The AI questions are top-notch.' },
  { name: 'Manmohit',  role: 'Tech Lead at Amazon',         text: "We've used CompileX for 50+ interviews. The quality of candidates improved dramatically." },
]

// ---------------------------------------------------------------------------
// Typewriter hook
// ---------------------------------------------------------------------------
function useTypewriter() {
  const [sIdx, setSIdx]       = useState(0)
  const [chars, setChars]     = useState(0)
  const [erasing, setErasing] = useState(false)

  const snippet  = SNIPPETS[sIdx]
  const fullText = snippet.lines.join('\n')

  useEffect(() => {
    if (chars >= fullText.length) return // finished: leave the code on screen

    const t = setTimeout(() => {
      setChars(c => c + 1)
    }, 28)

    return () => clearTimeout(t)
  }, [chars, erasing, fullText.length])

  const visible = fullText.slice(0, chars)
  return { visible, file: snippet.file, lang: snippet.lang }
}

// ---------------------------------------------------------------------------
// Animated stat counter - OPTIMIZED: Faster animation, cleanup
// ---------------------------------------------------------------------------
function AnimatedStat({ value, label }) {
  return (
    <div className="text-center px-4 cursor-default">
      <div className="text-4xl md:text-5xl font-bold text-white mb-2 tracking-tight tabular-nums">{value}</div>
      <div className="text-slate-400 text-sm font-medium">{label}</div>
    </div>
  )
}

// Old 2D backgrounds removed in favor of AnimatedBackground3D

// ---------------------------------------------------------------------------
// Live terminal
// ---------------------------------------------------------------------------
function LiveTerminal() {
  const { visible, file, lang } = useTypewriter()

  // Multi-language syntax highlighting
  function colourLine(line, language) {
    // Comments
    if (line.trim().startsWith('//') || line.trim().startsWith('#')) {
      return <span style={{ color: '#64748B' }}>{line}</span>
    }

    const parts = []
    let rest = line
    let key = 0

    // Language-specific keywords
    const keywords = {
      python: ['def ', 'for ', 'in ', 'if ', 'elif ', 'else:', 'return ', 'while ', 'class ', 'import ', 'from '],
      javascript: ['function ', 'const ', 'let ', 'var ', 'if ', 'else ', 'return ', 'for ', 'while ', 'class ', 'import ', 'export '],
      cpp: ['int ', 'void ', 'return ', 'if ', 'else ', 'for ', 'while ', 'vector<', 'class ', 'public:', 'private:'],
      java: ['public ', 'private ', 'int ', 'void ', 'return ', 'if ', 'else ', 'for ', 'while ', 'class ', 'static '],
      c: ['int ', 'void ', 'char', 'return ', 'if ', 'else ', 'for ', 'while ', 'struct ', 'sizeof'],
    }

    const kws = keywords[language] || keywords.python

    while (rest.length) {
      let matched = false
      
      // Check for keywords
      for (const kw of kws) {
        if (rest.startsWith(kw)) {
          parts.push(<span key={key++} style={{ color: '#C084FC' }}>{kw}</span>)
          rest = rest.slice(kw.length)
          matched = true
          break
        }
      }

      if (!matched) {
        // Find next keyword
        let end = rest.length
        for (const kw of kws) {
          const idx = rest.indexOf(kw)
          if (idx > 0 && idx < end) end = idx
        }
        
        const chunk = rest.slice(0, end)
        // Numbers in green, rest in white
        const color = /^\s*-?\d/.test(chunk) ? '#34D399' : '#E2E8F0'
        parts.push(<span key={key++} style={{ color }}>{chunk}</span>)
        rest = rest.slice(end)
      }
    }
    return parts
  }

  const lines = visible.split('\n')
  const currentLineIndex = lines.length - 1
  const isLastCharNewline = visible.endsWith('\n')

  // Always show 12 lines (pad with empty lines if needed)
  const displayLines = [...lines]
  while (displayLines.length < 12) {
    displayLines.push('')
  }
  // Limit to 12 lines
  const fixedLines = displayLines.slice(0, 12)

  return (
    <div className="relative max-w-4xl mx-auto group">
      <div className="absolute -inset-6 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-3xl blur-2xl pointer-events-none transition-all duration-500 group-hover:blur-3xl group-hover:from-blue-600/40 group-hover:to-cyan-600/40" style={{ transform: 'translateZ(0)', willChange: 'opacity, filter' }} />
      <div className="relative bg-[#0A0A10] border border-white/[0.07] rounded-2xl overflow-hidden shadow-2xl transition-all duration-500 hover:border-blue-500/40 hover:shadow-blue-900/40 hover:shadow-2xl ">

        {/* title bar */}
        <div className="flex items-center gap-2 px-4 py-3 bg-[#101018] border-b border-white/[0.05]">
          <div className="w-3 h-3 rounded-full bg-[#FF5F57] transition-all duration-300 hover:shadow-[0_0_15px_rgba(255,95,87,0.8)] cursor-pointer" />
          <div className="w-3 h-3 rounded-full bg-[#FFBD2E] transition-all duration-300 hover:shadow-[0_0_15px_rgba(255,189,46,0.8)] cursor-pointer" />
          <div className="w-3 h-3 rounded-full bg-[#28C840] transition-all duration-300 hover:shadow-[0_0_15px_rgba(40,200,64,0.8)] cursor-pointer" />
          <span className="text-slate-400 text-xs ml-3 font-mono transition-all duration-300 group-hover:text-blue-300 group-hover:tracking-wide">{file}</span>
          <span className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400 font-medium group">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 absolute" />
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 relative" />
            <span className="group-hover:tracking-wide transition-all duration-300">live</span>
          </span>
        </div>

        {/* code body with line numbers - FIXED HEIGHT */}
        <div className="flex font-mono text-base leading-8" style={{ height: '416px' }}>
          {/* Line numbers - always show 1-12 */}
          <div className="py-6 px-4 bg-[#0A0A10] border-r border-white/[0.05] select-none" style={{ minWidth: '64px' }}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((num) => (
              <div key={num} className="text-slate-600 text-right pr-4 transition-colors duration-300 hover:text-slate-400">
                {num}
              </div>
            ))}
          </div>
          
          {/* Code content */}
          <div className="flex-1 py-6 px-6 overflow-hidden">
            {fixedLines.map((line, i) => (
              <div key={i} className="transition-all duration-300 hover:bg-white/[0.02] -mx-2 px-2 rounded" style={{ fontFamily: 'monospace', whiteSpace: 'pre' }}>
                {colourLine(line, lang)}
                {/* Show cursor at the end of current line being typed */}
                {i === currentLineIndex && !isLastCharNewline && (
                  <span
                    className="inline-block w-[8px] h-[1.1em] bg-blue-400 align-middle"
                    style={{ animation: 'caBlink 1s step-end infinite' }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* status bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-[#101018] border-t border-white/[0.05] text-xs text-slate-500 font-mono">
          <span className="transition-colors duration-300 hover:text-blue-300">
            {lang === 'python' && 'Python 3.11'}
            {lang === 'javascript' && 'Node.js 20'}
            {lang === 'cpp' && 'C++ 17'}
            {lang === 'java' && 'Java 17'}
            {lang === 'c' && 'GCC 11'}
          </span>
          <span className="text-emerald-400 transition-all duration-300 ">All tests passed</span>
          <span className="transition-colors duration-300 hover:text-blue-300">UTF-8</span>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Features Section with scroll animations
// ---------------------------------------------------------------------------
function FeaturesSection() {
  const [ref, isVisible] = useScrollReveal()

  return (
    <div ref={ref}>
      <div className={`text-center mb-16 transition-all duration-700 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">Platform Features</h2>
        <p className="text-slate-400 max-w-xl mx-auto text-lg">Everything you need for competitive programming practice</p>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {FEATURES.map((f, i) => (
          <div
            key={i}
            className={`p-8 bg-[#0A0A10]/80 rounded-2xl hover:bg-[#141420]/90 transition-all duration-500 group cursor-default border border-white/[0.05] hover:border-blue-500/30 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] ${
              isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
            }`}
            style={{ transitionDelay: `${i * 100}ms` }}
          >
            <div className="w-12 h-12 rounded-xl bg-[#3b82f6]/10 group-hover:bg-[#3b82f6]/20 flex items-center justify-center mb-6 text-blue-400 transition-colors duration-300">
              <Icon name={f.icon} size={22} />
            </div>
            <h3 className="text-xl font-bold text-white mb-3 group-hover:text-blue-300 transition-colors duration-300">{f.title}</h3>
            <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Game Modes Section with scroll animations
// ---------------------------------------------------------------------------
function GameModesSection() {
  const [ref, isVisible] = useScrollReveal()

  return (
    <div ref={ref}>
      <div className={`text-center mb-16 transition-all duration-700 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">Game Modes</h2>
        <p className="text-slate-400 max-w-xl mx-auto text-lg">Choose your battle format</p>
      </div>
      <div className="grid md:grid-cols-3 gap-6">
        {GAME_MODES.map((m, i) => (
          <div
            key={i}
            className={`p-10 bg-[#0A0A10]/80 rounded-2xl text-center hover:shadow-[0_0_40px_rgba(59,130,246,0.2)] transition-all duration-500 cursor-pointer border border-white/[0.05] hover:border-blue-500/40 group ${
              isVisible ? 'opacity-100 scale-100' : 'opacity-0 scale-90'
            }`}
            style={{ transitionDelay: `${i * 150}ms` }}
          >
            <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-[#3b82f6]/10 flex items-center justify-center text-blue-400"><Icon name={m.icon} size={30} /></div>
            <h3 className="text-2xl font-bold text-white mb-3 group-hover:text-blue-300 transition-colors duration-300">{m.title}</h3>
            <p className="text-slate-400 text-sm">{m.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Testimonials Section with scroll animations
// ---------------------------------------------------------------------------
function TestimonialsSection() {
  const [ref, isVisible] = useScrollReveal()

  return (
    <div ref={ref}>
      <div className={`text-center mb-16 transition-all duration-700 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">What Coders Say</h2>
        <p className="text-slate-400 max-w-xl mx-auto text-lg">Join the community of improving developers</p>
      </div>
      <div className="grid md:grid-cols-3 gap-6">
        {TESTIMONIALS.map((t, i) => (
          <div
            key={i}
            className={`p-8 bg-[#0A0A10]/80 rounded-2xl flex flex-col justify-between hover:bg-[#141420]/90 transition-all duration-500 cursor-default border border-white/[0.05] hover:border-blue-500/30 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] ${
              isVisible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'
            }`}
            style={{ transitionDelay: `${i * 120}ms` }}
          >
            <p className="text-slate-300 mb-8 italic leading-relaxed">"{t.text}"</p>
            <div>
              <div className="text-white font-bold">{t.name}</div>
              <div className="text-slate-500 text-sm font-medium">{t.role}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hero Title Component (Isolated to prevent full page re-renders on typing)
// ---------------------------------------------------------------------------
const HeroTitle = React.memo(({ isDarkMode, onCompleteOnce }) => {
  const { displayText, hasCompletedOnce } = useHeroTypewriter()
  
  useEffect(() => {
    if (hasCompletedOnce) onCompleteOnce()
  }, [hasCompletedOnce, onCompleteOnce])

  const renderTitle = (text) => {
    // Split the current text by ". " to separate the words
    const words = text.split('. ')
    
    return words.map((word, index) => {
      // If this is not the last item in the split array, it means it had a ". " after it
      // So we append the "." back. We also don't want to add a <br/> if it's just an empty string at the end.
      const isLast = index === words.length - 1
      const isConquer = word.includes('Conquer')
      
      return (
        <React.Fragment key={index}>
          <span className={isConquer ? "ca-grad" : ""}>
            {word}
            {!isLast && "."}
          </span>
          {!isLast && <br />}
        </React.Fragment>
      )
    })
  }

  const fullText = "Code. Compete. Conquer."

  return (
    <h1 className={`text-6xl md:text-7xl lg:text-8xl font-black mb-6 tracking-tight leading-[1.1] relative ${isDarkMode ? 'text-white' : 'text-slate-900'}`}>
      {/* Invisible placeholder to reserve exact space and prevent layout shifts */}
      <span className="inline-block invisible pointer-events-none select-none" aria-hidden="true">
        {renderTitle(fullText)}
      </span>
      
      {/* Actual animated typing text */}
      <span className="inline-block absolute top-0 left-0">
        {renderTitle(displayText)}
        <span className="inline-block w-[4px] h-[0.9em] bg-blue-400 ml-2 animate-blink align-middle" />
      </span>
    </h1>
  )
})

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function Landing() {
  const [hasCompletedOnce, setHasCompletedOnce] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(true)
  const { user, logout, login } = useAuth()
  const navigate = useNavigate()
  
  // Handle OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    const username = params.get('username')
    const oauthSuccess = params.get('oauth_success')
    const oauthError = params.get('oauth_error')
    
    if (oauthError) {
      console.error('OAuth error:', oauthError)
      // Clear URL parameters
      window.history.replaceState({}, document.title, window.location.pathname)
      return
    }
    
    if (oauthSuccess === 'true' && token && username) {
      // Store token
      localStorage.setItem('token', token)
      
      // Login user
      login({ username }, token)
      
      // Clear URL parameters
      window.history.replaceState({}, document.title, window.location.pathname)
      
      // Redirect to home page (not dashboard)
      navigate('/home')
    }
  }, [login, navigate])
  return (
    <div className={`min-h-screen text-slate-200 font-sans overflow-x-hidden relative bg-[#010204]`}>
      
      {/* ── Ultra-Premium Ambient Lighting (Vantablack Minimalist) ── */}
      <div className="absolute top-0 left-0 w-full h-screen overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-[20%] -right-[10%] w-[50%] h-[60%] bg-[#06b6d4] opacity-[0.05] blur-[150px] rounded-full " />
        <div className="absolute top-[40%] -left-[10%] w-[60%] h-[60%] bg-[#3b82f6] opacity-[0.06] blur-[150px] rounded-full " />
        <div className="absolute top-[20%] left-[20%] w-[40%] h-[40%] bg-[#a855f7] opacity-[0.03] blur-[150px] rounded-full " />
      </div>

      <AnimatedGlobe3D />




      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <Navbar />

      {/* ── Hero ───────────────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-32 overflow-hidden min-h-[90vh] flex items-center">
        <div className="relative max-w-7xl mx-auto px-6 w-full z-10 flex flex-col lg:flex-row items-center justify-between gap-16">
          
          {/* Left Side: Typography */}
          <div className="text-left max-w-2xl flex-shrink-0 relative z-10">
            <div className={`inline-flex items-center gap-2 ${isDarkMode ? 'bg-[#101018] border-blue-500/20' : 'bg-white border-blue-400/30'} border rounded-full px-4 py-1.5 mb-8 transition-all duration-1000 ${hasCompletedOnce ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 -translate-y-4 scale-95'}  hover:border-blue-500/40 hover:shadow-lg hover:shadow-blue-500/20 group cursor-default`} style={{ transitionDelay: '400ms' }}>
              <span className="w-2 h-2 rounded-full bg-[#3b82f6] absolute" />
              <span className="w-2 h-2 rounded-full bg-[#3b82f6] relative" />
              <span className={`text-sm font-medium group-hover:text-blue-300 transition-colors ${isDarkMode ? 'text-[#60a5fa]' : 'text-blue-600'}`}>Join 10,000+ Active Coders</span>
            </div>

            <HeroTitle isDarkMode={isDarkMode} onCompleteOnce={() => setHasCompletedOnce(true)} />

            <div className={`transition-all duration-1000 ${hasCompletedOnce ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`} style={{ transitionDelay: '600ms' }}>
              <p className={`text-xl max-w-xl mb-12 leading-relaxed hover:text-slate-300 transition-colors duration-300 ${isDarkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                The real-time multiplayer coding platform. Battle against developers worldwide,
                master algorithms, and climb the leaderboard with AI-generated challenges.
              </p>

              <div className="flex items-center justify-start gap-6 flex-wrap mb-16">
                {/* Primary CTA */}
                <Link to={user ? "/dashboard" : "/register"}
                  className="relative px-12 py-4 font-bold text-white rounded-full transition-all duration-500 active:scale-95 group overflow-hidden shadow-2xl">
                  <div className="absolute inset-0 rounded-full bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-600 bg-[length:200%_100%] " />
                  <div className="absolute -inset-[2px] rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 to-cyan-500 opacity-0 group-hover:opacity-100 blur-sm transition-all duration-500 " />
                  <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full transition-transform duration-700 ease-out" />
                  <div className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500" style={{ boxShadow: 'inset 0 0 20px rgba(59, 130, 246, 0.5)' }} />
                  <span className="relative z-10 flex items-center gap-3 tracking-wide text-lg">
                    {user ? "Go to Dashboard" : "Start Coding Free"}
                  </span>
                </Link>

                {/* Secondary CTA — jumps to the explainer-video generator below */}
                <a href="#learn-more" className="relative px-12 py-4 font-bold text-white rounded-full transition-all duration-500 active:scale-95 group overflow-hidden border border-white/[0.1] bg-[#0A0A10]/50 hover:bg-[#0A0A10]/80">
                  <span className="relative z-10 flex items-center gap-3 tracking-wide text-lg">
                    Learn More
                  </span>
                </a>
              </div>
            </div>
          </div>

          <div className={`mt-20 lg:mt-0 w-full lg:w-[600px] flex-shrink-0 transition-all duration-1000 ${hasCompletedOnce ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-12 scale-95'}`} style={{ transitionDelay: '800ms', perspective: '1000px' }}>
             <div style={{ transform: 'rotateY(-10deg) rotateX(5deg)' }} className=" transition-transform duration-700 hidden md:block">
               <LiveTerminal />
             </div>
          </div>
        </div>
      </section>

      {/* ── Stats ──────────────────────────────────────────────────────────── */}
      <section className="py-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600/5 via-transparent to-cyan-600/5 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 relative">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 divide-x divide-white/[0.05]">
            {STATS.map((s, i) => <AnimatedStat key={i} value={s.value} label={s.label} />)}
          </div>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────────────────────── */}
      <section id="features" className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <FeaturesSection />
        </div>
      </section>

      {/* ── Learn More (AI explainer videos) ───────────────────────────────── */}
      {/* relative z-10 is load-bearing: the fixed three.js globe canvas paints
          above unpositioned content and swallows clicks, so without it the topic
          input and Generate button cannot be used. The hero does the same. */}
      <section id="learn-more" className="relative z-10 py-24 scroll-mt-24">
        <div className="max-w-7xl mx-auto px-6">
          <LearnMore />
        </div>
      </section>

      {/* ── Game Modes ─────────────────────────────────────────────────────── */}
      <section id="modes" className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <GameModesSection />
        </div>
      </section>

      {/* ── Testimonials ───────────────────────────────────────────────────── */}
      <section id="testimonials" className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <TestimonialsSection />
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────────── */}
      <section className="py-24">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <div className="relative p-12 md:p-16 bg-[#0A0A10]/80 border border-white/[0.05] rounded-3xl overflow-hidden group transition-all duration-500 cursor-default shadow-[0_0_50px_rgba(0,0,0,0.5)]">
            <div className="absolute inset-0 bg-gradient-to-br from-[#3b82f6]/10 to-[#06b6d4]/10 pointer-events-none transition-all duration-500 group-hover:from-[#3b82f6]/20 group-hover:to-[#06b6d4]/20" />

            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-6 tracking-tight transition-all duration-500 ">Ready to Level Up?</h2>
              <p className="text-slate-300 mb-10 max-w-xl mx-auto text-lg transition-all duration-500 group-hover:text-slate-200">
                Join thousands of developers improving their skills through competitive programming.
              </p>
              <Link to="/register"
                className="inline-block px-8 py-4 bg-[#3b82f6] hover:bg-[#2563eb] text-white font-bold rounded-xl transition-all duration-300 shadow-xl shadow-blue-500/25 hover:shadow-blue-500/50 active:scale-95 ">
                Join Now
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <Footer />
    </div>
  )
}

