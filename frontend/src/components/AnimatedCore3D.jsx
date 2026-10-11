import React, { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import * as THREE from 'three'

// Premium Glass Material (MeshPhysicalMaterial) for a highly professional look
const glassMaterial = new THREE.MeshPhysicalMaterial({
  color: '#0ea5e9',
  metalness: 0.1,
  roughness: 0.05,
  transmission: 0.95, // Glass-like transparency
  ior: 1.5,
  thickness: 2,
  transparent: true,
  opacity: 1
})

const purpleGlass = new THREE.MeshPhysicalMaterial({
  color: '#a855f7',
  metalness: 0.1,
  roughness: 0.05,
  transmission: 0.95,
  ior: 1.5,
  thickness: 2,
  transparent: true,
  opacity: 1
})

function FloatingObject({ geometry, material, position, speed, rotationIntensity, floatIntensity, scale }) {
  const meshRef = useRef()
  
  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * 0.15
      meshRef.current.rotation.y += delta * 0.2
    }
  })

  return (
    // Float adds that ultra-smooth, organic "breathing" animation
    <Float speed={speed} rotationIntensity={rotationIntensity} floatIntensity={floatIntensity}>
      <mesh ref={meshRef} geometry={geometry} material={material} position={position} scale={scale} />
    </Float>
  )
}

export default function AnimatedCore3D() {
  const torus = useMemo(() => new THREE.TorusGeometry(1.2, 0.4, 32, 64), [])
  const icosahedron = useMemo(() => new THREE.IcosahedronGeometry(1.2, 0), [])
  const octahedron = useMemo(() => new THREE.OctahedronGeometry(1.2, 0), [])
  const box = useMemo(() => new THREE.BoxGeometry(1.5, 1.5, 1.5), [])

  return (
    // 'absolute' ensures these objects stay in the hero section and don't scroll over cards!
    <div className="absolute inset-0 z-0 pointer-events-none">
      {/* alpha: true ensures the beautiful dark Aurora background shows through! */}
      <Canvas gl={{ antialias: true, alpha: true }} camera={{ position: [0, 0, 10], fov: 45 }} dpr={[1, 1.5]}>
        
        {/* Soft, professional lighting to catch the glass highlights */}
        <ambientLight intensity={1.5} />
        <directionalLight position={[10, 10, 5]} intensity={3} color="#ffffff" />
        <directionalLight position={[-10, -10, -5]} intensity={2} color="#a855f7" />
        <pointLight position={[0, 0, 5]} intensity={2} color="#0ea5e9" />

        {/* Floating Glass Tech Objects perfectly scattered around the edges */}
        <FloatingObject geometry={torus} material={glassMaterial} position={[-7, 3, -2]} speed={1.5} rotationIntensity={1} floatIntensity={2} scale={1} />
        <FloatingObject geometry={icosahedron} material={purpleGlass} position={[7, 2, -3]} speed={2} rotationIntensity={1.5} floatIntensity={1.5} scale={1.2} />
        <FloatingObject geometry={octahedron} material={glassMaterial} position={[-6, -4, -4]} speed={1.2} rotationIntensity={0.8} floatIntensity={1} scale={1.5} />
        <FloatingObject geometry={box} material={purpleGlass} position={[6, -3, 1]} speed={1.8} rotationIntensity={1.2} floatIntensity={2} scale={0.7} />
        
        {/* A subtle, massive background ring wrapping the scene */}
        <Float speed={0.5} rotationIntensity={0.2} floatIntensity={0.5}>
          <mesh geometry={new THREE.TorusGeometry(9, 0.02, 16, 100)} position={[0, 0, -8]} rotation={[Math.PI/4, 0, 0]}>
            <meshBasicMaterial color="#a855f7" transparent opacity={0.15} />
          </mesh>
        </Float>
      </Canvas>
    </div>
  )
}
