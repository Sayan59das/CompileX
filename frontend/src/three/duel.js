// The duel: two players at one table, each typing on their own laptop, facing each other, with a live scoreboard above them.
//
// Built in metres from primitives, in the same language as the coder figure in coder.js (seated figure, hoodie, headphones,
// arms that reach the keyboard with a two-bone solve). You sit on the left in cyan, the rival on the right in violet, matching the
// arena's two rim lights. The arena's own laptop flies onto the table as yours (arena.js places it at `slotA`); the rival's laptop
// is a copy of it that arena.js puts at `slotB`.

import * as THREE from 'three'
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))

export const TABLE_TOP = 0.74
// The arena laptop is 3.6 units wide; on the table it is a 45 cm machine (a touch large, so the screens read at page size).
export const LAPTOP_SCALE = 0.125

export const CYAN = 0x3de0ff
// natural skin tones, a little less saturated than they look on paper, since the filmic tone mapping warms and deepens them
export const SKIN = { you: 0xc89a7c, rival: 0x7c5642, third: 0xe9c9b0 }
export const VIOLET = 0x9b7bff

export const M = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.7, metalness: 0.05, ...o })
export const box = (w, h, d, m, r = 0.01) => new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2 - 1e-4, h / 2 - 1e-4, d / 2 - 1e-4)), m)
export const cyl = (a, b, h, m, s = 20) => new THREE.Mesh(new THREE.CylinderGeometry(a, b, h, s), m)
export const sph = (r, m, ws = 24, hs = 16) => new THREE.Mesh(new THREE.SphereGeometry(r, ws, hs), m)
// a capsule standing on its own length, centred
export const cap = (r, len, m) => new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 5, 14), m)
export const glow = (c) => new THREE.MeshBasicMaterial({ color: c, toneMapped: false })
export const at = (o, x, y, z) => { o.position.set(x, y, z); return o }

// Merge the still meshes under `root` into one mesh per material: the same picture for far fewer draw calls (in the shadow pass
// too). A group marked `userData.live` moves on its own, so it is merged separately into itself. `own` says the source geometries
// belong to this tree and can be freed (a cloned laptop shares them with the original, so it passes false).
export function bake(root, own = true) {
  root.updateMatrixWorld(true)
  const inv = new THREE.Matrix4().copy(root.matrixWorld).invert()
  const rel = new THREE.Matrix4()
  const buckets = new Map()
  const live = []
  const visit = (o) => {
    for (const c of o.children) {
      if (c.userData.live) { live.push(c); continue }
      if (c.isMesh && !c.isInstancedMesh && c.visible && c.children.length === 0) {
        const g = c.geometry
        const key = `${c.material.uuid}|${g.index ? 1 : 0}|${Object.keys(g.attributes).sort().join(',')}|${c.renderOrder}`
        if (!buckets.has(key)) buckets.set(key, { material: c.material, items: [] })
        buckets.get(key).items.push(c)
      }
      visit(c)
    }
  }
  visit(root)
  for (const { material, items } of buckets.values()) {
    if (items.length < 2) continue
    const geos = items.map((m) => { rel.multiplyMatrices(inv, m.matrixWorld); return m.geometry.clone().applyMatrix4(rel) })
    const merged = mergeGeometries(geos)
    geos.forEach((g) => g.dispose())
    if (!merged) continue
    items.forEach((m) => { m.removeFromParent(); if (own) m.geometry.dispose() })
    const mesh = new THREE.Mesh(merged, material)
    mesh.renderOrder = items[0].renderOrder
    root.add(mesh)
  }
  live.forEach((l) => bake(l, own))
}

// a soft dark spot: the ambient shadow where furniture meets the floor
export function blobTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  const r = g.createRadialGradient(64, 64, 4, 64, 64, 64)
  r.addColorStop(0, 'rgba(0,0,0,0.85)')
  r.addColorStop(0.55, 'rgba(0,0,0,0.4)')
  r.addColorStop(1, 'rgba(0,0,0,0)')
  g.fillStyle = r
  g.fillRect(0, 0, 128, 128)
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return t
}

