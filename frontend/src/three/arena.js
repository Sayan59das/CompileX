// The arena: a gaming laptop that somebody is typing code on.
//
// Built from primitives, no model files, in the design language of a modern gaming machine: a dark gunmetal chassis with
// crisp edges, a raised rear section with exhaust vents behind the hinge, an RGB light bar under the front edge that washes
// the surface, a per-key RGB keyboard with highlighted WASD, a thin-bezel screen, and an LED dot-matrix panel and a glowing
// mark on the lid. The marks are CompileX's own.
//
// The screen is a canvas texture redrawn as characters are typed (the same solution in Python, C++, Java, JavaScript and C in
// turn), every typed character presses a real key, and the scroll steers the pose: it opens as you arrive, turns to the
// match, swings round to show its back, and shuts at the end. Nothing here touches React: `createArena` takes a canvas and
// returns a handle.

import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'

export const CHAPTERS = 4

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const lerp = (a, b, t) => a + (b - a) * t
const smooth = (t) => t * t * (3 - 2 * t)
const easeOutBack = (t) => { const c = 1.5; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2) }

// How the machine is posed in each chapter: turn (ry), tip toward you (rx), how far the lid is open (0 shut, 1 open), scale.
const POSES = [
  { ry: -0.5, rx: 0.12, lid: 1, s: 1 },      // arena: three-quarter front, screen toward the page
  { ry: 0.28, rx: 0.06, lid: 1, s: 1 },      // a match: almost square to the screen
  { ry: 2.55, rx: 0.07, lid: 0.94, s: 1 },   // modes: turned round, the lid, vents and light bar toward you
  { ry: 3.4, rx: -0.86, lid: 0.03, s: 1.12 }, // start: lid shut, seen from above and behind so the lid reads upright
]

// The same solution in five languages: what is typed on the screen.
const SNIPPETS = [
  { lang: 'Python', file: 'main.py', code: [
    'def best_window(n, k, prices):',
    '    cur = 0',
    '    for i in range(k):',
    '        cur += prices[i]',
    '    best = cur',
    '    for i in range(k, n):',
    '        cur += prices[i] - prices[i - k]',
    '        best = max(best, cur)',
    '    return best',
  ] },
  { lang: 'C++', file: 'main.cpp', code: [
    'long long bestWindow(int n, int k, vector<int>& prices) {',
    '    long long cur = 0;',
    '    for (int i = 0; i < k; i++) cur += prices[i];',
    '    long long best = cur;',
    '    for (int i = k; i < n; i++) {',
    '        cur += prices[i] - prices[i - k];',
    '        best = max(best, cur);',
    '    }',
    '    return best;',
    '}',
  ] },
  { lang: 'Java', file: 'Solution.java', code: [
    'public long bestWindow(int n, int k, int[] prices) {',
    '    long cur = 0;',
    '    for (int i = 0; i < k; i++) cur += prices[i];',
    '    long best = cur;',
    '    for (int i = k; i < n; i++) {',
    '        cur += prices[i] - prices[i - k];',
    '        best = Math.max(best, cur);',
    '    }',
    '    return best;',
    '}',
  ] },
  { lang: 'JavaScript', file: 'main.js', code: [
    'function bestWindow(n, k, prices) {',
    '  let cur = 0;',
    '  for (let i = 0; i < k; i++) cur += prices[i];',
    '  let best = cur;',
    '  for (let i = k; i < n; i++) {',
    '    cur += prices[i] - prices[i - k];',
    '    best = Math.max(best, cur);',
    '  }',
    '  return best;',
    '}',
  ] },
  { lang: 'C', file: 'main.c', code: [
    'long long best_window(int n, int k, int *prices) {',
    '    long long cur = 0;',
    '    for (int i = 0; i < k; i++) cur += prices[i];',
    '    long long best = cur;',
    '    for (int i = k; i < n; i++) {',
    '        cur += prices[i] - prices[i - k];',
    '        if (cur > best) best = cur;',
    '    }',
    '    return best;',
    '}',
  ] },
]
// which language a chapter starts on
const CHAPTER_LANG = [0, 0, 1, 2]

// the lighting: cyan (you) and violet (the rival), nothing else
const RGB = ['#3DE0FF', '#8B6CFF']
const RGB3 = RGB.map((h) => new THREE.Color(h))

