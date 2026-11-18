// The podium: after the duel, the standings. The winner stands on the top step holding a trophy overhead, second place one step
// down, third place on the lowest step, with confetti falling over them.
//
// Built from the same parts as the duel (three/duel.js): the same standing figures, the same platform and colours. You are the
// winner in cyan, the rival from the duel is second in violet, and a third player in white is third. Units are metres; arena.js
// places and scales the group exactly where the duel stood.

import * as THREE from 'three'
import { M, box, cyl, glow, at, bake, blobTexture, makePlayer, solveArm, CYAN, VIOLET, SKIN, STAND_HEIGHT } from './duel'

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v))
const WHITE = 0xdfe4ec
const GREEN = 0x3ddc97

// the steps, left to right: second, first, third (x, height, colour)
const STEPS = [
  { place: 2, x: -0.8, h: 0.34, color: VIOLET },
  { place: 1, x: 0, h: 0.5, color: CYAN },
  { place: 3, x: 0.8, h: 0.2, color: WHITE },
]
const STEP_W = 0.78
const STEP_D = 0.7
const FLOOR = 0.05 // the platform's top
const HIPS = STAND_HEIGHT // a standing player's root height above their feet

function makeTrophy() {
  const metal = M(0xe9edf3, { metalness: 1, roughness: 0.22, side: THREE.DoubleSide })
  const trophy = new THREE.Group()
  const profile = [[0, 0], [0.06, 0], [0.06, 0.018], [0.03, 0.03], [0.014, 0.075], [0.02, 0.1], [0.07, 0.125], [0.082, 0.19], [0.078, 0.215]]
  trophy.add(new THREE.Mesh(new THREE.LatheGeometry(profile.map(([x, y]) => new THREE.Vector2(x, y)), 32), metal))
  ;[-1, 1].forEach((s) => {
    const handle = new THREE.Mesh(new THREE.TorusGeometry(0.03, 0.006, 8, 20, Math.PI), metal)
    handle.rotation.z = s > 0 ? -Math.PI / 2 : Math.PI / 2
    trophy.add(at(handle, s * 0.082, 0.165, 0))
  })
  const band = new THREE.Mesh(new THREE.TorusGeometry(0.0805, 0.004, 8, 40), glow(CYAN))
  band.rotation.x = Math.PI / 2
  trophy.add(at(band, 0, 0.175, 0))
  return trophy
}

function labelTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 256
  const t = new THREE.CanvasTexture(c)
  t.colorSpace = THREE.SRGBColorSpace
  return { canvas: c, texture: t }
}

