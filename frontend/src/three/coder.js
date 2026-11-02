// The coder: a small 3D scene of someone at a desk writing code.
//
// They type, the tests fail (red light, a "!", they lean back), they stop and think with a hand on the chin, fix the one
// broken line, run the tests again and everything passes (green light, a check, a nod). It loops every 12 seconds.
//
// Built from primitives, no model files. The monitor is a canvas texture that really types the code, deletes the bad
// characters and types the fix. The arms are two-bone IK, so the hands follow targets (keys, up, chin) instead of
// canned poses. Nothing here touches React: `createCoder` takes a canvas and returns a handle.

import * as THREE from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'

const LOOP = 12 // seconds

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const lerp = (a, b, t) => a + (b - a) * t
const smooth = (t) => t * t * (3 - 2 * t)
const ramp = (p, a, b) => smooth(clamp((p - a) / (b - a), 0, 1))
const easeOutBack = (t) => { const c = 1.6; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2) }

// value of a keyframed track at p (percent of the loop), eased between keys
function track(p, pts) {
  if (p <= pts[0][0]) return pts[0][1]
  for (let i = 1; i < pts.length; i++) {
    if (p <= pts[i][0]) {
      const [p0, v0] = pts[i - 1]
      const [p1, v1] = pts[i]
      return lerp(v0, v1, smooth((p - p0) / (p1 - p0)))
    }
  }
  return pts[pts.length - 1][1]
}

const COL = { cyan: 0x3de0ff, red: 0xff5c7a, mint: 0x35f2a0, amber: 0xffc857, violet: 0x9b7bff }

// ---- the code on the monitor -------------------------------------------------------------------------------------------

const FULL = [
  'def max_gain(prices):',
  '    best = 0',
  '    low = prices[0]',
  '    for i in range(1, len(prices) + 1):',
  '        best = max(best, prices[i] - low)',
  '        low = min(low, prices[i])',
  '    return best',
]
const BUG_LINE = 3        // the loop runs one step past the end of the list
const BUG_TAIL = ' + 1):' // what is deleted
const FIX_TAIL = '):'     // what replaces it
const BUG_BASE = '    for i in range(1, len(prices)'
const TOTAL_CHARS = FULL.reduce((n, l) => n + l.length + 1, 0)

// which lines are visible, as strings, at p
function codeAt(p) {
  const n = clamp(Math.floor(((p - 3) / 26) * TOTAL_CHARS), 0, TOTAL_CHARS)
  const out = []
  let left = n
  for (let i = 0; i < FULL.length; i++) {
    if (left <= 0 && i > 0) break
    const l = FULL[i]
    out.push(l.slice(0, Math.max(0, left)))
    left -= l.length + 1
    if (left < 0) break
  }
  if (n === 0) return { lines: [], caret: null }
  // the fix: backspace the bad tail, type the good one
  if (p >= 61 && out.length > BUG_LINE) {
    if (p < 63) {
      const k = Math.floor(((p - 61) / 2) * (BUG_TAIL.length + 1))
      out[BUG_LINE] = FULL[BUG_LINE].slice(0, FULL[BUG_LINE].length - clamp(k, 0, BUG_TAIL.length))
    } else {
      const k = p < 63.5 ? 0 : Math.floor(((p - 63.5) / 2) * (FIX_TAIL.length + 1))
      out[BUG_LINE] = BUG_BASE + FIX_TAIL.slice(0, clamp(k, 0, FIX_TAIL.length))
    }
  }
  let caretLine = out.length - 1
  if (p >= 60 && p < 66) caretLine = BUG_LINE
  return { lines: out, caret: { line: caretLine, col: out[caretLine].length } }
}

// the stream of key presses: every typed character, then the backspaces, then the fix
const STREAM = FULL.map((l) => l + '\n').join('')
function eventsAt(p) {
  let n = 0
  if (p >= 3) n = clamp(Math.floor(((p - 3) / 26) * TOTAL_CHARS), 0, TOTAL_CHARS)
  if (p >= 61) n += clamp(Math.floor(((p - 61) / 2) * (BUG_TAIL.length + 1)), 0, BUG_TAIL.length)
  if (p >= 63.5) n += clamp(Math.floor(((p - 63.5) / 2) * (FIX_TAIL.length + 1)), 0, FIX_TAIL.length)
  return n
}

const KW = /^(def|for|in|return|if|else|while)$/
const BI = /^(range|len|print|sum|max|min)$/

