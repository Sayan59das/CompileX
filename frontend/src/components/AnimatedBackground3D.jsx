import React, { useState, useEffect } from 'react'

export default function AnimatedBackground3D() {
  const [mousePos, setMousePos] = useState({ x: -1000, y: -1000 })
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const handleMouseMove = (e) => {
      setMousePos({ x: e.clientX, y: e.clientY })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  if (!mounted) return null

  return (
    <div className="fixed inset-0 w-full h-full z-0 pointer-events-none bg-[#010204] overflow-hidden">
      
      {/* 
        1. The Base Grid:
        Clean, minimalist engineering grid pattern
      */}
      <div 
        className="absolute inset-0"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(255, 255, 255, 0.04) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.04) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
          maskImage: 'radial-gradient(ellipse at 50% 40%, rgba(0,0,0,1) 20%, rgba(0,0,0,0) 80%)',
          WebkitMaskImage: 'radial-gradient(ellipse at 50% 40%, rgba(0,0,0,1) 20%, rgba(0,0,0,0) 80%)'
        }}
      />
      
      {/* 
        2. Interactive Mouse Spotlight:
        High-end professional interaction that illuminates the grid
      */}
      <div 
        className="absolute inset-0 transition-opacity duration-300"
        style={{
          background: `radial-gradient(600px circle at ${mousePos.x}px ${mousePos.y}px, rgba(59, 130, 246, 0.12), transparent 40%)`,
        }}
      />

      {/* 
        3. Subtle Ambient Glows:
        Provides depth without being distracting
      */}
      <div className="absolute top-[10%] left-[20%] w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-[120px] animate-pulse-slow mix-blend-screen" />
      <div className="absolute bottom-[10%] right-[10%] w-[600px] h-[600px] bg-cyan-500/5 rounded-full blur-[150px] animate-pulse mix-blend-screen" style={{ animationDelay: '2s' }} />
      <div className="absolute top-[40%] left-[60%] w-[400px] h-[400px] bg-purple-500/5 rounded-full blur-[120px] animate-pulse-slow mix-blend-screen" style={{ animationDelay: '4s' }} />

      {/* 
        4. Slow-moving vertical data lines for subtle dynamism 
      */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-0 left-[20%] w-[1px] h-full bg-gradient-to-b from-transparent via-blue-500 to-transparent animate-scan-line" style={{ animationDuration: '8s' }} />
        <div className="absolute top-0 left-[60%] w-[1px] h-full bg-gradient-to-b from-transparent via-cyan-500 to-transparent animate-scan-line" style={{ animationDuration: '12s', animationDelay: '3s' }} />
        <div className="absolute top-0 left-[80%] w-[1px] h-full bg-gradient-to-b from-transparent via-purple-500 to-transparent animate-scan-line" style={{ animationDuration: '10s', animationDelay: '1s' }} />
      </div>
    </div>
  )
}