export function createPodium() {
  const group = new THREE.Group()
  const blob = blobTexture()
  const spotMat = new THREE.MeshBasicMaterial({ map: blob, transparent: true, opacity: 0.6, depthWrite: false, color: 0x000000 })

  // the platform, as under the duel
  const platform = new THREE.Group()
  platform.add(at(cyl(1.36, 1.39, 0.05, M(0x0b0d12, { roughness: 0.55, metalness: 0.35 }), 96), 0, 0.025, 0))
  ;[[CYAN, Math.PI / 2], [VIOLET, -Math.PI / 2]].forEach(([color, start]) => {
    const rim = new THREE.Mesh(new THREE.TorusGeometry(1.375, 0.006, 8, 128, Math.PI), glow(color))
    rim.rotation.x = Math.PI / 2; rim.rotation.z = start; rim.position.y = FLOOR
    platform.add(rim)
  })
  ;[1.05, 0.6].forEach((r) => {
    const ring = new THREE.Mesh(new THREE.RingGeometry(r - 0.003, r + 0.003, 128), new THREE.MeshBasicMaterial({ color: 0x1a1e27 }))
    ring.rotation.x = -Math.PI / 2; ring.position.y = FLOOR + 0.0005
    platform.add(ring)
  })
  const spot = new THREE.Mesh(new THREE.PlaneGeometry(2.9, 1.3), spotMat)
  spot.rotation.x = -Math.PI / 2; spot.position.y = FLOOR + 0.0015
  platform.add(spot)

  // the steps: a dark block each, its place number on the front and a light strip in its player's colour along the top edge
  const stepMat = M(0x15171d, { roughness: 0.38, metalness: 0.4 })
  const labels = []
  const steps = STEPS.map((st) => {
    const step = new THREE.Group()
    step.position.set(st.x, FLOOR, 0)
    step.add(at(box(STEP_W, st.h, STEP_D, stepMat, 0.02), 0, st.h / 2, 0))
    step.add(at(box(STEP_W - 0.04, 0.012, 0.012, glow(st.color), 0.004), 0, st.h - 0.012, STEP_D / 2 + 0.002))
    const label = labelTexture()
    labels.push({ ...label, place: st.place })
    const size = Math.min(0.26, st.h * 0.8)
    const face = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: label.texture, transparent: true, toneMapped: false, depthWrite: false }))
    step.add(at(face, 0, st.h * 0.46, STEP_D / 2 + 0.003))
    return step
  })

  // the three players, standing on their steps and turned a little towards the winner
  const winner = makePlayer({ shirt: 0x1f232b, skin: SKIN.you, hair: 0x1b1410, accent: CYAN, stand: true })
  const second = makePlayer({ shirt: 0x2a2233, skin: SKIN.rival, hair: 0x0c0a09, accent: VIOLET, stand: true })
  const third = makePlayer({ shirt: 0x262a31, skin: SKIN.third, hair: 0x5a3a22, accent: WHITE, stand: true })
  const stand = (p, st, turn) => {
    p.root.position.set(st.x, FLOOR + st.h + HIPS, 0.02)
    p.root.rotation.y = -Math.PI / 2 + turn
    p.baseY = p.root.position.y
  }
  stand(second, STEPS[0], 0.28)
  stand(winner, STEPS[1], 0)
  stand(third, STEPS[2], -0.28)
  const trophy = makeTrophy()
  trophy.scale.setScalar(1.25)
  trophy.userData.live = true
  winner.root.add(trophy)

  // confetti in the players' colours, falling and turning over the podium (one draw for all of it)
  const COUNT = 150
  const confetti = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.03, 0.05), new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, toneMapped: false }), COUNT)
  confetti.frustumCulled = false
  const palette = [CYAN, VIOLET, WHITE, GREEN].map((c) => new THREE.Color(c))
  const flakes = []
  for (let i = 0; i < COUNT; i++) {
    const r = 1.25 * Math.sqrt(Math.random())
    const a = Math.random() * Math.PI * 2
    flakes.push({ x: Math.cos(a) * r, z: Math.sin(a) * r * 0.7, speed: 0.22 + Math.random() * 0.25, phase: Math.random() * 3, spin: 1.5 + Math.random() * 3, sway: Math.random() * 6 })
    confetti.setColorAt(i, palette[i % palette.length])
  }
  const confettiGroup = new THREE.Group()
  confettiGroup.add(confetti)

  group.add(platform, ...steps, winner.root, second.root, third.root, confettiGroup)
  ;[platform, ...steps, winner.root, second.root, third.root].forEach((o) => bake(o))
  group.traverse((o) => {
    if (!o.isMesh || o.isInstancedMesh || o.material.transparent || o.material.isMeshBasicMaterial) return
    o.castShadow = true
    o.receiveShadow = true
  })

  // pieces arrive lowest step first, then the players from third to the winner, then the confetti
  const parts = [
    [platform, 0.1, 0.5], [steps[2], 0.2, 0.55], [steps[0], 0.27, 0.62], [steps[1], 0.34, 0.69],
    [third.root, 0.45, 0.8], [second.root, 0.52, 0.87], [winner.root, 0.6, 0.95], [confettiGroup, 0.85, 1],
  ]

  // ── animation ──────────────────────────────────────────────────────────
  const K = new THREE.Vector3()
  const reach = (p, side, x, y, z) => { K.set(x, y, z); p.root.localToWorld(K); solveArm(p, p.arms[side], K) }
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), pos = new THREE.Vector3(), one = new THREE.Vector3(1, 1, 1)

  function animate(t) {
    // the winner hops, arms up in a V, the trophy held high in the right hand and pumped
    const hop = Math.abs(Math.sin(t * 3.2))
    winner.root.position.y = winner.baseY + hop * 0.03
    winner.torso.rotation.z = 0.02 * Math.sin(t * 1.3)
    winner.head.rotation.z = 0.2
    winner.head.rotation.y = Math.sin(t * 0.8) * 0.12
    const lift = 1.0 + Math.sin(t * 6.4) * 0.035
    winner.root.updateMatrixWorld(true)
    reach(winner, 'R', 0.06, lift, 0.34)
    reach(winner, 'L', 0.06, 0.95 + Math.sin(t * 6.4 + 1.2) * 0.03, -0.43)
    trophy.position.set(0.06, lift + 0.01, 0.34)

    // second place claps, looking up at the winner
    second.torso.rotation.z = 0.03
    second.head.rotation.y = 0.35
    second.head.rotation.z = 0.12 + Math.sin(t * 1.1) * 0.02
    const clap = 0.025 + 0.06 * (0.5 + 0.5 * Math.sin(t * 7.5))
    second.root.updateMatrixWorld(true)
    reach(second, 'L', 0.3, 0.33, -clap)
    reach(second, 'R', 0.3, 0.33, clap)

    // third place waves with the outer (left) hand, so the wave stays clear of the winner
    third.torso.rotation.z = 0.01
    third.head.rotation.y = -0.35
    third.head.rotation.z = 0.1
    third.root.updateMatrixWorld(true)
    reach(third, 'R', 0.03, -0.06, 0.28)
    reach(third, 'L', 0.1, 0.92, -0.36 - Math.sin(t * 5) * 0.09)

    // blinks
    ;[winner, second, third].forEach((p, i) => { p.eyes.scale.y = (t * 0.37 + i * 0.31) % 1 < 0.035 ? 0.15 : 1 })
  }

  function fall(t) {
    for (let i = 0; i < COUNT; i++) {
      const f = flakes[i]
      const y = 3.0 - ((t * f.speed + f.phase) % 1) * 2.9
      pos.set(f.x + Math.sin(t * 0.9 + f.sway) * 0.06, y, f.z + Math.cos(t * 0.7 + f.sway) * 0.05)
      e.set(t * f.spin, t * f.spin * 0.7 + f.sway, 0)
      q.setFromEuler(e)
      m4.compose(pos, q, one)
      confetti.setMatrixAt(i, m4)
    }
    confetti.instanceMatrix.needsUpdate = true
  }

  let labelsDrawn = false
  function drawLabels() {
    labels.forEach(({ canvas, texture, place }) => {
      const g = canvas.getContext('2d')
      g.clearRect(0, 0, 256, 256)
      g.fillStyle = 'rgba(232,234,239,0.9)'
      g.font = '600 200px "Sora Variable", sans-serif'
      g.textAlign = 'center'
      g.textBaseline = 'middle'
      g.fillText(String(place), 128, 140)
      texture.needsUpdate = true
    })
    labelsDrawn = true
  }

  return {
    group, parts,
    /** Formation 0..1 brings the pieces in; t is the scene clock; still (reduced motion) holds every pose. */
    update(formation, t, still, fontsReady) {
      if (!labelsDrawn && fontsReady) drawLabels()
      parts.forEach(([o, a, b]) => {
        const u = clamp((formation - a) / (b - a), 0, 1)
        const s = still ? (u > 0 ? 1 : 0) : 1 + 2.2 * Math.pow(u - 1, 3) + 1.2 * Math.pow(u - 1, 2)
        o.scale.setScalar(Math.max(0.0001, u === 0 ? 0 : s))
        o.visible = u > 0
      })
      group.updateMatrixWorld(true)
      if (formation > 0.4) animate(still ? 0 : t)
      if (confettiGroup.visible) fall(still ? 0 : t)
    },
    dispose() { blob.dispose(); spotMat.dispose(); labels.forEach((l) => l.texture.dispose()) },
  }
}
