import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Line, Stars } from '@react-three/drei'
import * as THREE from 'three'

function GlobeGeometry() {
  const meshRef = useRef()
  const pointsRef = useRef()

  // Generate points on a sphere using Fibonacci lattice
  const [positions] = useMemo(() => {
    const count = 4000
    const pos = new Float32Array(count * 3)
    const phi = Math.PI * (3 - Math.sqrt(5)) // Golden angle

    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2 // y goes from 1 to -1
      const radius = Math.sqrt(1 - y * y) // radius at y

      const theta = phi * i // golden angle increment

      const r = 5
      pos[i * 3] = r * Math.cos(theta) * radius
      pos[i * 3 + 1] = r * y
      pos[i * 3 + 2] = r * Math.sin(theta) * radius
    }
    return [pos]
  }, [])

  // Create a perfectly circular texture for the points
  const circleTexture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 64
    const context = canvas.getContext('2d')
    const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32)
    gradient.addColorStop(0, 'rgba(255,255,255,1)')
    gradient.addColorStop(0.5, 'rgba(255,255,255,0.8)')
    gradient.addColorStop(1, 'rgba(255,255,255,0)')
    context.fillStyle = gradient
    context.fillRect(0, 0, 64, 64)
    return new THREE.CanvasTexture(canvas)
  }, [])

  useFrame((state, delta) => {
    if (meshRef.current && pointsRef.current) {
      meshRef.current.rotation.y += delta * 0.05
      pointsRef.current.rotation.y += delta * 0.05
      
      // Gentle tilt
      const tilt = Math.sin(state.clock.elapsedTime * 0.5) * 0.1
      meshRef.current.rotation.x = 0.2 + tilt
      pointsRef.current.rotation.x = 0.2 + tilt
    }
  })

  return (
    <group>
      {/* Wireframe Core */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[4.95, 32, 32]} />
        <meshBasicMaterial 
          color="#1e3a8a" 
          wireframe 
          transparent 
          opacity={0.15} 
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Point Shell */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute 
            attach="attributes-position" 
            count={positions.length / 3} 
            array={positions} 
            itemSize={3} 
          />
        </bufferGeometry>
        <pointsMaterial 
          size={0.06} 
          color="#06b6d4" 
          transparent 
          opacity={0.6} 
          map={circleTexture}
          blending={THREE.AdditiveBlending} 
          depthWrite={false}
        />
      </points>
    </group>
  )
}

function ConnectionArcs() {
  const groupRef = useRef()

  // Generate random bezier curves connecting points on the globe
  const arcs = useMemo(() => {
    const lines = []
    for (let i = 0; i < 15; i++) {
      const start = new THREE.Vector3().randomDirection().multiplyScalar(5)
      const end = new THREE.Vector3().randomDirection().multiplyScalar(5)
      
      // Control point is pushed outwards
      const mid = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(5 + Math.random() * 2)
      
      const curve = new THREE.QuadraticBezierCurve3(start, mid, end)
      const points = curve.getPoints(30)
      lines.push(points)
    }
    return lines
  }, [])

  useFrame((state, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.05
      groupRef.current.rotation.x = 0.2 + Math.sin(state.clock.elapsedTime * 0.5) * 0.1
    }
  })

  return (
    <group ref={groupRef}>
      {arcs.map((points, i) => (
        <Line 
          key={i}
          points={points}
          color="#3b82f6"
          lineWidth={2}
          transparent
          opacity={0.4}
        />
      ))}
    </group>
  )
}

export default function AnimatedGlobe3D() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none bg-[#0A0A10]">
      <Canvas camera={{ position: [0, 0, 12], fov: 45 }}>
        <ambientLight intensity={0.5} />
        {/* Shift the entire globe and arcs to the right side of the screen */}
        <group position={[6, -1, 0]}>
          <GlobeGeometry />
          <ConnectionArcs />
        </group>
        <Stars radius={50} depth={50} count={3000} factor={3} saturation={0} fade speed={1} />
      </Canvas>
    </div>
  )
}