// A gaming chair facing +X, with a stripe in the player's colour down the backrest.
function makeChair(accent) {
  const shell = M(0x16181d, { roughness: 0.5 })
  const cushion = M(0x1d2026, { roughness: 0.85 })
  const metal = M(0x34373f, { metalness: 0.8, roughness: 0.3 })
  const stripe = M(accent, { emissive: accent, emissiveIntensity: 0.35, roughness: 0.4 })
  const chair = new THREE.Group()
  chair.add(at(box(0.5, 0.08, 0.5, cushion, 0.035), 0, 0.46, 0))
  ;[-1, 1].forEach((s) => chair.add(at(box(0.46, 0.06, 0.07, shell, 0.03), 0.01, 0.5, s * 0.235)))
  // backrest with side bolsters, a headrest and the stripe
  const back = new THREE.Group(); back.position.set(-0.27, 0.5, 0); back.rotation.z = 0.12; chair.add(back)
  back.add(at(box(0.08, 0.66, 0.46, shell, 0.04), 0, 0.33, 0))
  ;[-1, 1].forEach((s) => back.add(at(box(0.1, 0.5, 0.07, shell, 0.035), 0.03, 0.28, s * 0.2)))
  back.add(at(box(0.05, 0.56, 0.3, cushion, 0.025), 0.045, 0.32, 0))
  back.add(at(box(0.012, 0.5, 0.035, stripe, 0.006), 0.073, 0.32, 0))
  back.add(at(box(0.07, 0.12, 0.24, cushion, 0.05), 0.05, 0.6, 0))
  // armrests
  ;[-1, 1].forEach((s) => {
    chair.add(at(box(0.04, 0.2, 0.04, metal, 0.012), -0.02, 0.6, s * 0.27))
    chair.add(at(box(0.24, 0.035, 0.07, shell, 0.016), 0.0, 0.71, s * 0.27))
  })
  // gas lift and a five-star base on castors
  chair.add(at(cyl(0.032, 0.032, 0.34, metal), 0, 0.26, 0))
  chair.add(at(cyl(0.05, 0.05, 0.06, metal), 0, 0.11, 0))
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2 + 0.3
    const leg = box(0.3, 0.035, 0.05, metal, 0.012)
    leg.position.set(Math.cos(a) * 0.15, 0.085, Math.sin(a) * 0.15); leg.rotation.y = -a
    chair.add(leg)
    chair.add(at(sph(0.026, shell, 14, 10), Math.cos(a) * 0.29, 0.03, Math.sin(a) * 0.29))
  }
  return chair
}

// Seated, the thighs swing forward by SIT_ANGLE (a little under a right angle, so the feet reach the floor from the seat) and the
// knees fold back by the same; standing, both are 0 and the soles are STAND_HEIGHT below the root.
export const SIT_ANGLE = Math.PI / 2 - 0.16
export const STAND_HEIGHT = 0.872
export function poseLegs(p, hip, knee) {
  for (const side of ['L', 'R']) {
    p.legs[side].hip.rotation.z = hip
    p.legs[side].knee.rotation.z = -knee
  }
}