function drawScreen(ctx, W, H, p, time, fontOk) {
  const FS = 30, LH = 40, CW = FS * 0.6
  const err = ramp(p, 31, 32) * (1 - ramp(p, 61, 62))
  const running = p >= 66.5 && p < 69
  const passed = p >= 69
  const font = fontOk ? `${FS}px "JetBrains Mono Variable", ui-monospace, monospace` : `${FS}px ui-monospace, Consolas, monospace`

  ctx.fillStyle = '#05070A'
  ctx.fillRect(0, 0, W, H)

  // title bar
  ctx.fillStyle = '#101216'
  ctx.fillRect(0, 0, W, 46)
  ;['#FF5C7A', '#FFC857', '#35F2A0'].forEach((c, i) => { ctx.fillStyle = c; ctx.globalAlpha = 0.8; ctx.beginPath(); ctx.arc(26 + i * 24, 23, 6, 0, 7); ctx.fill() })
  ctx.globalAlpha = 1
  ctx.fillStyle = '#05070A'
  ctx.fillRect(120, 8, 190, 38)
  ctx.fillStyle = '#3DE0FF'
  ctx.fillRect(120, 8, 190, 2)
  ctx.font = '600 18px "JetBrains Mono Variable", ui-monospace, monospace'
  ctx.fillStyle = '#E6E6E6'
  ctx.fillText('solution.py', 138, 33)
  ctx.fillStyle = '#737373'
  ctx.fillText('Python', W - 108, 33)
  // the Run button: the mouse clicks it twice, once before the failure and once after the fix
  const clicking = (p >= 29.9 && p < 31) || (p >= 66.4 && p < 67.4)
  ctx.fillStyle = clicking ? '#35F2A0' : '#0F1217'
  ctx.beginPath(); ctx.roundRect(W - 250, 9, 120, 30, 7); ctx.fill()
  ctx.strokeStyle = '#35F2A0'; ctx.lineWidth = 2
  ctx.beginPath(); ctx.roundRect(W - 250, 9, 120, 30, 7); ctx.stroke()
  ctx.fillStyle = clicking ? '#03140C' : '#35F2A0'
  ctx.font = '600 17px "JetBrains Mono Variable", ui-monospace, monospace'
  ctx.fillText('\u25b6  Run', W - 232, 31)

  // editor
  const { lines, caret } = codeAt(p)
  const top = 58, gx = 80
  ctx.font = font
  ctx.textBaseline = 'alphabetic'
  if (err > 0.01) {
    ctx.fillStyle = `rgba(255,92,122,${0.14 * err})`
    ctx.fillRect(0, top + BUG_LINE * LH - 6, W, LH)
    ctx.fillStyle = `rgba(255,92,122,${err})`
    ctx.fillRect(0, top + BUG_LINE * LH - 6, 5, LH)
  }
  lines.forEach((text, li) => {
    const y = top + li * LH + FS
    ctx.fillStyle = '#4A4F57'
    ctx.textAlign = 'right'
    ctx.fillText(String(li + 1), 56, y)
    ctx.textAlign = 'left'
    const re = /([A-Za-z_]\w*)|(\d+)|(\s+)|(.)/g
    let m, col = 0, afterDef = false
    while ((m = re.exec(text))) {
      const t = m[0]
      let c = '#8C8C8C'
      if (m[1]) c = KW.test(t) ? '#9B7BFF' : BI.test(t) ? '#3DE0FF' : afterDef ? '#35F2A0' : '#E6E6E6'
      else if (m[2]) c = '#FFC857'
      else if (m[3]) c = '#000'
      if (m[1]) afterDef = t === 'def'
      ctx.fillStyle = c
      if (!m[3]) ctx.fillText(t, gx + col * CW, y)
      col += t.length
    }
    if (li === BUG_LINE && err > 0.01) {
      // squiggle under the bad expression
      const x0 = gx + (BUG_BASE.length - 'len(prices'.length) * CW
      const x1 = gx + FULL[BUG_LINE].length * CW - CW
      ctx.strokeStyle = `rgba(255,92,122,${err})`
      ctx.lineWidth = 2
      ctx.beginPath()
      for (let x = x0; x <= x1; x += 6) ctx.lineTo(x, y + 8 + ((x / 6) % 2 === 0 ? 0 : 3))
      ctx.stroke()
    }
  })
  if (caret && Math.floor(time * 2) % 2 === 0) {
    ctx.fillStyle = '#3DE0FF'
    ctx.fillRect(gx + caret.col * CW + 1, top + caret.line * LH - 2, 3, FS + 8)
  }

  // test panel
  const py = 352
  ctx.fillStyle = '#0A0C10'
  ctx.fillRect(0, py, W, H - py - 44)
  ctx.fillStyle = '#1B1F26'
  ctx.fillRect(0, py, W, 2)
  ctx.font = '600 17px "JetBrains Mono Variable", ui-monospace, monospace'
  ctx.fillStyle = '#737373'
  ctx.fillText('OUTPUT', 28, py + 34)
  ctx.font = '22px "JetBrains Mono Variable", ui-monospace, monospace'
  let msg = 'Press Run to check your solution', mc = '#737373'
  if (p >= 31 && p < 66.5) { msg = 'IndexError: list index out of range   solution.py:4'; mc = '#FF5C7A' }
  else if (running) { msg = 'Running 5 tests...'; mc = '#D4D4D4' }
  else if (passed) { msg = 'All tests passed'; mc = '#35F2A0' }
  ctx.fillStyle = mc
  ctx.fillText(msg, 28, py + 76)

  for (let i = 0; i < 5; i++) {
    const x = 28 + i * 190, y = py + 108, w = 172, h = 58
    let st = 'idle'
    if (p >= 31 && p < 66.5) st = 'fail'
    else if (running) st = 'run'
    else if (passed && p >= 69 + i * 1.3) st = 'pass'
    else if (passed) st = 'run'
    const c = st === 'fail' ? '#FF5C7A' : st === 'pass' ? '#35F2A0' : st === 'run' ? '#FFC857' : '#3A3F47'
    ctx.fillStyle = '#0F1217'
    ctx.beginPath(); ctx.roundRect(x, y, w, h, 10); ctx.fill()
    ctx.strokeStyle = c; ctx.globalAlpha = st === 'idle' ? 0.6 : 0.9; ctx.lineWidth = 2
    ctx.beginPath(); ctx.roundRect(x, y, w, h, 10); ctx.stroke(); ctx.globalAlpha = 1
    ctx.fillStyle = '#B3B3B3'
    ctx.font = '20px "JetBrains Mono Variable", ui-monospace, monospace'
    ctx.fillText(`test ${i + 1}`, x + 16, y + 36)
    ctx.fillStyle = c
    ctx.font = '600 26px "JetBrains Mono Variable", ui-monospace, monospace'
    ctx.textAlign = 'right'
    ctx.fillText(st === 'fail' ? '✗' : st === 'pass' ? '✓' : st === 'run' ? '…' : '–', x + w - 16, y + 38)
    ctx.textAlign = 'left'
  }

  // status bar
  const sb = err > 0.5 ? '#FF5C7A' : passed ? '#35F2A0' : '#12151A'
  ctx.fillStyle = sb
  ctx.fillRect(0, H - 44, W, 44)
  ctx.font = '600 19px "JetBrains Mono Variable", ui-monospace, monospace'
  ctx.fillStyle = err > 0.5 ? '#1A0309' : passed ? '#03140C' : '#737373'
  ctx.fillText(err > 0.5 ? '1 error  ·  solution.py' : passed ? '5/5 tests passed' : running ? 'running' : 'ready', 24, H - 14)

  // the pointer, while the hand is on the mouse
  if ((p >= 28.8 && p < 32) || (p >= 65.6 && p < 68.5)) {
    const k = p < 40 ? clamp((p - 28.8) / 1.0, 0, 1) : clamp((p - 65.6) / 0.8, 0, 1)
    const cx = lerp(W - 420, W - 205, smooth(k)), cy = lerp(210, 28, smooth(k))
    ctx.fillStyle = '#FFFFFF'; ctx.strokeStyle = '#000000'; ctx.lineWidth = 2
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx, cy + 26); ctx.lineTo(cx + 7, cy + 20); ctx.lineTo(cx + 13, cy + 32); ctx.lineTo(cx + 18, cy + 29); ctx.lineTo(cx + 12, cy + 18); ctx.lineTo(cx + 21, cy + 17); ctx.closePath(); ctx.fill(); ctx.stroke()
  }

  // clear the screen for the next loop
  const fade = ramp(p, 94, 98)
  if (fade > 0) { ctx.fillStyle = `rgba(5,7,10,${fade})`; ctx.fillRect(0, 0, W, H) }
}

