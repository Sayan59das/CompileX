import React from 'react'
import Avatar from './Avatar'

/**
 * Standings table. Rows are ranked by the order they arrive in, which is how
 * the server sends them. The current player's row is highlighted.
 */
export default function Leaderboard({ entries = [], currentPlayerId, showSolved = true, className = '' }) {
  if (!entries.length) {
    return (
      <div className={`px-5 py-10 text-center ${className}`}>
        <p className="font-semibold">No scores yet</p>
        <p className="mt-1 text-sm text-ink-3">Standings appear when the first solution is submitted.</p>
      </div>
    )
  }

  return (
    <ol className={className}>
      {entries.map((entry, i) => {
        const isMe = (entry.player_id ?? entry.id) === currentPlayerId
        return (
          <li
            key={entry.player_id ?? entry.id ?? i}
            className={`flex items-center gap-3 border-b border-line px-4 py-3 last:border-b-0 ${isMe ? 'bg-sun/15' : ''}`}
          >
            <span className={`numeral w-7 shrink-0 text-2xl ${i === 0 ? 'text-sun-ink' : 'text-ink-3'}`}>{i + 1}</span>
            <Avatar name={entry.username} size={30} />
            <div className="min-w-0 flex-1">
              <div className="truncate font-semibold">
                {entry.username}
                {isMe && <span className="ml-2 text-xs font-medium text-ink-3">you</span>}
              </div>
              {showSolved && <div className="text-xs text-ink-3">{entry.questions_solved ?? 0} solved</div>}
            </div>
            <span className="numeral text-2xl">{Math.round(entry.score ?? 0)}</span>
          </li>
        )
      })}
    </ol>
  )
}
