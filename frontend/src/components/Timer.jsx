import React, { useEffect, useState, useRef } from 'react'

export default function Timer({ startedAt, timeLimit, onExpire }) {
  const [remaining, setRemaining] = useState(null)
  // track whether we've already fired onExpire so we don't call it twice
  const expiredRef = useRef(false)

  useEffect(() => {
    if (!startedAt || !timeLimit) return

    const endTime = new Date(startedAt).getTime() + timeLimit * 1000

    // if the date parse failed for some reason, bail out
    if (isNaN(endTime)) {
      console.warn('[Timer] invalid startedAt value:', startedAt)
      return
    }

    expiredRef.current = false

    const tick = () => {
      const left = Math.max(0, Math.floor((endTime - Date.now()) / 1000))
      setRemaining(left)

      if (left === 0 && !expiredRef.current) {
        expiredRef.current = true
        if (onExpire) onExpire()
      }
    }

    tick()
    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [startedAt, timeLimit])

  // don't render anything until we have a valid startedAt
  if (remaining === null) return null

  const mins = String(Math.floor(remaining / 60)).padStart(2, '0')
  const secs = String(remaining % 60).padStart(2, '0')
  const isUrgent = remaining < 60
  const progress = timeLimit ? (remaining / timeLimit) * 100 : 100

  return (
    <div className="flex items-center gap-2">
      <div className="relative w-6 h-6">
        <svg className="w-6 h-6 -rotate-90" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="2.5" />
          <circle
            cx="12" cy="12" r="10" fill="none"
            stroke={isUrgent ? '#f43f5e' : '#6366f1'}
            strokeWidth="2.5"
            strokeDasharray={`${2 * Math.PI * 10}`}
            strokeDashoffset={`${2 * Math.PI * 10 * (1 - progress / 100)}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s linear, stroke 0.5s' }}
          />
        </svg>
      </div>
      <span className={`font-mono font-bold text-base tabular-nums ${isUrgent ? 'text-rose animate-pulse' : 'text-white'}`}>
        {mins}:{secs}
      </span>
    </div>
  )
}