// ── the screen ─────────────────────────────────────────────────────────────
const W = 1280
const H = 800
// the screen is drawn at 80% of its layout size: it is re-uploaded on every keystroke, and smaller uploads keep frames smooth
const SCREEN_SCALE = 0.8
const TOKEN = /(\/\/.*|#.*)|(\b(?:def|for|in|return|if|else|while|public|static|function|let|const|new)\b)|(\b(?:int|long|char|void|vector|double)\b)|(\b(?:range|max|min|Math)\b)|(\b\d+\b)|(\w+|\s+|.)/g
const COL = { comment: '#737373', keyword: '#A387FF', type: '#5AA2FF', builtin: '#3DE0FF', number: '#FFC857', plain: '#F2F2F2' }
const MONO = '"JetBrains Mono Variable", "JetBrains Mono", monospace'

function drawScreen(ctx, snip, chars, caretOn, resultT) {
  ctx.setTransform(SCREEN_SCALE, 0, 0, SCREEN_SCALE, 0, 0)
  const lines = snip.code.join('\n').slice(0, chars).split('\n')
  ctx.fillStyle = '#050608'
  ctx.fillRect(0, 0, W, H)

  // title bar
  ctx.fillStyle = '#0B0C10'
  ctx.fillRect(0, 0, W, 58)
  ;[34, 60, 86].forEach((x) => { ctx.fillStyle = '#2A2C33'; ctx.beginPath(); ctx.arc(x, 29, 7, 0, Math.PI * 2); ctx.fill() })
  ctx.fillStyle = '#14161C'
  ctx.fillRect(128, 12, 250, 46)
  ctx.fillStyle = '#3DE0FF'
  ctx.fillRect(128, 56, 250, 2)
  ctx.font = `22px ${MONO}`
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#F2F2F2'
  ctx.fillText(snip.file, 150, 36)
  ctx.textAlign = 'right'
  ctx.fillStyle = '#737373'
  ctx.fillText(snip.lang, W - 28, 30)
  ctx.textAlign = 'left'

  // code
  const lh = 41
  const top = 104
  ctx.font = `27px ${MONO}`
  const cw = ctx.measureText('M').width
  const cur = lines.length - 1
  ctx.fillStyle = 'rgba(61,224,255,0.06)'
  ctx.fillRect(100, top + cur * lh - lh / 2, W - 100, lh)
  lines.forEach((line, i) => {
    const y = top + i * lh
    ctx.textAlign = 'right'
    ctx.fillStyle = i === cur ? '#8C8C8C' : '#4A4A4A'
    ctx.fillText(String(i + 1), 78, y)
    ctx.textAlign = 'left'
    let x = 118
    for (const m of line.matchAll(TOKEN)) {
      ctx.fillStyle = m[1] ? COL.comment : m[2] ? COL.keyword : m[3] ? COL.type : m[4] ? COL.builtin : m[5] ? COL.number : COL.plain
      ctx.fillText(m[0], x, y)
      x += m[0].length * cw
    }
    if (i === cur && caretOn) {
      ctx.fillStyle = '#3DE0FF'
      ctx.fillRect(x + 1, y - 17, 3, 34)
    }
  })

  // result panel
  const py = 612
  ctx.fillStyle = '#0B0C10'
  ctx.fillRect(40, py, W - 80, 112)
  ctx.strokeStyle = resultT > 0 ? 'rgba(53,242,160,0.5)' : 'rgba(255,255,255,0.14)'
  ctx.lineWidth = 2
  ctx.strokeRect(41, py + 1, W - 82, 110)
  const passes = Math.floor(clamp(resultT, 0, 1) * 10)
  ctx.font = '600 30px "Sora Variable", "Onest Variable", system-ui, sans-serif'
  ctx.fillStyle = resultT > 0 ? '#35F2A0' : '#737373'
  ctx.fillText(resultT > 0 ? `${passes} / 10 tests passed` : 'Tests: waiting for a solution', 72, py + 38)
  for (let i = 0; i < 10; i++) {
    ctx.fillStyle = i < passes ? '#35F2A0' : 'rgba(255,255,255,0.14)'
    ctx.fillRect(72 + i * 38, py + 70, 30, 12)
  }
  const info = [['Time', 'O(n)'], ['Space', 'O(1)'], ['Confidence', 'High']]
  info.forEach(([k, v], i) => {
    const x = 560 + i * 224
    ctx.font = `22px ${MONO}`
    ctx.fillStyle = '#737373'
    ctx.fillText(k.toUpperCase(), x, py + 38)
    ctx.font = `600 30px ${MONO}`
    ctx.fillStyle = resultT >= 1 ? '#3DE0FF' : '#333333'
    ctx.fillText(resultT >= 1 ? v : '...', x, py + 78)
  })

  // status bar
  ctx.fillStyle = '#0B0C10'
  ctx.fillRect(0, 752, W, 48)
  ctx.font = `20px ${MONO}`
  ctx.fillStyle = '#35F2A0'
  ctx.fillText('●', 28, 776)
  ctx.fillStyle = '#8C8C8C'
  ctx.fillText(`${snip.lang}  ·  harness locked`, 52, 776)
  ctx.textAlign = 'right'
  ctx.fillText(`Ln ${cur + 1}, Col ${lines[cur].length + 1}   UTF-8`, W - 28, 776)
  ctx.textAlign = 'left'
}

// ── the LED dot matrix on the lid ──────────────────────────────────────────
const GLYPHS = {
  C: [' ### ', '#   #', '#    ', '#    ', '#    ', '#   #', ' ### '],
  O: [' ### ', '#   #', '#   #', '#   #', '#   #', '#   #', ' ### '],
  M: ['#   #', '## ##', '# # #', '# # #', '#   #', '#   #', '#   #'],
  P: ['#### ', '#   #', '#   #', '#### ', '#    ', '#    ', '#    '],
  I: [' ### ', '  #  ', '  #  ', '  #  ', '  #  ', '  #  ', ' ### '],
  L: ['#    ', '#    ', '#    ', '#    ', '#    ', '#    ', '#####'],
  E: ['#####', '#    ', '#    ', '#### ', '#    ', '#    ', '#####'],
  X: ['#   #', '#   #', ' # # ', '  #  ', ' # # ', '#   #', '#   #'],
  '<': ['   # ', '  #  ', ' #   ', '#    ', ' #   ', '  #  ', '   # '],
  '>': [' #   ', '  #  ', '   # ', '    #', '   # ', '  #  ', ' #   '],
  '/': ['    #', '    #', '   # ', '  #  ', ' #   ', '#    ', '#    '],
  1: ['  #  ', ' ##  ', '  #  ', '  #  ', '  #  ', '  #  ', ' ### '],
  0: [' ### ', '#   #', '#  ##', '# # #', '##  #', '#   #', ' ### '],
  ' ': ['     ', '     ', '     ', '     ', '     ', '     ', '     '],
}
const MCOLS = 40
const MROWS = 22
const CELL = 12

function drawMatrix(ctx, t) {
  const lit = new Uint8Array(MCOLS * MROWS)
  const stamp = (text, row, shift) => {
    const L = text.length * 6
    for (let c = 0; c < MCOLS; c++) {
      const v = (((c + shift) % L) + L) % L
      const g = GLYPHS[text[Math.floor(v / 6)]]
      const gx = v % 6
      if (!g || gx > 4) continue
      for (let gy = 0; gy < 7; gy++) if (g[gy][gx] === '#') lit[(row + gy) * MCOLS + c] = 1
    }
  }
  stamp('COMPILEX  ', 3, Math.floor(t * 7))
  stamp('</> 10/10  ', 12, -Math.floor(t * 5))
  ctx.clearRect(0, 0, MCOLS * CELL, MROWS * CELL)
  for (let r = 0; r < MROWS; r++) {
    for (let c = 0; c < MCOLS; c++) {
      ctx.fillStyle = lit[r * MCOLS + c] ? '#E6FAFF' : 'rgba(255,255,255,0.07)'
      ctx.fillRect(c * CELL + 2, r * CELL + 2, CELL - 4, CELL - 4)
    }
  }
}

// ── textures ───────────────────────────────────────────────────────────────
function canvasTexture(w, h, draw, repeat = false) {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  draw(c.getContext('2d'), w, h)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping
  return t
}

// a seamless horizontal RGB strip, for the light bar and the keyboard's underglow
const rgbStrip = () => canvasTexture(512, 4, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, w, 0)
  ;[RGB[0], RGB[1], RGB[0]].forEach((c, i) => gr.addColorStop(i / 2, c))
  g.fillStyle = gr
  g.fillRect(0, 0, w, h)
}, true)