// A player facing +X: seated (the root sits on the seat) or, with `stand`, standing (the root is STAND_HEIGHT above the feet).
export function makePlayer({ shirt, skin, hair, accent, stand = false }) {
  const mats = {
    shirt: M(shirt, { roughness: 0.88 }),
    rib: M(new THREE.Color(shirt).multiplyScalar(0.7), { roughness: 0.95 }),
    pants: M(0x14161b, { roughness: 0.82 }),
    shoe: M(0x0b0c0f, { roughness: 0.45 }),
    sole: M(0xd9dbe0, { roughness: 0.6 }),
    skin: M(skin, { roughness: 0.62 }),
    hair: M(hair, { roughness: 0.92 }),
    eye: M(0x0d0e10, { roughness: 0.2 }),
    white: M(0xe8e9ec, { roughness: 0.5 }),
    phone: M(0x18191d, { roughness: 0.35, metalness: 0.4 }),
    accent: new THREE.MeshStandardMaterial({ color: accent, emissive: accent, emissiveIntensity: 0.6, roughness: 0.35, metalness: 0.2 }),
    led: glow(accent),
  }
  const root = new THREE.Group()
  // Legs, jointed at the hip and the knee so a player can sit, stand and jump: each joint is a group that turns about z, the hip
  // swinging the thigh forward (towards +X) and the knee folding the shin back. Straight, the soles are STAND_HEIGHT below the root.
  // Trainers with white soles.
  const legs = {}
  ;[-1, 1].forEach((s) => {
    const hip = new THREE.Group(); hip.userData.live = true; hip.position.set(0, 0.04, s * 0.105); root.add(hip)
    hip.add(at(cap(0.075, 0.3, mats.pants), 0, -0.22, 0))
    const knee = new THREE.Group(); knee.userData.live = true; knee.position.set(0, -0.44, 0); hip.add(knee)
    knee.add(at(cap(0.062, 0.3, mats.pants), 0, -0.21, 0))
    knee.add(at(box(0.27, 0.07, 0.125, mats.shoe, 0.034), 0.06, -0.425, 0))
    knee.add(at(box(0.275, 0.022, 0.13, mats.sole, 0.01), 0.06, -0.461, 0))
    legs[s < 0 ? 'L' : 'R'] = { hip, knee }
  })
  const torso = new THREE.Group(); torso.userData.live = true; root.add(torso)
  torso.add(at(box(0.3, 0.54, 0.42, mats.shirt, 0.12), 0, 0.28, 0))
  torso.add(at(box(0.27, 0.07, 0.4, mats.rib, 0.03), 0, 0.025, 0))
  // hoodie: a hood folded behind the neck, a front pocket and two drawstrings
  const hood = sph(0.13, mats.shirt, 24, 16); hood.scale.set(0.8, 0.55, 1.4); torso.add(at(hood, -0.1, 0.58, 0))
  torso.add(at(box(0.012, 0.13, 0.24, mats.rib, 0.006), 0.152, 0.13, 0))
  ;[-1, 1].forEach((s) => torso.add(at(cyl(0.0055, 0.0055, 0.13, mats.white, 8), 0.155, 0.44, s * 0.045)))

  const head = new THREE.Group(); head.userData.live = true; head.position.set(0.02, 0.57, 0); torso.add(head)
  head.add(at(cyl(0.052, 0.058, 0.12, mats.skin), -0.005, 0, 0))
  const skull = sph(0.15, mats.skin, 32, 22); skull.scale.set(1.0, 1.1, 0.95); head.add(at(skull, 0, 0.2, 0))
  const jaw = sph(0.12, mats.skin, 24, 14); jaw.scale.set(1.05, 0.8, 0.95); head.add(at(jaw, 0.02, 0.13, 0))
  const hairTop = new THREE.Mesh(new THREE.SphereGeometry(0.16, 32, 12, 0, Math.PI * 2, 0, Math.PI * 0.5), mats.hair)
  hairTop.scale.set(1.0, 1.05, 0.98); head.add(at(hairTop, -0.022, 0.235, 0))
  const hairBack = new THREE.Mesh(new THREE.SphereGeometry(0.16, 24, 10, -Math.PI * 0.55, Math.PI * 1.1, Math.PI * 0.45, Math.PI * 0.35), mats.hair)
  hairBack.scale.set(1.0, 1.05, 0.98); head.add(at(hairBack, -0.022, 0.235, 0))
  const fringe = sph(0.07, mats.hair, 20, 12); fringe.scale.set(0.7, 0.45, 1.7); head.add(at(fringe, 0.11, 0.33, -0.02))
  const eyes = new THREE.Group(); eyes.userData.live = true; head.add(eyes)
  ;[-1, 1].forEach((s) => {
    eyes.add(at(sph(0.019, mats.white, 14, 10), 0.133, 0.215, s * 0.055))
    eyes.add(at(sph(0.012, mats.eye, 12, 8), 0.148, 0.215, s * 0.055))
  })
  ;[-1, 1].forEach((s) => head.add(at(box(0.012, 0.01, 0.045, mats.hair, 0.004), 0.143, 0.258, s * 0.056)))
  const nose = sph(0.022, mats.skin, 14, 10); nose.scale.set(1, 1.3, 0.9); head.add(at(nose, 0.152, 0.18, 0))
  head.add(at(box(0.008, 0.007, 0.05, M(0x5a2f28, { roughness: 0.6 }), 0.003), 0.143, 0.118, 0))
  // headphones: band, cushioned cups and a light ring in the player's colour
  const band = new THREE.Mesh(new THREE.TorusGeometry(0.175, 0.013, 12, 48, Math.PI), mats.phone)
  band.position.set(-0.01, 0.2, 0); band.rotation.y = Math.PI / 2; head.add(band)
  ;[-1, 1].forEach((s) => {
    const cup = cyl(0.06, 0.06, 0.05, mats.phone); cup.rotation.x = Math.PI / 2; head.add(at(cup, -0.01, 0.2, s * 0.172))
    const pad = new THREE.Mesh(new THREE.TorusGeometry(0.048, 0.014, 10, 28), mats.pants); head.add(at(pad, -0.01, 0.2, s * 0.15))
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.042, 0.005, 8, 32), mats.led); head.add(at(ring, -0.01, 0.2, s * 0.198))
    const plate = cyl(0.036, 0.036, 0.004, mats.accent); plate.rotation.x = Math.PI / 2; head.add(at(plate, -0.01, 0.2, s * 0.198))
  })

  const L1 = 0.29, L2 = 0.29
  const makeArm = (z) => {
    const shoulder = new THREE.Group(); shoulder.userData.live = true; shoulder.position.set(0, 0.5, z); torso.add(shoulder)
    shoulder.add(at(sph(0.064, mats.shirt), 0, 0, 0))
    shoulder.add(at(cap(0.054, L1 - 0.06, mats.shirt), 0, -L1 / 2, 0))
    const elbow = new THREE.Group(); elbow.userData.live = true; elbow.position.set(0, -L1, 0); shoulder.add(elbow)
    elbow.add(at(cap(0.047, L2 - 0.08, mats.shirt), 0, -L2 / 2 + 0.01, 0))
    elbow.add(at(cyl(0.05, 0.05, 0.035, mats.rib), 0, -L2 + 0.045, 0))
    const hand = sph(0.043, mats.skin); hand.scale.set(1.3, 0.75, 1.05); elbow.add(at(hand, 0, -L2 - 0.012, 0))
    const thumb = cap(0.012, 0.03, mats.skin); thumb.rotation.x = 0.9; elbow.add(at(thumb, 0.01, -L2 + 0.005, z > 0 ? -0.04 : 0.04))
    return { shoulder, elbow }
  }
  // +Z is the player's right when they face +X
  const player = { root, torso, head, eyes, mats, legs, arms: { L: makeArm(-0.255), R: makeArm(0.255) }, L1, L2 }
  if (!stand) poseLegs(player, SIT_ANGLE, SIT_ANGLE)
  return player
}

