import React from 'react'
import Icon from '../components/Icons'

const RANK_COLOR = ['text-amber-400', 'text-slate-300', 'text-orange-400']

export default function Leaderboard({ entries = [], currentPlayerId }) {
  if (!entries.length) {
    return (
      <div className="text-center py-8">
        <Icon name="bars" size={28} className="mx-auto mb-2 text-slate-500" />
        <p className="text-slate-500 text-xs">No scores yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      {entries.map((entry, i) => {
        const isMe = (entry.player_id ?? entry.id) === currentPlayerId
        return (
          <div
            key={entry.player_id ?? entry.id ?? i}
            className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm ${
 isMe
                ? 'bg-indigo/20 border border-indigo/30'
                : 'bg-white/[0.03] border border-white/5'
            }`}
          >
            <span className="w-5 text-center text-base shrink-0">
              <span className={`text-sm font-bold ${RANK_COLOR[i] ?? 'text-slate-500'}`}>{i + 1}</span>
            </span>
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo to-violet flex items-center justify-center text-white text-xs font-bold shrink-0">
              {entry.username?.[0]?.toUpperCase()}
            </div>
            <span className={`flex-1 truncate font-medium text-xs ${isMe ? 'text-indigo-light' : 'text-slate-200'}`}>
              {entry.username}
            </span>
            <span className={`font-bold text-sm shrink-0 ${isMe ? 'text-indigo-light' : 'text-white'}`}>
              {entry.score}
            </span>
          </div>
        )
      })}
    </div>
  )
}
