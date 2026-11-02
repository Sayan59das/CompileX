import React, { useId } from 'react'

// The flat SVG version of the coder scene. Only used when WebGL is unavailable.
// A small looping scene for the app's backgrounds: someone at a desk writes code, the tests fail,
// they stop and think with a hand on the chin, fix the line, and the tests pass.
// Pure SVG with CSS keyframes on a 12 second loop, so it costs almost nothing to run.
// With reduced motion it rests on the solved frame.

const T = 12

const R = (d) => `rotate(${d}deg)`

// keyframes from [percent, value] pairs
function kf(name, pts, prop = 'transform') {
  const m = new Map()
  pts.forEach(([p, v]) => m.set(Math.round(p * 100) / 100, v))
  const body = [...m.entries()].sort((a, b) => a[0] - b[0]).map(([p, v]) => `${p}%{${prop}:${v}}`).join('')
  return `@keyframes ${name}{${body}}`
}

// quick alternation between a and b inside [from, to]: typing, tapping
function tap(from, to, step, a, b) {
  const out = [[from, a]]
  let flip = true
  for (let t = from + step; t < to - 0.05; t += step) { out.push([t, flip ? b : a]); flip = !flip }
  out.push([to, a])
  return out
}

const anim = (cls, ease = 'ease-in-out') => `.${cls}{animation:${cls} ${T}s ${ease} infinite}`

// The code on screen: indent and width of each line, and its two colours. Line 3 is the one that breaks.
const LINES = [
  { ind: 0, w: 84, c: ['#9B7BFF', '#F2F2F2'] },
  { ind: 8, w: 60, c: ['#737373', '#3DE0FF'] },
  { ind: 8, w: 100, c: ['#9B7BFF', '#FFC857'] },
  { ind: 16, w: 72, c: ['#F2F2F2', '#3DE0FF'] },
  { ind: 8, w: 108, c: ['#737373', '#9B7BFF'] },
  { ind: 8, w: 48, c: ['#9B7BFF', '#F2F2F2'] },
]
const LX = 308 // where the code starts
const LY = (i) => 61 + i * 11
const START = (i) => 3 + i * 4.2

