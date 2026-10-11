import React, { useEffect, useState, useRef } from 'react'

/** Countdown for the current question. Turns red in the last minute. */
export default function Timer({ startedAt, timeLimit, onExpire }) {
  const [remaining, setRemaining] = useState(null)
  // Track whether we've already fired onExpire so it only runs once.
  const expiredRef = useRef(false)

  useEffect(() => {
    if (!startedAt || !timeLimit) return

    const endTime = new Date(startedAt).getTime() + timeLimit * 1000

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

  if (remaining === null) return null

  const mins = String(Math.floor(remaining / 60)).padStart(2, '0')
  const secs = String(remaining % 60).padStart(2, '0')
  const urgent = remaining < 60
  const progress = timeLimit ? Math.max(0, Math.min(100, (remaining / timeLimit) * 100)) : 100

  return (
    <div
      className="flex flex-col items-end gap-1"
      role="timer"
      aria-label={`${mins} minutes ${secs} seconds left`}
    >
      <span className={`numeral text-2xl ${urgent ? 'text-tomato-ink' : 'text-ink'}`}>
        {mins}:{secs}
      </span>
      <span className="block h-1 w-16 overflow-hidden rounded-full bg-line">
        <span
          className={`block h-full ${urgent ? 'bg-tomato' : 'bg-ink'}`}
          style={{ width: `${progress}%`, transition: 'width 1s linear' }}
        />
      </span>
    </div>
  )
}