function makeMug(color) {
  const mug = new THREE.Group()
  const body = M(color, { roughness: 0.35 })
  mug.add(at(cyl(0.04, 0.036, 0.095, body), 0, 0.0475, 0))
  mug.add(at(cyl(0.034, 0.034, 0.002, M(0x2a1508, { roughness: 0.15 })), 0, 0.085, 0))
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.026, 0.008, 10, 24), body)
  mug.add(at(handle, 0.045, 0.05, 0))
  return mug
}

// Point a player's arm at a world-space target with a two-bone solve (shoulder, elbow). The player's matrices must be current:
// update them once before solving both arms.
const V = new THREE.Vector3()
const T = new THREE.Vector3()
export function solveArm(p, arm, target) {
  arm.shoulder.getWorldPosition(V); p.root.worldToLocal(V)
  T.copy(target); p.root.worldToLocal(T)
  const { L1, L2 } = p
  const dx = T.x - V.x, dy = T.y - V.y, dz = T.z - V.z
  const rh = Math.hypot(dx, dz)
  const d = clamp(Math.hypot(rh, dy), Math.abs(L1 - L2) + 0.02, L1 + L2 - 0.005)
  const base = Math.atan2(rh, -dy)
  const alpha = Math.acos(clamp((L1 * L1 + d * d - L2 * L2) / (2 * L1 * d), -1, 1))
  const a1 = base - alpha
  const er = L1 * Math.sin(a1), ey = V.y - L1 * Math.cos(a1)
  const a2 = Math.atan2(rh - er, -(T.y - ey))
  arm.shoulder.rotation.set(0, -Math.atan2(dz, Math.max(dx, 0.05)), a1 - p.torso.rotation.z, 'XYZ')
  arm.elbow.rotation.z = a2 - a1
}