// the light the bar throws on the surface in front of it
const floorWash = () => canvasTexture(512, 256, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, w, 0)
  gr.addColorStop(0, 'rgba(61,224,255,0)')
  gr.addColorStop(0.25, RGB[0])
  gr.addColorStop(0.75, RGB[1])
  gr.addColorStop(1, 'rgba(139,108,255,0)')
  g.fillStyle = gr
  g.fillRect(0, 0, w, h)
  g.globalCompositeOperation = 'destination-in'
  const fade = g.createLinearGradient(0, 0, 0, h)
  fade.addColorStop(0, 'rgba(0,0,0,0.38)')
  fade.addColorStop(0.3, 'rgba(0,0,0,0.1)')
  fade.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = fade
  g.fillRect(0, 0, w, h)
})

const poolTexture = () => canvasTexture(256, 256, (g) => {
  const r = g.createRadialGradient(128, 128, 0, 128, 128, 128)
  r.addColorStop(0, 'rgba(139,108,255,0.14)')
  r.addColorStop(0.45, 'rgba(61,224,255,0.04)')
  r.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = r
  g.fillRect(0, 0, 256, 256)
})

const ventTexture = () => canvasTexture(512, 32, (g, w, h) => {
  g.fillStyle = '#0d0e12'
  g.fillRect(0, 0, w, h)
  for (let x = 10; x < w - 10; x += 22) {
    g.fillStyle = '#000'
    g.fillRect(x, 6, 16, h - 12)
    g.fillStyle = 'rgba(255,255,255,0.06)'
    g.fillRect(x, 6, 16, 2)
  }
})