// ---- small helpers for building ----------------------------------------------------------------------------------------

function glyphTexture(kind) {
  const c = document.createElement('canvas')
  c.width = c.height = 256
  const g = c.getContext('2d')
  const fill = kind === 'err' ? '#FF5C7A' : kind === 'ok' ? '#35F2A0' : '#1A1A1A'
  g.fillStyle = fill
  g.beginPath(); g.arc(128, 128, 112, 0, 7); g.fill()
  if (kind === 'q') { g.strokeStyle = '#9A9A9A'; g.lineWidth = 8; g.stroke() }
  g.fillStyle = kind === 'err' ? '#1A0309' : kind === 'ok' ? '#03140C' : '#F2F2F2'
  g.strokeStyle = g.fillStyle
  g.lineCap = 'round'; g.lineJoin = 'round'
  if (kind === 'err') {
    g.beginPath(); g.roundRect(114, 60, 28, 88, 12); g.fill()
    g.beginPath(); g.arc(128, 182, 15, 0, 7); g.fill()
  } else if (kind === 'ok') {
    g.lineWidth = 26
    g.beginPath(); g.moveTo(72, 132); g.lineTo(112, 172); g.lineTo(188, 88); g.stroke()
  } else {
    g.font = '700 150px Onest Variable, system-ui, sans-serif'
    g.textAlign = 'center'; g.textBaseline = 'middle'
    g.fillText('?', 128, 138)
  }
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

function blobTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64)
  grd.addColorStop(0, 'rgba(0,0,0,0.85)')
  grd.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = grd
  g.fillRect(0, 0, 128, 128)
  return new THREE.CanvasTexture(c)
}

// ---- the scene ---------------------------------------------------------------------------------------------------------

export function createCoder(canvas, opts = {}) {
  const fpsCap = opts.fps ?? 45
  const reduced = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
  const lift = opts.lift ?? 0 // moves the whole scene up (+) or down (-) in the frame

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.05

  const scene = new THREE.Scene()
  const pmrem = new THREE.PMREMGenerator(renderer)
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.environmentIntensity = 0.28

  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 40)
  const TARGET = new THREE.Vector3(0.38, 1.0 - lift, 0.05)

  const M = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.62, metalness: 0.05, ...o })
  const mats = {
    desk: M(0x1a1c20, { roughness: 0.45, metalness: 0.15 }),
    deskEdge: M(0x2a2d33, { roughness: 0.4, metalness: 0.3 }),
    metal: M(0x25272c, { roughness: 0.35, metalness: 0.7 }),
    dark: M(0x15161a),
    chair: M(0x1b1d22, { roughness: 0.8 }),
    shirt: M(0x2b3040, { roughness: 0.85 }),
    sleeve: M(0x2f3446, { roughness: 0.85 }),
    pants: M(0x1b1e26, { roughness: 0.85 }),
    shoe: M(0x2c303b, { roughness: 0.6 }),
    skin: M(0xd7a985, { roughness: 0.7 }),
    skinBack: M(0xc99a78, { roughness: 0.7 }),
    hair: M(0x141414, { roughness: 0.55 }),
    cyan: new THREE.MeshStandardMaterial({ color: 0x0b2a30, emissive: COL.cyan, emissiveIntensity: 1.1, roughness: 0.4 }),
    face: new THREE.MeshBasicMaterial({ color: 0x141414 }),
    mouth: new THREE.MeshBasicMaterial({ color: 0x6e3f2d }),
    mouthIn: new THREE.MeshBasicMaterial({ color: 0x3d1d14 }),
    mug: M(0xe9e9e9, { roughness: 0.3 }),
    plant: M(0x1f8f5f, { roughness: 0.8 }),
    pot: M(0x3a3a40, { roughness: 0.7 }),
    note: M(0xffc857, { roughness: 0.9, emissive: 0x3a2a00, emissiveIntensity: 0.4 }),
    floor: M(0x0b0c0f, { roughness: 0.95 }),
  }
  const box = (w, h, d, mat, r = 0.012) => new THREE.Mesh(r > 0 ? new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2.2, h / 2.2, d / 2.2)) : new THREE.BoxGeometry(w, h, d), mat)
  const cyl = (rt, rb, h, mat, seg = 20) => new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat)
  const sph = (r, mat, ws = 24, hs = 16) => new THREE.Mesh(new THREE.SphereGeometry(r, ws, hs), mat)
  const at = (o, x, y, z) => { o.position.set(x, y, z); return o }

  // floor and soft contact shadows
  const floor = new THREE.Mesh(new THREE.CircleGeometry(2.5, 72), mats.floor)
  floor.rotation.x = -Math.PI / 2
  floor.position.set(0.4, 0, 0)
  scene.add(floor)
  const ring = new THREE.Mesh(new THREE.RingGeometry(2.47, 2.5, 96), new THREE.MeshBasicMaterial({ color: COL.cyan, transparent: true, opacity: 0.35 }))
  ring.rotation.x = -Math.PI / 2
  ring.position.set(0.4, 0.002, 0)
  scene.add(ring)
  const blobTex = blobTexture()
  ;[[0.55, 1.4, 0.7, 2.9], [-0.42, 1.2, 1.2, 1.2], [1.35, 0.8, 0.6, 0.6]].forEach(([x, , z, s], i) => {
    const b = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, opacity: 0.8 }))
    b.rotation.x = -Math.PI / 2
    b.position.set(x, 0.004, 0)
    b.scale.set(s * (i === 0 ? 1.15 : 1.0), s * (i === 0 ? 0.55 : 1.0), 1)
    scene.add(b)
  })

  // desk
  const desk = new THREE.Group()
  scene.add(desk)
  const top = box(1.95, 0.05, 1.1, mats.desk, 0.02)
  desk.add(at(top, 0.72, 0.745, 0))
  const lip = box(1.95, 0.012, 1.1, mats.deskEdge, 0.006)
  desk.add(at(lip, 0.72, 0.716, 0))
  ;[[-0.2, -0.48], [-0.2, 0.48], [1.64, -0.48], [1.64, 0.48]].forEach(([x, z]) => desk.add(at(box(0.05, 0.72, 0.05, mats.metal, 0.01), x, 0.36, z)))
  desk.add(at(box(0.5, 0.5, 0.7, mats.dark, 0.02), 1.38, 0.47, 0)) // drawer unit
  desk.add(at(box(0.01, 0.06, 0.4, mats.cyan, 0.003), 1.134, 0.58, 0)) // its light strip

  // monitor: faces the person, turned a little toward the camera
  const monitor = new THREE.Group()
  monitor.position.set(0.95, 0.77, 0)