// ── the scoreboard drawn above the table ─────────────────────────────────────
const BW = 1024 // the board is drawn in these units onto a canvas BOARD_SCALE as large
const BH = 400
const BOARD_SCALE = 0.75
function roundRect(g, x, y, w, h, r) {
  g.beginPath()
  g.moveTo(x + r, y)
  g.arcTo(x + w, y, x + w, y + h, r)
  g.arcTo(x + w, y + h, x, y + h, r)
  g.arcTo(x, y + h, x, y, r)
  g.arcTo(x, y, x + w, y, r)
  g.closePath()
}
function drawBoard(g, s) {
  g.setTransform(BOARD_SCALE, 0, 0, BOARD_SCALE, 0, 0)
  g.clearRect(0, 0, BW, BH)
  roundRect(g, 4, 4, BW - 8, BH - 8, 30)
  g.fillStyle = 'rgba(9,11,15,0.9)'
  g.fill()
  g.lineWidth = 3
  g.strokeStyle = '#262a33'
  g.stroke()

  g.textBaseline = 'middle'
  g.font = '600 34px "Sora Variable", sans-serif'
  // the title names whoever solved it first, in their colour
  g.fillStyle = s.winner === 'you' ? '#3de0ff' : s.winner === 'rival' ? '#b8a4ff' : '#e8eaef'
  g.textAlign = 'left'
  g.fillText(s.winner === 'you' ? 'You solved it first' : s.winner === 'rival' ? 'Rival solved it first' : 'Ranked duel', 48, 70)
  g.font = '500 32px "JetBrains Mono Variable", monospace'
  g.fillStyle = '#8b919c'
  g.textAlign = 'right'
  const mm = String(Math.floor(s.clock / 60)).padStart(2, '0')
  const ss = String(Math.floor(s.clock % 60)).padStart(2, '0')
  g.fillText(`${mm}:${ss}`, BW - 48, 70)
  g.fillStyle = '#1d2027'
  g.fillRect(48, 118, BW - 96, 2)

  const row = (y, name, lang, color, p, done) => {
    g.fillStyle = color
    g.beginPath(); g.arc(60, y, 9, 0, Math.PI * 2); g.fill()
    g.textAlign = 'left'
    g.font = '600 32px "Sora Variable", sans-serif'
    g.fillStyle = '#e8eaef'
    g.fillText(name, 84, y)
    g.font = '400 24px "JetBrains Mono Variable", monospace'
    g.fillStyle = '#6f7682'
    g.fillText(lang, 204, y + 2)
    const bx = 400, bw = 380, bh = 14
    roundRect(g, bx, y - bh / 2, bw, bh, 7)
    g.fillStyle = '#191c22'
    g.fill()
    const fw = Math.max(bh, bw * clamp(p, 0, 1))
    roundRect(g, bx, y - bh / 2, fw, bh, 7)
    g.fillStyle = done ? '#3ddc97' : color
    g.fill()
    g.textAlign = 'right'
    g.font = '500 28px "JetBrains Mono Variable", monospace'
    g.fillStyle = done ? '#3ddc97' : '#8b919c'
    g.fillText(done ? '5/5' : `${Math.round(p * 100)}%`, BW - 48, y)
  }
  row(206, 'You', s.youLang, '#3de0ff', s.you, s.youDone)
  row(316, 'Rival', s.rivalLang, '#9b7bff', s.rival, s.rivalDone)
}