const portTexture = () => canvasTexture(256, 16, (g, w, h) => {
  g.fillStyle = '#121318'
  g.fillRect(0, 0, w, h)
  g.fillStyle = '#000'
  ;[[16, 22], [50, 14], [76, 14], [104, 30], [150, 10], [176, 10]].forEach(([x, pw]) => g.fillRect(x, 4, pw, h - 8))
})

const markTexture = () => canvasTexture(256, 256, (g) => {
  g.lineWidth = 22
  g.lineCap = 'round'
  g.lineJoin = 'round'
  g.shadowBlur = 26
  g.shadowColor = '#3DE0FF'
  g.strokeStyle = '#CFF7FF'
  g.beginPath(); g.moveTo(112, 74); g.lineTo(56, 128); g.lineTo(112, 182); g.stroke()
  g.shadowColor = '#9B7BFF'
  g.strokeStyle = '#E2D8FF'
  g.beginPath(); g.moveTo(144, 74); g.lineTo(200, 128); g.lineTo(144, 182); g.stroke()
})

// ── the keyboard layout: six justified rows ────────────────────────────────
function keyLayout(z0) {
  const GAP = 0.032
  const TARGET = 3.34
  const rows = [
    { d: 0.13, w: Array(13).fill(1) },
    { d: 0.19, w: [...Array(13).fill(1), 1.6] },
    { d: 0.19, w: [1.5, ...Array(12).fill(1), 1.1] },
    { d: 0.19, w: [1.8, ...Array(11).fill(1), 2.1] },
    { d: 0.19, w: [2.3, ...Array(10).fill(1), 2.3] },
    { d: 0.19, w: [1.2, 1.2, 1.2, 5.6, 1.2, 1.2, 1.2] },
  ]
  const keys = []
  let z = z0
  rows.forEach((row, ri) => {
    z += row.d / 2
    const sum = row.w.reduce((a, b) => a + b, 0)
    const unit = (TARGET - (row.w.length - 1) * GAP) / sum
    let x = -TARGET / 2
    row.w.forEach((w, ki) => {
      const kw = w * unit
      keys.push({ x: x + kw / 2, z, w: kw, d: row.d, row: ri, col: ki, last: ki === row.w.length - 1 })
      x += kw + GAP
    })
    z += row.d / 2 + GAP
  })
  return keys
}