const CSS = [
  // lines type in one after another; line 3 is cleared and typed again during the fix
  ...LINES.map((_, i) => kf(`cs-l${i}`, i === 3
    ? [[0, 'scaleX(0)'], [START(i), 'scaleX(0)'], [START(i) + 3, 'scaleX(1)'], [61, 'scaleX(1)'], [61.6, 'scaleX(0)'], [66.5, 'scaleX(1)'], [100, 'scaleX(1)']]
    : [[0, 'scaleX(0)'], [START(i), 'scaleX(0)'], [START(i) + 3, 'scaleX(1)'], [100, 'scaleX(1)']])),
  ...LINES.map((_, i) => anim(`cs-l${i}`, 'linear')),
  kf('cs-code', [[0, 1], [93, 1], [97, 0], [100, 0]], 'opacity'), anim('cs-code', 'linear'),
  kf('cs-errline', [[0, 0], [31, 0], [32, 1], [61, 1], [62, 0], [100, 0]], 'opacity'), anim('cs-errline', 'linear'),
  kf('cs-caret', [[0, 0], [41.9, 0], [42, 1], [44, 0], [46, 1], [48, 0], [50, 1], [52, 0], [54, 1], [56, 0], [58, 1], [60, 0], [100, 0]], 'opacity'), anim('cs-caret', 'step-end'),
  kf('cs-errbar', [[0, 0], [31, 0], [31.8, 1], [61, 1], [61.8, 0], [100, 0]], 'opacity'), anim('cs-errbar', 'linear'),
  kf('cs-runbar', [[0, 0], [66.5, 0], [67, 1], [68.5, 1], [69, 0], [100, 0]], 'opacity'), anim('cs-runbar', 'linear'),
  kf('cs-okbar', [[0, 0], [68.5, 0], [69.2, 1], [93, 1], [96, 0], [100, 0]], 'opacity'), anim('cs-okbar', 'linear'),
  kf('cs-glow-err', [[0, 0], [31, 0], [33, 0.6], [61, 0.6], [64, 0], [100, 0]], 'opacity'), anim('cs-glow-err'),
  kf('cs-glow-ok', [[0, 0], [68.5, 0], [71, 0.55], [90, 0.55], [95, 0], [100, 0]], 'opacity'), anim('cs-glow-ok'),
  kf('cs-rim', [[0, '#3DE0FF'], [31, '#3DE0FF'], [32.5, '#FF5C7A'], [61, '#FF5C7A'], [63, '#3DE0FF'], [68.5, '#3DE0FF'], [70, '#35F2A0'], [90, '#35F2A0'], [95, '#3DE0FF'], [100, '#3DE0FF']], 'stroke'), anim('cs-rim', 'linear'),

  // the person
  kf('cs-body', [[0, R(0)], [30, R(0)], [32, R(-5)], [38, R(-5)], [42, R(-2)], [57, R(-2)], [60, R(2.5)], [67, R(2.5)], [71, R(-1)], [76, R(0)], [100, R(0)]]), anim('cs-body'),
  kf('cs-head', [[0, R(0)], [30, R(0)], [32, R(-10)], [38, R(-9)], [42, R(-4)], [50, R(-6.5)], [57, R(-4)], [60, R(3)], [67, R(3)], [70, R(-2)], [73, R(5)], [76, R(-1)], [79, R(4)], [82, R(0)], [100, R(0)]]), anim('cs-head'),
  kf('cs-fu', [[0, R(0)], [30, R(0)], [32, R(-8)], [38, R(-8)], [42, R(-17.5)], [57, R(-17.5)], [61, R(0)], [100, R(0)]]), anim('cs-fu'),
  kf('cs-ff', [[0, R(0)], ...tap(2, 29.5, 1.1, R(0), R(-5)), [30, R(0)], [32, R(-18)], [38, R(-18)], [42, R(-93)], [45, R(-86)], [48, R(-93)], [51, R(-86)], [54, R(-93)], [57, R(-93)], [61, R(0)], ...tap(61.5, 67.5, 0.7, R(0), R(-6)), [100, R(0)]]), anim('cs-ff'),
  kf('cs-bu', [[0, R(0)], [30, R(0)], [32, R(-6)], [38, R(-6)], [42, R(0)], [100, R(0)]]), anim('cs-bu'),
  kf('cs-bf', [[0, R(0)], ...tap(2.55, 29.5, 1.1, R(0), R(-5)), [30, R(0)], [32, R(-14)], [38, R(-14)], [42, R(0)], ...tap(43, 56, 2.6, R(0), R(-3)), [57, R(0)], ...tap(61.85, 67.5, 0.7, R(0), R(-6)), [100, R(0)]]), anim('cs-bf'),
  kf('cs-eye', [[0, 'scaleY(1)'], [9.6, 'scaleY(1)'], [10.1, 'scaleY(0.1)'], [10.6, 'scaleY(1)'], [49.6, 'scaleY(1)'], [50.1, 'scaleY(0.1)'], [50.6, 'scaleY(1)'], [85.6, 'scaleY(1)'], [86.1, 'scaleY(0.1)'], [86.6, 'scaleY(1)'], [100, 'scaleY(1)']]), anim('cs-eye', 'linear'),
  kf('cs-brow', [[0, 'translateY(0) rotate(0deg)'], [31, 'translateY(0) rotate(0deg)'], [32, 'translateY(-2.5px) rotate(-4deg)'], [39, 'translateY(-2.5px) rotate(-4deg)'], [42, 'translateY(0.5px) rotate(10deg)'], [58, 'translateY(0.5px) rotate(10deg)'], [61, 'translateY(0) rotate(0deg)'], [100, 'translateY(0) rotate(0deg)']]), anim('cs-brow'),
  kf('cs-m-smile', [[0, 1], [31, 1], [31.5, 0], [67.5, 0], [68.5, 1], [100, 1]], 'opacity'), anim('cs-m-smile', 'linear'),
  kf('cs-m-o', [[0, 0], [31, 0], [31.5, 1], [40, 1], [41, 0], [100, 0]], 'opacity'), anim('cs-m-o', 'linear'),
  kf('cs-m-flat', [[0, 0], [40, 0], [41, 1], [67.5, 1], [68.5, 0], [100, 0]], 'opacity'), anim('cs-m-flat', 'linear'),

  // what they are thinking
  `@keyframes cs-b-err{0%,30.5%{transform:scale(0);opacity:0}32.5%{transform:scale(1.15);opacity:1}34%,39%{transform:scale(1);opacity:1}41%,100%{transform:scale(.6);opacity:0}}`, anim('cs-b-err', 'ease-out'),
  `@keyframes cs-b-q{0%,41%{transform:scale(0);opacity:0}43%{transform:scale(1.1);opacity:1}44.5%,57%{transform:scale(1);opacity:1}59%,100%{transform:scale(.6);opacity:0}}`, anim('cs-b-q', 'ease-out'),
  `@keyframes cs-b-ok{0%,69%{transform:scale(0);opacity:0}71%{transform:scale(1.15);opacity:1}72.5%,88%{transform:scale(1);opacity:1}91%,100%{transform:scale(.6);opacity:0}}`, anim('cs-b-ok', 'ease-out'),

  `.cs-steam,.cs-steam2{animation:cs-steam 3.2s ease-in-out infinite}.cs-steam2{animation-delay:1.6s}`,
  `@keyframes cs-steam{0%{transform:translateY(4px);opacity:0}40%{opacity:.5}100%{transform:translateY(-10px);opacity:0}}`,

  `@media (prefers-reduced-motion: reduce){.cs *{animation:none!important}.cs .cs-okbar,.cs .cs-b-ok,.cs .cs-glow-ok{opacity:1}}`,
].join('\n')

