import React from 'react'
import { balloonFill, balloonForString, onBalloon } from '../utils/balloons'

/** Initial in a balloon-coloured circle. The colour is stable per username. */
export default function Avatar({ name = '?', size = 32, className = '' }) {
  const color = balloonForString(name)
  return (
    <span
      className={`inline-flex shrink-0 select-none items-center justify-center rounded-full font-bold ${className}`}
      style={{
        width: size,
        height: size,
        fontSize: size * 0.42,
        background: balloonFill(color),
        color: onBalloon(color),
      }}
      aria-hidden="true"
    >
      {name.charAt(0).toUpperCase()}
    </span>
  )
}

/** Difficulty marker: a coloured dot and a plain-language label. */
export function DifficultyTag({ level = 'medium', className = '' }) {
  const palette = { easy: 'grass', medium: 'sun', hard: 'tomato' }
  const key = String(level).toLowerCase()
  const color = palette[key] || 'sun'
  return (
    <span className={`chip capitalize ${className}`}>
      <span className="dot" style={{ background: balloonFill(color) }} />
      {key}
    </span>
  )
}