export function createArena(canvas) {
  const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setClearColor(0x000000, 0)
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.1
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 80)
  camera.position.set(0, 0.5, 12.5)

  const pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.environmentIntensity = 0.5

  // lights: cyan from one side, violet from the other, a soft key from the front
  const rimA = new THREE.DirectionalLight(0x3de0ff, 2.0)
  rimA.position.set(-5, 3, -3)
  const rimB = new THREE.DirectionalLight(0x8b6cff, 1.8)
  rimB.position.set(5, 2.5, -3)
  const keyLight = new THREE.DirectionalLight(0xffffff, 1.0)
  keyLight.position.set(1.5, 5, 6)
  scene.add(rimA, rimB, keyLight)

  // ── the machine ──────────────────────────────────────────────────────────
  const laptop = new THREE.Group()
  const BASE_W = 3.6
  const BASE_D = 2.6
  const BASE_H = 0.15
  const LID_H = 2.35
  const LID_T = 0.06
  const HINGE_Z = -BASE_D / 2 + 0.36 // the rear section with the vents sits behind the hinge

  const gunmetal = new THREE.MeshStandardMaterial({ color: 0x24262d, metalness: 0.85, roughness: 0.34 })
  const dark = new THREE.MeshStandardMaterial({ color: 0x0b0c10, metalness: 0.5, roughness: 0.55 })

  const base = new THREE.Mesh(new RoundedBoxGeometry(BASE_W, BASE_H, BASE_D, 3, 0.022), gunmetal)
  base.position.y = BASE_H / 2
  laptop.add(base)

  // raised rear section
  const rear = new THREE.Mesh(new RoundedBoxGeometry(BASE_W, 0.08, 0.36, 3, 0.02), gunmetal)
  rear.position.set(0, BASE_H + 0.03, -BASE_D / 2 + 0.18)
  laptop.add(rear)

  // exhaust vents on the back and ports on the side
  const vents = new THREE.Mesh(new THREE.PlaneGeometry(3.1, 0.15), new THREE.MeshBasicMaterial({ map: ventTexture() }))
  vents.rotation.y = Math.PI
  vents.position.set(0, 0.12, -BASE_D / 2 - 0.002)
  laptop.add(vents)
  const ports = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.09), new THREE.MeshBasicMaterial({ map: portTexture() }))
  ports.rotation.y = Math.PI / 2
  ports.position.set(BASE_W / 2 + 0.002, 0.075, -0.2)
  laptop.add(ports)

  // keyboard well: a steady cyan underglow that shows between the keys
  const deck = new THREE.Mesh(new THREE.PlaneGeometry(3.44, 1.36), new THREE.MeshBasicMaterial({ color: 0x0a3a48 }))
  deck.rotation.x = -Math.PI / 2
  deck.position.set(0, BASE_H + 0.002, -0.2)
  laptop.add(deck)

  const pad = new THREE.Mesh(new RoundedBoxGeometry(1.25, 0.012, 0.62, 2, 0.006), new THREE.MeshStandardMaterial({ color: 0x2c2e36, metalness: 0.6, roughness: 0.25 }))
  pad.position.set(0, BASE_H + 0.004, 0.92)
  laptop.add(pad)

  // keys: dark caps, and a lit legend on each that runs an RGB wave
  const layout = keyLayout(-0.86)
  const KEY_H = 0.05
  const caps = new THREE.InstancedMesh(new RoundedBoxGeometry(1, KEY_H, 1, 2, 0.012), new THREE.MeshStandardMaterial({ color: 0x15161b, metalness: 0.3, roughness: 0.45 }), layout.length)
  const legends = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), layout.length)
  const press = new Float32Array(layout.length)
  const dummy = new THREE.Object3D()
  const white = new THREE.Color(0xffffff)
  const tmpColor = new THREE.Color()
  const keyIndex = { letters: [], space: 0, enter: 0, wasd: new Set() }
  layout.forEach((k, i) => {
    if (k.row >= 1 && k.row <= 4 && !k.last && k.col > 0) keyIndex.letters.push(i)
    if (k.row === 5 && k.w > 1) keyIndex.space = i
    if (k.row === 3 && k.last) keyIndex.enter = i
    if ((k.row === 2 && k.col === 2) || (k.row === 3 && k.col >= 1 && k.col <= 3)) keyIndex.wasd.add(i)
  })
  function placeKeys() {
    layout.forEach((k, i) => {
      const y = BASE_H + 0.02 + KEY_H / 2 - press[i] * 0.022
      dummy.position.set(k.x, y, k.z)
      dummy.rotation.set(0, 0, 0)
      dummy.scale.set(k.w, 1, k.d)
      dummy.updateMatrix()
      caps.setMatrixAt(i, dummy.matrix)
      dummy.position.set(k.x - k.w * 0.22, y + KEY_H / 2 + 0.001, k.z - k.d * 0.18)
      dummy.rotation.set(-Math.PI / 2, 0, 0)
      dummy.scale.set(Math.min(k.w, 0.2) * 0.34, k.d * 0.32, 1)
      dummy.updateMatrix()
      legends.setMatrixAt(i, dummy.matrix)
    })
    caps.instanceMatrix.needsUpdate = true
    legends.instanceMatrix.needsUpdate = true
  }
  function colourKeys(t) {
    layout.forEach((k, i) => {
      const glow = keyIndex.wasd.has(i) ? 0.95 : 0.5 + 0.12 * Math.sin(k.x * 0.9 - t * 0.6)
      tmpColor.copy(RGB3[0]).multiplyScalar(glow).lerp(white, press[i] * 0.85)
      legends.setColorAt(i, tmpColor)
    })
    legends.instanceColor.needsUpdate = true
  }
  placeKeys()
  colourKeys(0)
  laptop.add(caps, legends)

  // the light bar: along the front and both sides, under the edge
  const barTex = rgbStrip()
  const barMat = new THREE.MeshBasicMaterial({ map: barTex, toneMapped: false })
  const barFront = new THREE.Mesh(new THREE.BoxGeometry(BASE_W - 0.1, 0.028, 0.028), barMat)
  barFront.position.set(0, 0.012, BASE_D / 2 - 0.004)
  const barL = new THREE.Mesh(new THREE.BoxGeometry(0.028, 0.028, BASE_D - 0.4), barMat)
  barL.position.set(-BASE_W / 2 + 0.004, 0.012, 0.18)
  const barR = barL.clone()
  barR.position.x = BASE_W / 2 - 0.004
  laptop.add(barFront, barL, barR)

  // the wash it throws on the surface, and a soft pool under the machine
  const wash = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 1.5), new THREE.MeshBasicMaterial({ map: floorWash(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }))
  wash.rotation.x = -Math.PI / 2
  wash.position.set(0, -0.012, BASE_D / 2 + 0.72)
  laptop.add(wash)
  const pool = new THREE.Mesh(new THREE.PlaneGeometry(8, 8), new THREE.MeshBasicMaterial({ map: poolTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }))
  pool.rotation.x = -Math.PI / 2
  pool.position.y = -0.02
  laptop.add(pool)

  // hinge
  const hinge = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 3.2, 20), dark)
  hinge.rotation.z = Math.PI / 2
  hinge.position.set(0, BASE_H + 0.05, HINGE_Z)
  laptop.add(hinge)

  // lid: hinged ahead of the rear section. Upright, its inner face looks toward +z.
  const lid = new THREE.Group()
  lid.position.set(0, BASE_H + 0.05, HINGE_Z)
  laptop.add(lid)

  const lidBody = new THREE.Mesh(new RoundedBoxGeometry(BASE_W, LID_H, LID_T, 3, 0.02), gunmetal)
  lidBody.position.set(0, LID_H / 2, -LID_T / 2)
  lid.add(lidBody)

  const bezel = new THREE.Mesh(new THREE.PlaneGeometry(BASE_W - 0.05, LID_H - 0.05), new THREE.MeshBasicMaterial({ color: 0x030304 }))
  bezel.position.set(0, LID_H / 2, 0.001)
  lid.add(bezel)

  const camDot = new THREE.Mesh(new THREE.CircleGeometry(0.014, 16), new THREE.MeshBasicMaterial({ color: 0x1a1c24 }))
  camDot.position.set(0, LID_H - 0.035, 0.002)
  lid.add(camDot)

  const screenCanvas = document.createElement('canvas')
  screenCanvas.width = Math.round(W * SCREEN_SCALE)
  screenCanvas.height = Math.round(H * SCREEN_SCALE)
  const sctx = screenCanvas.getContext('2d')
  const screenTex = new THREE.CanvasTexture(screenCanvas)
  screenTex.colorSpace = THREE.SRGBColorSpace
  screenTex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy())
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(3.44, 2.15), new THREE.MeshBasicMaterial({ map: screenTex, toneMapped: false }))
  screen.position.set(0, 0.14 + 2.15 / 2, 0.002)
  lid.add(screen)

  // the back of the lid: an LED dot matrix and a glowing mark
  const matrixCanvas = document.createElement('canvas')
  matrixCanvas.width = MCOLS * CELL
  matrixCanvas.height = MROWS * CELL
  const mctx = matrixCanvas.getContext('2d')
  const matrixTex = new THREE.CanvasTexture(matrixCanvas)
  matrixTex.colorSpace = THREE.SRGBColorSpace
  const matrix = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.6 * (MROWS / MCOLS)), new THREE.MeshBasicMaterial({ map: matrixTex, transparent: true, toneMapped: false }))
  matrix.rotation.set(0, Math.PI, -0.42)
  matrix.position.set(0.78, 1.05, -LID_T - 0.002)
  lid.add(matrix)

  const mark = new THREE.Mesh(new THREE.PlaneGeometry(0.66, 0.66), new THREE.MeshBasicMaterial({ map: markTexture(), transparent: true, toneMapped: false, depthWrite: false }))
  mark.rotation.y = Math.PI
  mark.position.set(-0.95, 1.6, -LID_T - 0.003)
  lid.add(mark)

  // the screen lights the keyboard
  const screenLight = new THREE.PointLight(0x3de0ff, 8, 5, 2)
  screenLight.position.set(0, LID_H / 2, 0.9)
  lid.add(screenLight)

  const stage = new THREE.Group()
  stage.add(laptop)
  scene.add(stage)

  // ── typing ───────────────────────────────────────────────────────────────
  const typing = { lang: 0, chars: 0, acc: 0, pause: 0, done: false, doneT: 0 }
  function restart(lang) {
    typing.lang = lang
    typing.chars = 0
    typing.acc = 0
    typing.pause = 0.25
    typing.done = false
    typing.doneT = 0
  }
  function hit(ch) {
    let i
    if (ch === ' ') i = keyIndex.space
    else if (ch === '\n') i = keyIndex.enter
    else i = keyIndex.letters[(ch.charCodeAt(0) * 7 + typing.chars) % keyIndex.letters.length]
    press[i] = 1
  }
  restart(0)

  // ── state driven from outside ────────────────────────────────────────────
  const state = {
    c: 0, cs: 0,
    xs: new Array(CHAPTERS).fill(0), ys: new Array(CHAPTERS).fill(0), scales: new Array(CHAPTERS).fill(1), opacities: new Array(CHAPTERS).fill(1),
    kick: 0, spin: 0,
    mx: 0, my: 0, smx: 0, smy: 0,
    time: 0, intro: reduce ? 1 : 0, chapter: 0, lastOpacity: -1,
  }

  // The sharpness the scene is drawn at. It starts at 1.25 and only ever goes down, one step at a time, when frames are coming slowly
  // (see the end of `frame`), so a weak GPU gets a slightly softer picture instead of a stuttering one.
  let quality = 1.25
  function resize() {
    const w = canvas.clientWidth || window.innerWidth
    const h = canvas.clientHeight || window.innerHeight
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality))
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    // a tall, narrow screen needs the camera further back to keep the machine in view
    const halfTan = Math.tan((camera.fov * Math.PI) / 360)
    camera.position.z = Math.max(12.5, 5.6 / (2 * halfTan * camera.aspect))
    camera.updateProjectionMatrix()
  }
  resize()
  const ro = new ResizeObserver(resize)
  ro.observe(canvas)

  const onMove = (e) => {
    state.mx = (e.clientX / window.innerWidth) * 2 - 1
    state.my = -((e.clientY / window.innerHeight) * 2 - 1)
  }
  window.addEventListener('pointermove', onMove, { passive: true })

  // the screen text uses web fonts: redraw once they are in
  let fontsReady = false
  let dirty = true
  if (document.fonts?.load) {
    Promise.all([
      document.fonts.load('27px "JetBrains Mono Variable"'),
      document.fonts.load('600 30px "Sora Variable"'),
    ]).then(() => { fontsReady = true; dirty = true }).catch(() => { fontsReady = true; dirty = true })
  } else fontsReady = true

  let raf = 0
  let last = performance.now()
  let caret = true
  let lastChapterSwitch = 0
  let matrixT = -1
  let colourT = -1
  let frames = 0
  let slowFrames = 0
  function frame(now) {
    raf = requestAnimationFrame(frame)
    if (document.hidden) { last = now; return }
    const gap = now - last
    const dt = Math.min(0.05, gap / 1000)
    last = now

    // Adaptive sharpness: after the first second (shaders compiling are always slow), count frames that took over ~28 ms (under 36 fps).
    // If most of the last 60 were slow, draw fewer pixels from now on.
    frames++
    if (frames > 60) {
      if (gap > 28) slowFrames++
      if ((frames - 60) % 60 === 0) {
        if (slowFrames > 30 && quality > 0.8) { quality = Math.max(0.75, quality - 0.25); resize() }
        slowFrames = 0
      }
    }
    if (!reduce) state.time += dt
    const t = state.time

    // arrival, then chapter smoothing
    if (state.intro < 1) state.intro = Math.min(1, state.intro + dt / 3)
    state.cs = reduce ? state.c : state.cs + (state.c - state.cs) * (1 - Math.exp(-dt * 2.8))

    // the screen follows the chapter: each one starts on a different language
    const chap = Math.round(state.cs)
    if (chap !== state.chapter && t - lastChapterSwitch > 0.35) {
      state.chapter = chap
      lastChapterSwitch = t
      restart(CHAPTER_LANG[chap])
      dirty = true
    }

    // typing
    const snip = SNIPPETS[typing.lang]
    if (!typing.done && state.intro > 0.45) {
      if (typing.pause > 0) typing.pause -= dt
      else {
        typing.acc += dt * (reduce ? 400 : 24 + Math.sin(t * 2.3) * 6)
        const text = snip.code.join('\n')
        while (typing.acc >= 1 && typing.chars < text.length) {
          typing.acc -= 1
          const ch = text[typing.chars]
          typing.chars++
          hit(ch)
          dirty = true
          if (ch === '\n') { typing.pause = 0.16; break }
        }
        if (typing.chars >= text.length) { typing.done = true; typing.doneT = 0 }
      }
    } else if (typing.done) {
      typing.doneT += dt
      // The result fades in over the first ~1.6 s and then stops changing: redraw the screen only while it moves (it used to be every frame for 5 s)
      if (typing.doneT < 1.7) dirty = true
      if (typing.doneT > 5.2) { restart((typing.lang + 1) % SNIPPETS.length); dirty = true }
    }
    const nowCaret = Math.floor(t * 2) % 2 === 0
    if (nowCaret !== caret) { caret = nowCaret; dirty = true }
    if (dirty && fontsReady) {
      drawScreen(sctx, SNIPPETS[typing.lang], typing.chars, caret, typing.done ? clamp((typing.doneT - 0.2) / 1.4, 0, 1) : 0)
      screenTex.needsUpdate = true
      dirty = false
    }

    // the lid's dot matrix scrolls at about 12 frames a second
    if (t - matrixT > 1 / 12 || matrixT < 0) {
      matrixT = t
      drawMatrix(mctx, t)
      matrixTex.needsUpdate = true
    }

    // lighting: the light bar drifts slowly, the keys breathe, pressed keys flash and spring back
    barTex.offset.x = -t * 0.03
    let anyPressed = false
    for (let i = 0; i < press.length; i++) {
      if (press[i] > 0) { press[i] = Math.max(0, press[i] - dt * 4.5); anyPressed = true }
    }
    if (anyPressed) placeKeys()
    // the glow wave is slow: recolouring and re-uploading every key's colour 20 times a second looks the same as 60 and costs a third as much
    if (anyPressed || t - colourT > 1 / 20) { colourKeys(t); colourT = t }

    // pose, blended between chapters
    const ci = clamp(state.cs, 0, CHAPTERS - 1)
    const k0 = Math.floor(ci)
    const k1 = Math.min(k0 + 1, CHAPTERS - 1)
    const f = smooth(ci - k0)
    const a = POSES[k0]
    const b = POSES[k1]
    const intro = easeOutBack(clamp(state.intro * 1.15, 0, 1))
    const open = lerp(a.lid, b.lid, f) * clamp(easeOutBack(clamp((state.intro - 0.12) * 1.5, 0, 1)), 0, 1.06)
    lid.rotation.x = lerp(Math.PI / 2, -0.3, clamp(open, 0, 1.04))
    screenLight.intensity = 8 * clamp(open, 0, 1)

    state.smx += (state.mx - state.smx) * (1 - Math.exp(-dt * 2))
    state.smy += (state.my - state.smy) * (1 - Math.exp(-dt * 2))
    state.spin += state.kick
    state.kick *= Math.exp(-dt * 3)
    state.spin *= Math.exp(-dt * 1.1)

    const x = lerp(state.xs[k0], state.xs[k1], f)
    const y = lerp(state.ys[k0], state.ys[k1], f)
    const s = lerp(a.s, b.s, f) * lerp(state.scales[k0], state.scales[k1], f) * (0.55 + 0.45 * intro)
    stage.position.set(x, y + Math.sin(t * 0.6) * 0.045 - 0.95 * s, 0)
    stage.scale.setScalar(s)
    stage.rotation.order = 'YXZ'
    stage.rotation.y = lerp(a.ry, b.ry, f) + state.spin + state.smx * 0.2 + (1 - intro) * -0.9 + Math.sin(t * 0.25) * 0.03
    stage.rotation.x = lerp(a.rx, b.rx, f) - state.smy * 0.09

    // visibility of the whole canvas per chapter
    const op = lerp(state.opacities[k0], state.opacities[k1], f)
    if (Math.abs(op - state.lastOpacity) > 0.004) { canvas.style.opacity = op.toFixed(3); state.lastOpacity = op }

    // nobody can see a canvas that is faded out (between chapters the machine is hidden), so do not spend the GPU on it
    if (op > 0.01) renderer.render(scene, camera)
  }
  raf = requestAnimationFrame(frame)

  return {
    /** The chapter coordinate: 0 is the first pose, 3.0 the last, 1.5 is halfway between poses 1 and 2. */
    setChapter(c) { state.c = clamp(c, 0, CHAPTERS - 1) },
    /** Per chapter: where the machine sits (x, y in world units), how big it is, and how visible. */
    setLayout({ offsets, ys, scales, opacities }) {
      if (offsets) state.xs = offsets.slice(0, CHAPTERS)
      if (ys) state.ys = ys.slice(0, CHAPTERS)
      if (scales) state.scales = scales.slice(0, CHAPTERS)
      if (opacities) state.opacities = opacities.slice(0, CHAPTERS)
    },
    /** Feed scroll distance in pixels: the machine swings with the page. */
    pulse(dy) { if (!reduce) state.kick = clamp(state.kick + dy * 0.00006, -0.012, 0.012) },
    dispose() {
      cancelAnimationFrame(raf)
      ro.disconnect()
      window.removeEventListener('pointermove', onMove)
      scene.traverse((o) => {
        if (o.geometry) o.geometry.dispose()
        if (o.material) {
          const ms = Array.isArray(o.material) ? o.material : [o.material]
          ms.forEach((m) => { m.map?.dispose(); m.dispose() })
        }
      })
      screenTex.dispose()
      matrixTex.dispose()
      pmrem.dispose()
      renderer.dispose()
      renderer.forceContextLoss()
    },
  }
}
