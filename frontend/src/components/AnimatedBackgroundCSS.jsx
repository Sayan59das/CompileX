import React, { useEffect, useRef } from 'react'

export default function AnimatedBackgroundCSS() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d', { alpha: false })
    let animationFrameId
    
    // Smooth mouse tracking
    let mouse = { 
      x: window.innerWidth / 2, 
      y: window.innerHeight / 2, 
      targetX: window.innerWidth / 2, 
      targetY: window.innerHeight / 2 
    }
    
    const handleMouseMove = (e) => {
      mouse.targetX = e.clientX
      mouse.targetY = e.clientY
    }
    const handleMouseLeave = () => {
      mouse.targetX = window.innerWidth / 2
      mouse.targetY = window.innerHeight / 2
    }
    
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseleave', handleMouseLeave)
    
    let stars = []
    let meteors = []
    
    // 1. Realistic Stars
    class Star {
      constructor(cw, ch) {
        this.x = Math.random() * cw
        this.y = Math.random() * ch
        this.size = Math.random() * 1.5 + 0.1
        this.alpha = Math.random() * 0.8 + 0.2
        this.twinkleSpeed = Math.random() * 0.01 + 0.002
        this.twinkleDir = Math.random() > 0.5 ? 1 : -1
        this.parallaxFactor = this.size * 0.05
        
        // Continuous, subtle drift based on size (depth) to simulate traveling through space
        this.vx = -this.size * 0.05
        this.vy = -this.size * 0.02
        
        // Realistic astronomical star colors (Blue-white, pure white, faint yellow, rare red/orange dwarf)
        const rand = Math.random()
        if (rand < 0.6) this.color = '255, 255, 255'
        else if (rand < 0.8) this.color = '200, 220, 255'
        else if (rand < 0.95) this.color = '255, 240, 200'
        else this.color = '255, 200, 150'
      }
      update(cw, ch) {
        // Continuous slow movement
        this.x += this.vx
        this.y += this.vy
        
        // Screen wrap for infinite movement
        if (this.x < -10) this.x = cw + 10
        if (this.y < -10) this.y = ch + 10
        if (this.x > cw + 10) this.x = -10
        if (this.y > ch + 10) this.y = -10

        // Twinkle logic
        this.alpha += this.twinkleSpeed * this.twinkleDir
        if (this.alpha > 0.9 || this.alpha < 0.1) this.twinkleDir *= -1
      }
      draw(ctx, px, py) {
        const ox = this.x + px * this.parallaxFactor
        const oy = this.y + py * this.parallaxFactor
        
        // Performance Optimization: Use fillRect instead of arc for small particles 
        // to massively improve render speeds, especially on high resolution displays.
        ctx.fillStyle = `rgba(${this.color}, ${this.alpha})`
        ctx.fillRect(ox, oy, this.size * 2, this.size * 2)
      }
    }

    // 2. Realistic Fast Meteors (Shooting Stars)
    class Meteor {
      constructor(cw, ch) {
        this.cw = cw
        this.ch = ch
        this.active = false
        this.reset()
      }
      reset() {
        if (Math.random() > 0.5) {
          this.x = Math.random() * this.cw
          this.y = -50
        } else {
          this.x = this.cw + 50
          this.y = Math.random() * this.ch
        }
        this.length = Math.random() * 80 + 20
        this.speed = Math.random() * 15 + 15
        this.angle = (Math.PI / 180) * (Math.random() * 20 + 120) 
        this.active = true
      }
      update() {
        if (!this.active) return
        this.x += this.speed * Math.cos(this.angle)
        this.y += this.speed * Math.sin(this.angle)
        if (this.x < -100 || this.y > this.ch + 100) this.active = false
      }
      draw(ctx) {
        if (!this.active) return
        ctx.save()
        ctx.translate(this.x, this.y)
        ctx.rotate(this.angle)
        
        const grad = ctx.createLinearGradient(0, 0, -this.length, 0)
        grad.addColorStop(0, 'rgba(255, 255, 255, 1)')
        grad.addColorStop(0.1, 'rgba(200, 220, 255, 0.8)')
        grad.addColorStop(1, 'rgba(200, 220, 255, 0)')
        
        ctx.beginPath()
        ctx.moveTo(0, 0)
        ctx.lineTo(-this.length, 0)
        ctx.lineWidth = 1.5
        ctx.strokeStyle = grad
        ctx.stroke()
        ctx.restore()
      }
    }

    const setSize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
      
      if (stars.length === 0) {
        // Performance Optimization: Reduce star density and cap the maximum number of stars 
        // to prevent extreme lag on 4K/high-res monitors.
        let starCount = Math.floor((canvas.width * canvas.height) / 8000)
        if (starCount > 350) starCount = 350
        
        stars = Array.from({ length: starCount }, () => new Star(canvas.width, canvas.height))
        
        meteors = Array.from({ length: 3 }, () => new Meteor(canvas.width, canvas.height))
        meteors.forEach(m => m.active = false)
      }
    }
    
    setSize()
    window.addEventListener('resize', setSize)

    const render = () => {
      ctx.fillStyle = '#010206'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      mouse.x += (mouse.targetX - mouse.x) * 0.08
      mouse.y += (mouse.targetY - mouse.y) * 0.08

      const parallaxX = (canvas.width / 2 - mouse.x) * 0.2
      const parallaxY = (canvas.height / 2 - mouse.y) * 0.2

      stars.forEach(star => {
        star.update(canvas.width, canvas.height)
        star.draw(ctx, parallaxX, parallaxY)
      })

      if (Math.random() < 0.01) {
        const inactive = meteors.find(m => !m.active)
        if (inactive) inactive.reset()
      }

      meteors.forEach(meteor => {
        meteor.update()
        meteor.draw(ctx)
      })

      animationFrameId = window.requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseleave', handleMouseLeave)
      window.removeEventListener('resize', setSize)
      window.cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <div className="fixed inset-0 z-0 pointer-events-auto">
      <canvas ref={canvasRef} className="block w-full h-full cursor-default" />
    </div>
  )
}