export function createDuel() {
  const group = new THREE.Group()
  const blob = blobTexture()
  const spotMat = new THREE.MeshBasicMaterial({ map: blob, transparent: true, opacity: 0.65, depthWrite: false, color: 0x000000 })
  const shadowSpot = (w, d, x, z) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), spotMat)
    m.rotation.x = -Math.PI / 2
    return at(m, x, 0.0515, z)
  }

  // a low round platform, its rim split between the two players' colours
  const platform = new THREE.Group()
  const floor = at(cyl(1.36, 1.39, 0.05, M(0x0b0d12, { roughness: 0.55, metalness: 0.35 }), 96), 0, 0.025, 0)
  floor.receiveShadow = true
  platform.add(floor)
  const rim = (color, start) => {
    const m = new THREE.Mesh(new THREE.TorusGeometry(1.375, 0.006, 8, 128, Math.PI), glow(color))
    m.rotation.x = Math.PI / 2; m.rotation.z = start; m.position.y = 0.05
    return m
  }
  platform.add(rim(CYAN, Math.PI / 2), rim(VIOLET, -Math.PI / 2))
  // two faint rings inside the rim, like markings on a stage
  ;[1.05, 0.6].forEach((r) => {
    const ring = new THREE.Mesh(new THREE.RingGeometry(r - 0.003, r + 0.003, 128), new THREE.MeshBasicMaterial({ color: 0x1a1e27 }))
    ring.rotation.x = -Math.PI / 2; ring.position.y = 0.0505
    platform.add(ring)
  })
  platform.add(shadowSpot(2.3, 1.4, 0, 0), shadowSpot(0.85, 0.85, -1.04, 0), shadowSpot(0.85, 0.85, 1.04, 0))

  // the table: a dark top with a light strip along each player's edge
  const table = new THREE.Group()
  const tableMat = M(0x15171d, { roughness: 0.38, metalness: 0.4 })
  const legMat = M(0x2c2f37, { metalness: 0.8, roughness: 0.3 })
  const top = at(box(1.7, 0.035, 0.84, tableMat, 0.014), 0, TABLE_TOP - 0.0175, 0)
  table.add(top)
  ;[[-0.78, -0.36], [-0.78, 0.36], [0.78, -0.36], [0.78, 0.36]].forEach(([x, z]) => {
    table.add(at(cyl(0.022, 0.022, TABLE_TOP - 0.035), x, (TABLE_TOP - 0.035) / 2 + 0.05, z))
    table.add(at(cyl(0.035, 0.035, 0.012), x, 0.056, z))
  })
  table.children.forEach((o) => { if (o !== top) o.material = legMat })
  table.add(at(box(0.004, 0.002, 0.78, new THREE.MeshBasicMaterial({ color: 0x2a3140 }), 0.001), 0, TABLE_TOP + 0.001, 0))
  table.add(at(box(0.006, 0.008, 0.8, glow(CYAN), 0.002), -0.852, TABLE_TOP - 0.03, 0))
  table.add(at(box(0.006, 0.008, 0.8, glow(VIOLET), 0.002), 0.852, TABLE_TOP - 0.03, 0))
  const mugA = makeMug(0xdfe2e7); mugA.position.set(-0.66, TABLE_TOP, 0.32); mugA.rotation.y = -0.6; table.add(mugA)
  const mugB = makeMug(0x2b2e36); mugB.position.set(0.66, TABLE_TOP, -0.32); mugB.rotation.y = 2.4; table.add(mugB)

  // where the laptops go: each faces its player
  const slotA = new THREE.Object3D(); slotA.position.set(-0.55, TABLE_TOP, 0); slotA.rotation.y = -Math.PI / 2; slotA.scale.setScalar(LAPTOP_SCALE)
  const slotB = new THREE.Object3D(); slotB.position.set(0.55, TABLE_TOP, 0); slotB.rotation.y = Math.PI / 2; slotB.scale.setScalar(LAPTOP_SCALE)

  const chairA = makeChair(CYAN); chairA.position.set(-1.04, 0.05, 0)
  const chairB = makeChair(VIOLET); chairB.position.set(1.04, 0.05, 0); chairB.rotation.y = Math.PI
  const you = makePlayer({ shirt: 0x1f232b, skin: SKIN.you, hair: 0x1b1410, accent: CYAN })
  you.root.position.set(-1.0, 0.55, 0)
  const rival = makePlayer({ shirt: 0x2a2233, skin: SKIN.rival, hair: 0x0c0a09, accent: VIOLET })
  rival.root.position.set(1.0, 0.55, 0); rival.root.rotation.y = Math.PI

  // the scoreboard: a canvas on a plane above the table, kept square to the viewer by arena.js
  const boardCanvas = document.createElement('canvas')
  boardCanvas.width = Math.round(BW * BOARD_SCALE)
  boardCanvas.height = Math.round(BH * BOARD_SCALE)
  const bctx = boardCanvas.getContext('2d')
  const boardTex = new THREE.CanvasTexture(boardCanvas)
  boardTex.colorSpace = THREE.SRGBColorSpace
  boardTex.anisotropy = 8
  const board = new THREE.Mesh(new THREE.PlaneGeometry(1.25, 1.25 * (BH / BW)), new THREE.MeshBasicMaterial({ map: boardTex, transparent: true, toneMapped: false, depthWrite: false }))
  board.position.set(0, 1.8, 0)
  board.renderOrder = 2

  group.add(platform, table, slotA, slotB, chairA, chairB, you.root, rival.root, board)
  // every piece is built from many small meshes; merge the still ones so the scene costs a few dozen draws, not a few hundred
  ;[platform, table, chairA, chairB, you.root, rival.root].forEach((o) => bake(o))

  // everything solid casts a shadow; the floor, table and people also take them
  group.traverse((o) => {
    if (!o.isMesh || o === board || o.material.transparent || o.material.isMeshBasicMaterial) return
    o.castShadow = true
    o.receiveShadow = true
  })

  // pieces arrive in this order as the duel forms: [object, from, to] on the 0..1 formation scale
  const parts = [[platform, 0.15, 0.55], [table, 0.25, 0.65], [chairA, 0.35, 0.75], [chairB, 0.35, 0.75], [you.root, 0.45, 0.9], [rival.root, 0.45, 0.9], [board, 0.75, 1.0]]

  // ── animation ──────────────────────────────────────────────────────────
  const K = new THREE.Vector3()

  // a glance up at the other player every few seconds: 0, then up to 1, then back
  const glanceAt = (t, every, offset) => { const u = (t + offset) % every; return clamp((u - (every - 2.2)) / 0.45, 0, 1) * clamp((every - u) / 0.6, 0, 1) }
  const ease = (x) => { const u = clamp(x, 0, 1); return u * u * (3 - 2 * u) }

  // Where each player sits: their chair, their laptop, and which way they swivel to face the room when they celebrate. Each hand
  // eases towards the key it last struck (in the laptop's own units).
  const seats = [
    { p: you, chair: chairA, slot: slotA, cx: -1.04, base: 0, dir: -1, phase: 0 },
    { p: rival, chair: chairB, slot: slotB, cx: 1.04, base: Math.PI, dir: 1, phase: 3.1 },
  ].map((s) => ({ ...s, hand: { L: new THREE.Vector3(-0.75, 0.6, -0.3), R: new THREE.Vector3(0.75, 0.6, -0.3) }, lastT: 0 }))
  const U = new THREE.Vector3(), W = new THREE.Vector3()

  // act: { hands (the keys struck, from arena.js), win (seconds since this player finished first, or -1), lose (seconds since the
  // other player did, or -1) }
  function animatePlayer(seat, t, act, still) {
    const { p, chair, slot } = seat
    const dt = clamp(t - seat.lastT, 0, 0.05)
    seat.lastT = t
    // Finishing first: roll back a little and swivel the chair to face the room (0 to 0.3 s), stand up a step in front of it (to
    // 0.65 s), jump about three times with both arms up, crouching at each take-off and landing (to 2.45 s), sit back down (to
    // 2.85 s) and turn back to the table (to 3.2 s). arena.js starts the next round no sooner than 3.4 s.
    const k = act.win
    const on = k >= 0 && !still
    const turnE = on ? ease(k / 0.3) * (1 - ease((k - 2.85) / 0.35)) : 0
    const standE = on ? ease((k - 0.3) / 0.35) * (1 - ease((k - 2.45) / 0.4)) : 0
    const up = on ? ease((k - 0.15) / 0.4) * (1 - ease((k - 2.4) / 0.45)) : 0
    let hop = 0
    let crouch = 0
    if (on && k > 0.7 && k < 2.45) {
      const lift = Math.sin(Math.PI * (((k - 0.7) / 0.5) % 1))
      hop = lift * 0.24 * standE
      crouch = Math.pow(1 - lift, 3) * standE
    }
    // finishing second: the head drops for a moment
    const droop = act.lose >= 0 && !still ? ease(act.lose / 0.5) * (1 - ease((act.lose - 2.4) / 0.6)) : 0
    const turn = seat.base + seat.dir * turnE * (Math.PI / 2)
    const cx = seat.cx - Math.cos(seat.base) * 0.08 * turnE
    chair.rotation.y = turn
    chair.position.x = cx
    p.root.rotation.y = turn
    // seated on the chair, or standing a step in front of it, clear of the table; a crouch lowers the hips as the knees bend
    const out = 0.04 + standE * 0.51
    p.root.position.set(cx + Math.cos(turn) * out, 0.55 + standE * (0.05 + STAND_HEIGHT - 0.55) + hop - crouch * 0.1, -Math.sin(turn) * out)
    poseLegs(p, (1 - standE) * SIT_ANGLE + crouch * 0.5, (1 - standE) * SIT_ANGLE + crouch * 0.95)

    const glance = (1 - up) * (1 - droop) * glanceAt(t, 8.5, seat.phase)
    p.torso.rotation.z = (-0.1 + glance * 0.06 + Math.sin(t * 0.9 + seat.phase) * 0.012) * (1 - up) + up * 0.04 - droop * 0.06 - crouch * 0.2
    p.head.rotation.z = (-0.16 + glance * 0.36 + Math.sin(t * 1.6 + seat.phase) * 0.02) * (1 - up) + up * 0.3 - droop * 0.22
    p.head.rotation.y = Math.sin(t * 0.7 + seat.phase) * 0.05 + up * Math.sin(t * 5) * 0.12
    p.eyes.scale.y = (t * 0.37 + seat.phase) % 1 < 0.035 ? 0.15 : 1
    // the headphone light flares while this player celebrates
    p.mats.accent.emissiveIntensity = 0.6 + up * 1.6
    p.root.updateMatrixWorld(true)

    ;['L', 'R'].forEach((side) => {
      // over the key this hand last struck, dipping onto it for a moment as it presses
      const h = act.hands[side]
      const since = t - h.t
      const press = since >= 0 && since < 0.09 ? 1 - since / 0.09 : 0
      U.set(h.x, 0.6 - press * 0.1, h.z)
      seat.hand[side].lerp(U, 1 - Math.exp(-dt * 30))
      K.copy(seat.hand[side])
      slot.localToWorld(K)
      if (up > 0) {
        // both arms flung up in a V, pumping
        W.set(0.08, 0.98 + Math.sin(k * 9) * 0.04, (side === 'L' ? -1 : 1) * 0.4)
        p.root.localToWorld(W)
        K.lerp(W, up)
      }
      solveArm(p, p.arms[side], K)
    })
  }
  const IDLE = { hands: { L: { x: -0.75, z: -0.3, t: -9 }, R: { x: 0.75, z: -0.3, t: -9 } }, win: -1, lose: -1 }

  let boardKey = ''
  return {
    group, slotA, slotB, parts, board,
    /** Formation 0..1 brings the pieces in; t is the scene clock; actA/actB say what each player is doing (see animatePlayer). */
    update(formation, t, still, actA = IDLE, actB = IDLE) {
      parts.forEach(([o, a, b]) => {
        const u = clamp((formation - a) / (b - a), 0, 1)
        const s = still ? (u > 0 ? 1 : 0) : 1 + 2.2 * Math.pow(u - 1, 3) + 1.2 * Math.pow(u - 1, 2)
        o.scale.setScalar(Math.max(0.0001, u === 0 ? 0 : s))
        o.visible = u > 0
      })
      group.updateMatrixWorld(true)
      if (formation > 0.4) {
        animatePlayer(seats[0], still ? 0 : t, actA, still)
        animatePlayer(seats[1], still ? 0 : t, actB, still)
      } else seats.forEach((st) => { st.chair.rotation.y = st.base; st.chair.position.x = st.cx })
    },
    /** Redraw the scoreboard when what it shows has changed. */
    setScore(s, fontsReady) {
      s = { ...s, you: Math.round(s.you * 50) / 50, rival: Math.round(s.rival * 50) / 50 }
      const key = [s.you, s.rival, s.youDone, s.rivalDone, Math.floor(s.clock), s.youLang, s.rivalLang, s.winner, fontsReady].join('|')
      if (key === boardKey || !fontsReady) return
      boardKey = key
      drawBoard(bctx, s)
      boardTex.needsUpdate = true
    },
    dispose() { blob.dispose(); boardTex.dispose(); spotMat.dispose() },
  }
}