// transform origins, in the drawing's own units
const O = (x, y) => ({ transformOrigin: `${x}px ${y}px` })

const SKIN = '#D7A985'
const SKIN_BACK = '#C99A78'
const MONO = 'JetBrains Mono Variable, ui-monospace, monospace'

export default function CoderSceneFlat({ className = '', decorative = false }) {
  const uid = useId().replace(/:/g, '')
  const g = (n) => `cs-${n}-${uid}`
  const a11y = decorative
    ? { 'aria-hidden': true, focusable: 'false' }
    : { role: 'img', 'aria-label': 'Someone at a desk writes code, the tests fail, they think it through, fix the line and the tests pass' }

  return (
    <svg viewBox="0 0 480 320" className={`cs ${className}`} {...a11y}>
      <style>{CSS}</style>
      <defs>
        <radialGradient id={g('cyan')}><stop offset="0" stopColor="#3DE0FF" stopOpacity="0.28" /><stop offset="1" stopColor="#3DE0FF" stopOpacity="0" /></radialGradient>
        <radialGradient id={g('red')}><stop offset="0" stopColor="#FF5C7A" stopOpacity="0.5" /><stop offset="1" stopColor="#FF5C7A" stopOpacity="0" /></radialGradient>
        <radialGradient id={g('mint')}><stop offset="0" stopColor="#35F2A0" stopOpacity="0.45" /><stop offset="1" stopColor="#35F2A0" stopOpacity="0" /></radialGradient>
      </defs>

      {/* light thrown by the screen: cyan, red while failing, green when passing */}
      <ellipse cx="370" cy="104" rx="160" ry="118" fill={`url(#${g('cyan')})`} />
      <ellipse className="cs-glow-err" cx="370" cy="104" rx="160" ry="118" fill={`url(#${g('red')})`} opacity="0" />
      <ellipse className="cs-glow-ok" cx="370" cy="104" rx="160" ry="118" fill={`url(#${g('mint')})`} opacity="0" />

      <line x1="30" y1="296" x2="470" y2="296" stroke="#232323" strokeWidth="2" />

      {/* chair */}
      <rect x="104" y="108" width="12" height="98" rx="6" fill="#1D1D1D" />
      <rect x="104" y="203" width="86" height="9" rx="4.5" fill="#242424" />
      <rect x="143" y="212" width="7" height="52" fill="#1D1D1D" />
      <path d="M110 292 L146 264 L182 292" fill="none" stroke="#1D1D1D" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />

      {/* desk */}
      <rect x="196" y="178" width="276" height="8" rx="2" fill="#202020" />
      <rect x="196" y="178" width="276" height="1.5" fill="#333" />
      <rect x="200" y="186" width="7" height="110" fill="#191919" />
      <rect x="458" y="186" width="7" height="110" fill="#191919" />

      {/* monitor */}
      <rect x="368" y="148" width="10" height="30" fill="#1B1B1B" />
      <rect x="346" y="174" width="54" height="4" rx="2" fill="#262626" />
      <rect x="290" y="46" width="170" height="104" rx="7" fill="#0D0D0D" stroke="#303030" strokeWidth="1.5" />
      <rect x="297" y="53" width="156" height="90" rx="3" fill="#050608" />
      <rect x="447" y="40" width="12" height="12" rx="1" fill="#FFC857" opacity="0.8" transform="rotate(8 453 46)" />

      <g className="cs-code">
        {LINES.map((l, i) => (
          <g key={i}>
            <rect x="301" y={LY(i)} width="3" height="5" rx="1" fill="#2A2A2A" />
            <g className={`cs-l${i}`} style={O(LX + l.ind, 0)}>
              <rect x={LX + l.ind} y={LY(i)} width={l.w * 0.35} height="5" rx="2.5" fill={l.c[0]} />
              <rect x={LX + l.ind + l.w * 0.35 + 4} y={LY(i)} width={l.w * 0.65} height="5" rx="2.5" fill={l.c[1]} opacity="0.85" />
            </g>
          </g>
        ))}
      </g>
      <g className="cs-errline" opacity="0">
        <rect x="297" y={LY(3) - 3} width="156" height="11" fill="#FF5C7A" fillOpacity="0.16" />
        <rect x="297" y={LY(3) - 3} width="2.5" height="11" fill="#FF5C7A" />
      </g>
      <rect className="cs-caret" x={LX + 16 + 72 + 6} y={LY(3) - 2} width="1.6" height="9" fill="#3DE0FF" opacity="0" />

      {/* status bar: idle, failing, running, passing */}
      <rect x="297" y="131" width="156" height="12" fill="#101010" />
      <text x="303" y="139.5" fontSize="7" fontFamily={MONO} fill="#737373">solution.py</text>
      <g className="cs-errbar" opacity="0">
        <rect x="297" y="131" width="156" height="12" fill="#FF5C7A" />
        <text x="303" y="139.5" fontSize="7" fontFamily={MONO} fontWeight="700" fill="#1A0309">IndexError: line 4</text>
      </g>
      <g className="cs-runbar" opacity="0">
        <rect x="297" y="131" width="156" height="12" fill="#262626" />
        <text x="303" y="139.5" fontSize="7" fontFamily={MONO} fill="#D4D4D4">running tests...</text>
      </g>
      <g className="cs-okbar" opacity="0">
        <rect x="297" y="131" width="156" height="12" fill="#35F2A0" />
        <text x="303" y="139.5" fontSize="7" fontFamily={MONO} fontWeight="700" fill="#03140C">5/5 tests passed</text>
      </g>

      {/* keyboard, mouse, mug */}
      <rect x="226" y="173" width="82" height="5" rx="2" fill="#2A2A2A" />
      <rect x="226" y="173" width="82" height="1.2" fill="#3DE0FF" opacity="0.45" />
      <ellipse cx="322" cy="175.5" rx="6" ry="2.8" fill="#2A2A2A" />
      <rect x="424" y="156" width="15" height="22" rx="3" fill="#2A2A2A" />
      <path d="M439 161 q8 0 8 6.5 q0 6.5 -8 6.5" fill="none" stroke="#2A2A2A" strokeWidth="3" />
      <path className="cs-steam" d="M428 150 q3 -4 0 -8 q-3 -4 0 -8" fill="none" stroke="#8C8C8C" strokeWidth="1.5" strokeLinecap="round" />
      <path className="cs-steam2" d="M435 150 q3 -4 0 -8 q-3 -4 0 -8" fill="none" stroke="#8C8C8C" strokeWidth="1.5" strokeLinecap="round" />

      {/* legs */}
      <rect x="128" y="188" width="100" height="15" rx="7.5" fill="#1B1E26" />
      <rect x="214" y="192" width="15" height="96" rx="7" fill="#1B1E26" />
      <ellipse cx="230" cy="290" rx="16" ry="6" fill="#121212" />

      <g className="cs-body" style={O(146, 203)}>
        {/* far arm, behind the body: stays on the keys */}
        <g className="cs-bu" style={O(150, 124)}>
          <path d="M150 124 L176 168" stroke="#232733" strokeWidth="11" strokeLinecap="round" />
          <g className="cs-bf" style={O(176, 168)}>
            <path d="M176 168 L232 170" stroke="#232733" strokeWidth="11" strokeLinecap="round" />
            <circle cx="235" cy="170" r="6" fill={SKIN_BACK} />
          </g>
        </g>

        {/* torso, hood */}
        <path d="M118 204 L126 134 Q130 112 150 112 L160 112 Q175 114 173 134 L170 204 Z" fill="#2B3040" />
        <path d="M127 122 Q124 107 140 105 L151 112 Z" fill="#252937" />

        <g className="cs-head" style={O(158, 112)}>
          <rect x="151" y="97" width="12" height="17" rx="5" fill={SKIN_BACK} />
          <circle cx="164" cy="84" r="18" fill={SKIN} />
          <path d="M146 84 Q146 62 166 62 Q182 62 184 76 Q174 70 162 74 Q154 77 152 92 Z" fill="#161616" />
          <path className="cs-rim" d="M174 69 A18 18 0 0 1 175 98.5" fill="none" stroke="#3DE0FF" strokeWidth="1.5" opacity="0.55" />
          <path className="cs-brow" style={O(170, 75)} d="M170 75.5 q4 -1.6 9 -0.6" fill="none" stroke="#161616" strokeWidth="2" strokeLinecap="round" />
          <ellipse className="cs-eye" style={O(176, 83)} cx="176" cy="83" rx="1.8" ry="2" fill="#161616" />
          <path className="cs-m-smile" d="M179 93 q-3 2.2 -6.5 1" fill="none" stroke="#7E4E36" strokeWidth="1.5" strokeLinecap="round" />
          <ellipse className="cs-m-o" cx="177" cy="93.5" rx="2" ry="2.6" fill="#5A2F22" opacity="0" />
          <path className="cs-m-flat" d="M179 93.5 l-6 0" fill="none" stroke="#7E4E36" strokeWidth="1.5" strokeLinecap="round" opacity="0" />
          {/* headphones */}
          <path d="M154 79 Q150 59 169 59" fill="none" stroke="#3DE0FF" strokeWidth="3" strokeLinecap="round" />
          <rect x="149" y="77" width="10" height="16" rx="4.5" fill="#3DE0FF" />
          <rect x="151.5" y="80" width="5" height="10" rx="2.5" fill="#0B6E80" />
        </g>

        {/* near arm: types, lifts off the keys at the error, goes to the chin to think */}
        <g className="cs-fu" style={O(160, 126)}>
          <path d="M160 126 L188 170" stroke="#2F3446" strokeWidth="11" strokeLinecap="round" />
          <g className="cs-ff" style={O(188, 170)}>
            <path d="M188 170 L248 172" stroke="#2F3446" strokeWidth="11" strokeLinecap="round" />
            <circle cx="251" cy="172" r="6" fill={SKIN} />
          </g>
        </g>
      </g>

      {/* thought bubbles */}
      <g className="cs-b-err" style={O(202, 54)} opacity="0">
        <circle cx="202" cy="40" r="13" fill="#FF5C7A" />
        <rect x="200.5" y="31" width="3" height="11" rx="1.5" fill="#1A0309" />
        <circle cx="202" cy="47" r="1.8" fill="#1A0309" />
      </g>
      <g className="cs-b-q" style={O(202, 56)} opacity="0">
        <circle cx="191" cy="62" r="2.5" fill="#262626" stroke="#8C8C8C" strokeWidth="1" />
        <circle cx="204" cy="38" r="14" fill="#262626" stroke="#8C8C8C" strokeWidth="1.5" />
        <text x="204" y="44" textAnchor="middle" fontSize="17" fontWeight="700" fill="#F2F2F2" fontFamily="Onest Variable, system-ui, sans-serif">?</text>
      </g>
      <g className="cs-b-ok" style={O(202, 54)} opacity="0">
        <circle cx="202" cy="40" r="13" fill="#35F2A0" />
        <path d="M196 40 l4 4 l8 -9" fill="none" stroke="#03140C" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  )
}