monitor.scale.setScalar(1.2)
  monitor.rotation.y = -Math.PI / 2 + 0.85
  scene.add(monitor)
  monitor.add(at(cyl(0.11, 0.13, 0.025, mats.metal, 32), 0, 0.012, 0))
  monitor.add(at(box(0.05, 0.3, 0.03, mats.metal, 0.01), 0, 0.17, -0.04))
  const panel = box(1.06, 0.66, 0.04, mats.dark, 0.02)
  monitor.add(at(panel, 0, 0.5, 0))
  const SW = 1024, SH = 640
  const sc = document.createElement('canvas')
  sc.width = SW; sc.height = SH
  const sctx = sc.getContext('2d')
  const screenTex = new THREE.CanvasTexture(sc)
  screenTex.colorSpace = THREE.SRGBColorSpace
  screenTex.anisotropy = 8
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.625), new THREE.MeshBasicMaterial({ map: screenTex, toneMapped: false }))
  screen.position.set(0, 0.5, 0.0215)
  monitor.add(screen)
  monitor.add(at(box(0.012, 0.012, 0.012, mats.cyan, 0.002), 0, 0.172, 0.022)) // power led
  const note = box(0.08, 0.08, 0.004, mats.note, 0)
  note.position.set(0.5, 0.75, 0.022); note.rotation.z = 0.15
  monitor.add(note)

  // keyboard, mouse, mug, plant, lamp
  // keyboard: a 61-key layout, keys 3 cm apart, lit from below. Width runs along z (left to right for the person).
  const DESK_TOP = 0.77
  const U = 0.03
  const KB = { x: 0.2, z: 0.0 }
  const kb = new THREE.Group()
  kb.position.set(KB.x, DESK_TOP, KB.z)
  desk.add(kb)
  kb.add(at(box(5.55 * U + 0.012, 0.012, 15.5 * U + 0.012, mats.dark, 0.008), 0, 0.006, 0))
  kb.add(at(box(5.35 * U + 0.012, 0.004, 15.3 * U + 0.012, mats.cyan, 0.002), 0, 0.0125, 0))
  const chars = (str) => [...str].map((c) => [c, 1])
  const ROWS = [
    [...chars('`1234567890-='), ['bksp', 2]],
    [['tab', 1.5], ...chars('qwertyuiop[]'), ['\\', 1.5]],
    [['caps', 1.75], ...chars("asdfghjkl;'"), ['enter', 2.25]],
    [['lshift', 2.25], ...chars('zxcvbnm,./'), ['rshift', 2.75]],
    [['ctrl', 1.25], ['win', 1.25], ['alt', 1.25], [' ', 6.25], ['ralt', 1.25], ['fn', 1.25], ['menu', 1.25], ['rctrl', 1.25]],
  ]
  const keys = []
  ROWS.forEach((row, r) => {
    let zc = -7.5
    row.forEach(([label, w]) => {
      keys.push({ label, w, x: (2 - r) * U, z: (zc + w / 2) * U, depth: 0 })
      zc += w
    })
  })
  const KEY_H = 0.014, KEY_Y = 0.0145
  const keyMesh = new THREE.InstancedMesh(new RoundedBoxGeometry(1, 1, 1, 2, 0.16), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.5, metalness: 0.1 }), keys.length)
  const keyDummy = new THREE.Object3D()
  const keyColor = new THREE.Color()
  const placeKey = (i) => {
    const k = keys[i]
    keyDummy.position.set(k.x, KEY_Y + KEY_H / 2 - 0.0045 * k.depth, k.z)
    keyDummy.scale.set(U * 0.9, KEY_H, k.w * U - U * 0.1)
    keyDummy.updateMatrix()
    keyMesh.setMatrixAt(i, keyDummy.matrix)
  }
  keys.forEach((k, i) => {
    placeKey(i)
    const wasd = k.label.length === 1 && 'wasd'.includes(k.label)
    keyColor.setHex(wasd ? 0x1d5663 : k.label.length > 1 ? 0x15171c : 0x262a32)
    keyMesh.setColorAt(i, keyColor)
  })
  kb.add(keyMesh)
  const keyIndex = new Map()
  keys.forEach((k, i) => { if (!keyIndex.has(k.label)) keyIndex.set(k.label, i) })
  const SHIFTED = { '(': '9', ')': '0', '_': '-', ':': ';', '+': '=', '"': "'", '{': '[', '}': ']', '<': ',', '>': '.', '?': '/', '!': '1' }
  const keyForChar = (ch) => (ch === '\n' ? keyIndex.get('enter') : (keyIndex.get(ch.toLowerCase()) ?? keyIndex.get(SHIFTED[ch]) ?? keyIndex.get(' ')))
  const keyForEvent = (i) => {
    if (i < TOTAL_CHARS) return keyForChar(STREAM[i])
    if (i < TOTAL_CHARS + BUG_TAIL.length) return keyIndex.get('bksp')
    return keyForChar(FIX_TAIL[i - TOTAL_CHARS - BUG_TAIL.length])
  }

  // mouse on a pad, to the right of the keyboard
  const MOUSE = { x: 0.2, z: 0.42 }
  const padMat = M(0x101216, { roughness: 0.95 })
  desk.add(at(box(0.22, 0.004, 0.26, padMat, 0.002), MOUSE.x, DESK_TOP + 0.002, MOUSE.z))
  desk.add(at(box(0.003, 0.0045, 0.26, mats.cyan, 0.001), MOUSE.x + 0.11, DESK_TOP + 0.002, MOUSE.z))
  const mouse = new THREE.Group()
  mouse.position.set(MOUSE.x, DESK_TOP + 0.004, MOUSE.z)
  desk.add(mouse)
  const mouseBody = sph(1, M(0x23262d, { roughness: 0.4, metalness: 0.2 }), 28, 16)
  mouseBody.scale.set(0.058, 0.019, 0.034)
  mouse.add(at(mouseBody, 0, 0.008, 0))
  const btnMat = M(0x2d3138, { roughness: 0.35, metalness: 0.2 })
  const btnL = box(0.04, 0.004, 0.0155, btnMat, 0.0015)
  const btnR = box(0.04, 0.004, 0.0155, btnMat, 0.0015)
  mouse.add(at(btnL, 0.02, 0.0225, -0.0105), at(btnR, 0.02, 0.0225, 0.0105))
  const wheel = cyl(0.0065, 0.0065, 0.009, mats.cyan, 16)
  wheel.rotation.x = Math.PI / 2
  mouse.add(at(wheel, 0.026, 0.0262, 0))
  mouse.add(at(box(0.02, 0.003, 0.012, mats.cyan, 0.001), -0.026, 0.0235, 0))
  const cable = (pts, r = 0.0026) => {
    const curve = new THREE.CatmullRomCurve3(pts.map((q) => new THREE.Vector3(q[0], q[1], q[2])))
    desk.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 40, r, 6), mats.dark))
  }
  cable([[MOUSE.x + 0.058, DESK_TOP + 0.012, MOUSE.z], [0.45, DESK_TOP + 0.004, 0.42], [0.72, DESK_TOP + 0.003, 0.28], [0.95, DESK_TOP + 0.004, 0.06], [1.04, DESK_TOP + 0.05, -0.04]])
  cable([[KB.x + 0.085, DESK_TOP + 0.01, 0.12], [0.5, DESK_TOP + 0.003, 0.14], [0.8, DESK_TOP + 0.003, 0.04], [1.02, DESK_TOP + 0.05, -0.05]])
  const mug = cyl(0.04, 0.036, 0.09, mats.mug, 24)
  desk.add(at(mug, 1.3, 0.815, 0.32))
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.024, 0.006, 8, 16, Math.PI), mats.mug)
  handle.position.set(1.3 + 0.04, 0.815, 0.32); handle.rotation.z = -Math.PI / 2
  desk.add(handle)
  const steam = []
  for (let i = 0; i < 3; i++) {
    const s = sph(0.014, new THREE.MeshBasicMaterial({ color: 0xcfd8dc, transparent: true, opacity: 0 }), 8, 6)
    desk.add(s); steam.push(s)
  }
  const pot = cyl(0.06, 0.045, 0.1, mats.pot, 20)
  desk.add(at(pot, 1.48, 0.82, -0.3))
  for (let i = 0; i < 6; i++) {
    const leaf = sph(0.05, mats.plant, 10, 8)
    leaf.scale.set(0.5, 1.6, 0.3)
    const a = (i / 6) * Math.PI * 2
    leaf.position.set(1.48 + Math.cos(a) * 0.04, 0.95 + (i % 2) * 0.03, -0.3 + Math.sin(a) * 0.04)
    leaf.rotation.set(Math.sin(a) * 0.5, 0, -Math.cos(a) * 0.5)
    desk.add(leaf)
  }
  // lamp
  const lamp = new THREE.Group()
  lamp.position.set(1.52, 0.77, 0.3)
  desk.add(lamp)
  lamp.add(at(cyl(0.06, 0.07, 0.02, mats.metal, 20), 0, 0.01, 0))
  const arm1 = at(box(0.015, 0.42, 0.015, mats.metal, 0.004), 0, 0.23, 0); arm1.rotation.z = 0.25; lamp.add(arm1)
  const arm2 = at(box(0.015, 0.32, 0.015, mats.metal, 0.004), -0.16, 0.5, 0); arm2.rotation.z = -1.0; lamp.add(arm2)
  lamp.add(at(cyl(0.02, 0.07, 0.07, mats.metal, 20), -0.3, 0.5, 0))
  lamp.add(at(sph(0.025, new THREE.MeshBasicMaterial({ color: 0xfff1c9 }), 12, 8), -0.3, 0.46, 0))
  lamp.rotation.y = -0.3
  // books
  ;[[0.07, 0xff5c7a], [0.06, 0x3de0ff], [0.05, 0x9b7bff]].forEach(([h, c], i) => {
    const b = box(0.26, h, 0.18, M(c, { roughness: 0.7 }), 0.006)
    b.position.set(1.38, 0.77 + 0.5 * 0 + 0.03 + [0, 0.07, 0.13][i], 0.0 + [0, 0.01, -0.01][i])
    b.position.y = 0.72 + 0.25 + 0.035 + [0, 0.07, 0.13][i] - 0.02
    b.rotation.y = [0, 0.1, -0.08][i]
    desk.add(b)
  })

  // chair
  const chair = new THREE.Group()
  chair.position.set(-0.4, 0, 0)
  scene.add(chair)
  chair.add(at(box(0.56, 0.07, 0.56, mats.chair, 0.03), 0, 0.46, 0))
  chair.add(at(box(0.06, 0.62, 0.5, mats.chair, 0.03), -0.3, 0.84, 0))
  chair.add(at(box(0.05, 0.1, 0.16, mats.metal, 0.01), -0.27, 0.56, 0))
  chair.add(at(cyl(0.03, 0.03, 0.36, mats.metal, 12), 0, 0.26, 0))
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2 + 0.3
    const leg = box(0.34, 0.025, 0.04, mats.metal, 0.008)
    leg.position.set(Math.cos(a) * 0.17, 0.08, Math.sin(a) * 0.17); leg.rotation.y = -a
    chair.add(leg)
    chair.add(at(sph(0.025, mats.dark, 10, 8), Math.cos(a) * 0.33, 0.03, Math.sin(a) * 0.33))
  }

  // the person: root sits on the seat, facing +X
  const person = new THREE.Group()
  person.position.set(-0.36, 0.5, 0)
  scene.add(person)
  ;[-1, 1].forEach((s) => {
    person.add(at(box(0.5, 0.15, 0.16, mats.pants, 0.06), 0.22, 0.08, s * 0.105))
    const shin = cyl(0.062, 0.05, 0.5, mats.pants, 14)
    person.add(at(shin, 0.46, -0.2, s * 0.105))
    person.add(at(box(0.27, 0.075, 0.13, mats.shoe, 0.035), 0.55, -0.44, s * 0.105))
  })
  const torso = new THREE.Group()
  person.add(torso)
  torso.add(at(box(0.3, 0.54, 0.42, mats.shirt, 0.1), 0, 0.28, 0))
  torso.add(at(box(0.26, 0.18, 0.4, mats.pants, 0.07), 0, 0.02, 0))
  const hood = sph(0.13, mats.shirt, 16, 12); hood.scale.set(0.8, 0.55, 1.4); torso.add(at(hood, -0.1, 0.58, 0))
  const logo = box(0.004, 0.06, 0.09, mats.cyan, 0.001); torso.add(at(logo, 0.152, 0.36, 0.0))

  const head = new THREE.Group()
  head.position.set(0.02, 0.57, 0)
  torso.add(head)
  head.add(at(cyl(0.052, 0.058, 0.12, mats.skinBack, 14), -0.005, 0.0, 0))
  const skull = sph(0.15, mats.skin, 28, 20); skull.scale.set(1.0, 1.1, 0.95); head.add(at(skull, 0.0, 0.2, 0))
  const hairTop = new THREE.Mesh(new THREE.SphereGeometry(0.16, 28, 14, 0, Math.PI * 2, 0, Math.PI * 0.5), mats.hair)
  head.add(at(hairTop, -0.022, 0.235, 0)); hairTop.scale.set(1.0, 1.05, 0.98)
  const hairBack = new THREE.Mesh(new THREE.SphereGeometry(0.16, 24, 14, -Math.PI * 0.55, Math.PI * 1.1, Math.PI * 0.45, Math.PI * 0.35), mats.hair)
  head.add(at(hairBack, -0.022, 0.235, 0)); hairBack.scale.set(1.0, 1.05, 0.98)
  const eyes = new THREE.Group(); head.add(eyes)
  ;[-1, 1].forEach((s) => eyes.add(at(sph(0.017, mats.face, 10, 8), 0.14, 0.215, s * 0.055)))
  const brows = []
  ;[-1, 1].forEach((s) => { const b = box(0.01, 0.009, 0.04, mats.hair, 0); b.position.set(0.142, 0.255, s * 0.055); head.add(b); brows.push(b) })
  head.add(at(sph(0.02, mats.skinBack, 10, 8), 0.152, 0.185, 0))
  const mouthSmile = new THREE.Group(); mouthSmile.position.set(0.147, 0.125, 0); mouthSmile.rotation.y = Math.PI / 2
  { const t = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.0045, 6, 14, Math.PI), mats.mouth); t.rotation.z = Math.PI; mouthSmile.add(t) }
  const mouthO = at(sph(0.02, mats.mouthIn, 12, 8), 0.146, 0.122, 0); mouthO.scale.set(0.45, 1.2, 0.8)
  const mouthFlat = at(box(0.006, 0.006, 0.05, mats.mouth, 0), 0.149, 0.122, 0)
  head.add(mouthSmile, mouthO, mouthFlat)
  // headphones
  const band = new THREE.Mesh(new THREE.TorusGeometry(0.175, 0.012, 8, 36, Math.PI), mats.cyan)
  band.position.set(-0.01, 0.2, 0); band.rotation.y = Math.PI / 2
  head.add(band)
  ;[-1, 1].forEach((s) => { const cup = cyl(0.058, 0.058, 0.045, mats.cyan, 20); cup.rotation.x = Math.PI / 2; head.add(at(cup, -0.01, 0.2, s * 0.17)) })
  const chin = new THREE.Object3D(); chin.position.set(0.1, 0.09, 0); head.add(chin)
  const crown = new THREE.Object3D(); crown.position.set(0, 0.5, 0); head.add(crown)

  // arms: shoulder pivot -> upper arm -> elbow pivot -> forearm -> hand
  const L1 = 0.29, L2 = 0.29
  function makeArm(z, sleeve, skin) {
    const shoulder = new THREE.Group(); shoulder.position.set(0, 0.5, z); torso.add(shoulder)
    shoulder.add(at(sph(0.062, sleeve, 14, 10), 0, 0, 0))
    shoulder.add(at(cyl(0.052, 0.046, L1, sleeve, 14), 0, -L1 / 2, 0))
    const elbow = new THREE.Group(); elbow.position.set(0, -L1, 0); shoulder.add(elbow)
    elbow.add(at(sph(0.047, sleeve, 12, 8), 0, 0, 0))
    elbow.add(at(cyl(0.046, 0.04, L2, sleeve, 14), 0, -L2 / 2, 0))
    const hand = sph(0.047, skin, 14, 10); hand.scale.set(1.25, 0.8, 1.0); elbow.add(at(hand, 0, -L2 - 0.01, 0))
    return { shoulder, elbow }
  }
  const armNear = makeArm(0.255, mats.sleeve, mats.skin)
  const armFar = makeArm(-0.255, mats.shirt, mats.skinBack)

  // thought bubbles
  const bubbleMat = (k) => new THREE.SpriteMaterial({ map: glyphTexture(k), transparent: true, depthTest: false })
  const bubbles = { err: new THREE.Sprite(bubbleMat('err')), q: new THREE.Sprite(bubbleMat('q')), ok: new THREE.Sprite(bubbleMat('ok')) }
  Object.values(bubbles).forEach((b) => { b.renderOrder = 10; b.scale.setScalar(0.0001); scene.add(b) })

  // lights: a cool rim from behind, a soft fill, and the screen, which changes colour with the story
  scene.add(new THREE.HemisphereLight(0x8fb0ff, 0x05060a, 0.55))
  const rim = new THREE.DirectionalLight(0x6fd8ff, 1.5); rim.position.set(-2.5, 3.2, -3); scene.add(rim)
  const key = new THREE.DirectionalLight(0xbcc7ff, 0.9); key.position.set(-2, 3.5, 3.5); scene.add(key)
  const screenLight = new THREE.PointLight(COL.cyan, 4, 5, 1.6); screenLight.position.set(0.55, 1.35, 0.2); scene.add(screenLight)
  const lampLight = new THREE.PointLight(0xffe0a8, 0.9, 2.2, 1.8); lampLight.position.set(1.15, 1.25, 0.4); scene.add(lampLight)

  // ---- animation ------------------------------------------------------------------------------------------------------
  const V = new THREE.Vector3()
  const tmp = new THREE.Vector3()
  const cNow = new THREE.Color(COL.cyan)

  function solveArm(arm, tx, ty, tz) {
    torso.updateMatrixWorld(true)
    arm.shoulder.getWorldPosition(V)
    const dx = tx - V.x, dy = ty - V.y, dz = tz - V.z
    const rh = Math.hypot(dx, dz) // reach along the floor; the shoulder yaws toward the target
    const d = clamp(Math.hypot(rh, dy), Math.abs(L1 - L2) + 0.02, L1 + L2 - 0.005)
    const base = Math.atan2(rh, -dy)
    const alpha = Math.acos(clamp((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1, 1))
    const a1 = base - alpha
    const er = L1 * Math.sin(a1), ey = V.y - L1 * Math.cos(a1)
    const a2 = Math.atan2(rh - er, -(ty - ey))
    arm.shoulder.rotation.set(0, -Math.atan2(dz, Math.max(dx, 0.05)), a1 - torso.rotation.z, 'XYZ')
    arm.elbow.rotation.z = a2 - a1
  }

  // the hands follow the keys that are being pressed: left hand for the left half, right hand for the right half
  const hand = { L: { x: KB.x, z: -0.09, tx: KB.x, tz: -0.09, dip: 0 }, R: { x: KB.x, z: 0.09, tx: KB.x, tz: 0.09, dip: 0 } }
  let lastEv = 0
  function typeKeys(p, dt) {
    const ev = eventsAt(p)
    if (ev < lastEv) lastEv = ev
    for (let i = Math.max(lastEv, ev - 8); i < ev; i++) {
      const idx = keyForEvent(i)
      if (idx == null) continue
      const k = keys[idx]
      k.depth = 1
      const h = k.z < 0.0 ? hand.L : hand.R
      h.tx = KB.x + k.x - 0.03
      h.tz = KB.z + k.z * 0.8
      h.dip = 1
    }
    lastEv = ev
    let dirty = false
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i]
      if (k.depth > 0.002) { k.depth *= Math.exp(-dt * 14); placeKey(i); dirty = true } else if (k.depth !== 0) { k.depth = 0; placeKey(i); dirty = true }
    }
    if (dirty) keyMesh.instanceMatrix.needsUpdate = true
    const busy = (p > 2 && p < 29.5) || (p > 61 && p < 65.6)
    ;[hand.L, hand.R].forEach((h, n) => {
      if (!busy) { h.tx = KB.x - 0.005; h.tz = n ? 0.09 : -0.09 }
      const f = 1 - Math.exp(-dt * 24)
      h.x += (h.tx - h.x) * f
      h.z += (h.tz - h.z) * f
      h.dip *= Math.exp(-dt * 16)
    })
  }

  function pose(p, time, dt) {
    // body
    torso.rotation.z = track(p, [[0, -0.1], [30, -0.1], [32.5, 0.2], [38, 0.17], [42, 0.03], [58, 0.05], [61, -0.12], [67, -0.12], [71, 0.02], [76, -0.06], [100, -0.1]])
    head.rotation.z = track(p, [[0, -0.1], [30, -0.1], [32.5, 0.16], [38, 0.14], [42, -0.14], [50, -0.2], [58, -0.14], [61, -0.08], [70, -0.02], [73, 0.1], [76, -0.04], [79, 0.08], [83, -0.06], [100, -0.1]])
    head.rotation.y = track(p, [[0, 0], [30, 0], [34, -0.12], [42, 0.05], [50, -0.1], [58, 0], [100, 0]])
    // eyes blink, brows and mouth
    const blink = [9.6, 49.6, 85.6].some((b) => p > b && p < b + 1.2)
    eyes.scale.y = blink ? 0.12 : 1
    const browUp = track(p, [[0, 0], [31, 0], [32.5, 0.016], [39, 0.016], [42, -0.008], [58, -0.008], [61, 0], [100, 0]])
    brows.forEach((b, i) => { b.position.y = 0.255 + browUp; b.rotation.x = (i ? -1 : 1) * track(p, [[0, 0], [41, 0], [43, 0.25], [58, 0.25], [61, 0], [100, 0]]) })
    const mood = p < 31.2 ? 'smile' : p < 40.5 ? 'o' : p < 68 ? 'flat' : 'smile'
    mouthSmile.visible = mood === 'smile'
    mouthO.visible = mood === 'o'
    mouthFlat.visible = mood === 'flat'

    // hands: targets in world space. Keys, then the mouse to click Run, then up in surprise, then to the chin.
    const keyY = 0.84
    const mouseW = Math.max(ramp(p, 28.8, 29.8) * (1 - ramp(p, 31.8, 33.5)), ramp(p, 65.4, 66.3) * (1 - ramp(p, 73, 78)))
    const clicking = (p >= 29.9 && p < 30.5) || (p >= 66.4 && p < 67)
    btnL.position.y = 0.0225 - (clicking ? 0.0022 : 0)
    mouse.position.x = MOUSE.x + 0.014 * Math.sin(time * 2.1) * mouseW * (clicking ? 0 : 1)
    mouse.position.z = MOUSE.z + 0.012 * Math.sin(time * 1.7 + 1) * mouseW * (clicking ? 0 : 1)
    const shock = ramp(p, 31, 32.5) * (1 - ramp(p, 40, 42))
    const think = ramp(p, 41, 43.5) * (1 - ramp(p, 57.5, 61))
    head.updateMatrixWorld(true)
    chin.getWorldPosition(tmp)
    const upX = person.position.x + 0.3, upY = 1.18
    const nearX = lerp(hand.R.x, mouse.position.x - 0.012, mouseW)
    const nearZ = lerp(hand.R.z, mouse.position.z, mouseW)
    const nearY = lerp(keyY - 0.012 * hand.R.dip, DESK_TOP + 0.075 - (clicking ? 0.004 : 0), mouseW)
    const nx = lerp(lerp(nearX, upX, shock), tmp.x + 0.02, think)
    const ny = lerp(lerp(nearY, upY, shock), tmp.y - 0.01, think)
    const nz = lerp(lerp(nearZ, 0.2, shock), tmp.z + 0.12, think)
    const fx = lerp(hand.L.x, upX - 0.05, shock * 0.85)
    const fy = lerp(keyY - 0.012 * hand.L.dip, upY - 0.1, shock * 0.85)
    const fz = lerp(hand.L.z, -0.2, shock * 0.85)
    solveArm(armNear, nx, ny, nz)
    solveArm(armFar, fx, fy, fz)
  }

  function lights(p) {
    const e = ramp(p, 31, 33) * (1 - ramp(p, 61, 64))
    const g = ramp(p, 68.5, 71) * (1 - ramp(p, 90, 95))
    cNow.setHex(COL.cyan).lerp(new THREE.Color(COL.red), e).lerp(new THREE.Color(COL.mint), g)
    screenLight.color.copy(cNow)
    screenLight.intensity = 4 + e * 3 + g * 2.5
    mats.cyan.emissive.copy(cNow)
  }

  function bubblesAt(p) {
    head.getWorldPosition(V)
    const place = (s, k, a, b, c, d) => {
      const t = ramp(p, a, b) * (1 - ramp(p, c, d))
      s.scale.setScalar(Math.max(0.0001, 0.36 * (t > 0 ? easeOutBack(clamp((p - a) / (b - a), 0, 1)) * (1 - ramp(p, c, d)) : 0)))
      s.position.set(V.x + 0.03, V.y + 0.56 + 0.012 * Math.sin(p * 0.9), V.z + 0.02)
      s.visible = t > 0.001
    }
    place(bubbles.err, 'err', 31.5, 33, 38.5, 41)
    place(bubbles.q, 'q', 42.5, 44, 56.5, 59)
    place(bubbles.ok, 'ok', 70.5, 72, 88, 91)
  }

  function steamAt(time) {
    steam.forEach((s, i) => {
      const t = ((time * 0.35 + i / 3) % 1)
      s.position.set(1.3 + Math.sin(t * 6 + i) * 0.012, 0.87 + t * 0.2, 0.32)
      s.material.opacity = Math.sin(t * Math.PI) * 0.35
    })
  }

  // camera: a slow drift plus a little parallax from the pointer
  const ptr = { x: 0, y: 0, tx: 0, ty: 0 }
  function onPointer(e) { ptr.tx = (e.clientX / innerWidth - 0.5) * 2; ptr.ty = (e.clientY / innerHeight - 0.5) * 2 }
  if (opts.interactive !== false) window.addEventListener('pointermove', onPointer, { passive: true })
  let width = 1, height = 1
  function placeCamera(time) {
    ptr.x += (ptr.tx - ptr.x) * 0.05
    ptr.y += (ptr.ty - ptr.y) * 0.05
    const aspect = width / height
    const half = Math.tan((camera.fov * Math.PI) / 360)
    const R = Math.max(1.4 / (half * aspect), 1.08 / half)
    const az = -0.2 + 0.1 * Math.sin(time * 0.22) + ptr.x * 0.14
    const el = TARGET.y + R * 0.2 + ptr.y * -0.16 + 0.04 * Math.sin(time * 0.17)
    camera.position.set(TARGET.x + Math.sin(az) * R, el, TARGET.z + Math.cos(az) * R)
    camera.lookAt(TARGET)
  }

  function resize() {
    const w = Math.max(2, canvas.clientWidth), h = Math.max(2, canvas.clientHeight)
    if (w === width && h === height) return
    width = w; height = h
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, opts.dpr ?? 1.6))
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()
  }

  // ---- loop -----------------------------------------------------------------------------------------------------------
  let raf = 0, visible = true, last = 0, lastT = 0, clockStart = performance.now(), sig = ''
  let fontOk = false
  const refreshFont = () => {
    if (!document.fonts?.load) return
    document.fonts.load('600 26px "JetBrains Mono Variable"').then(() => { fontOk = true; sig = '' }).catch(() => {})
  }
  refreshFont()

  function render(time) {
    const p = reduced ? 80 : ((time % LOOP) / LOOP) * 100
    resize()
    const dt = clamp(time - lastT, 0, 0.1)
    lastT = time
    if (!reduced) typeKeys(p, dt)
    pose(p, time, dt)
    lights(p)
    bubblesAt(p)
    steamAt(time)
    placeCamera(reduced ? 0 : time)
    const s = `${Math.floor(p * 12)}|${Math.floor(time * 2) % 2}|${fontOk}`
    if (s !== sig) { sig = s; drawScreen(sctx, SW, SH, p, time, fontOk); screenTex.needsUpdate = true }
    renderer.render(scene, camera)
  }

  function frame(now) {
    raf = requestAnimationFrame(frame)
    if (!visible || document.hidden) return
    if (now - last < 1000 / fpsCap) return
    last = now
    render((now - clockStart) / 1000)
  }

  const io = typeof IntersectionObserver === 'function' ? new IntersectionObserver((en) => { visible = en[0]?.isIntersecting !== false }) : null
  io?.observe(canvas)
  const ro = typeof ResizeObserver === 'function' ? new ResizeObserver(() => { if (reduced) render(0) }) : null
  ro?.observe(canvas)

  if (reduced) render(0)
  else raf = requestAnimationFrame(frame)

  return {
    dispose() {
      cancelAnimationFrame(raf)
      io?.disconnect(); ro?.disconnect()
      window.removeEventListener('pointermove', onPointer)
      scene.traverse((o) => {
        if (o.geometry) o.geometry.dispose()
        const ms = o.material ? (Array.isArray(o.material) ? o.material : [o.material]) : []
        ms.forEach((m) => { m.map?.dispose(); m.dispose() })
      })
      screenTex.dispose(); blobTex.dispose(); pmrem.dispose(); renderer.dispose()
    },
  }
}
