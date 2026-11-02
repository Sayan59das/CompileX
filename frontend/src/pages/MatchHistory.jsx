import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, History } from 'lucide-react'
import api from '../services/api'
import AppShell from '../components/AppShell'
import { PageHeader, Panel, Button, Badge, EmptyState, Spinner } from '../components/ui'

const MODE_LABEL = { multiplayer: 'Multiplayer', '1v1': '1v1 duel', tournament: 'Tournament', solo: 'Solo' }

export default function MatchHistory() {
  const nav = useNavigate()
  const [matches, setMatches] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const limit = 15

  useEffect(() => { fetchHistory() }, [page])

  async function fetchHistory() {
    setLoading(true)
    try {
      const { data } = await api.get(`/users/me/history?limit=${limit}&offset=${page * limit}`)
      setMatches(data.matches)
      setTotal(data.total)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  const totalPages = Math.ceil(total / limit)

  return (
    <AppShell>
      <PageHeader title="Match history" description={loading ? 'Loading' : `${total} ${total === 1 ? 'match' : 'matches'} played`} />

      <Panel bodyClassName="">
        {loading ? (
          <Spinner label="Loading matches" />
        ) : matches.length === 0 ? (
          <EmptyState icon={History} title="No matches yet" action={<Button onClick={() => nav('/dashboard')}>Find a match</Button>}>
            Matches you play show up here with your rank and score.
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[14px]">
              <thead>
                <tr className="border-b border-white/10 text-[12px] text-slate-500">
                  <th className="px-5 py-2.5 font-medium">Match</th>
                  <th className="px-3 py-2.5 font-medium">Mode</th>
                  <th className="px-3 py-2.5 text-right font-medium">Solved</th>
                  <th className="px-3 py-2.5 text-right font-medium">Rank</th>
                  <th className="px-3 py-2.5 text-right font-medium">Score</th>
                  <th className="px-5 py-2.5 text-right font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {matches.map((m, i) => {
                  const isWin = m.player_rank === 1 && m.total_players > 1
                  return (
                    <tr key={i} className="border-b border-white/5 transition-colors hover:bg-white/[0.02]">
                      <td className="px-5 py-3">
                        <span className="font-medium text-white">{m.lobby_name}</span>
                        {isWin && <Badge tone="success" className="ml-2">Won</Badge>}
                      </td>
                      <td className="px-3 py-3 text-slate-300">{MODE_LABEL[m.game_mode] || m.game_mode}</td>
                      <td className="px-3 py-3 text-right font-mono tabular-nums text-slate-300">{m.questions_solved}</td>
                      <td className="px-3 py-3 text-right font-mono tabular-nums text-slate-300">{m.player_rank} / {m.total_players}</td>
                      <td className="px-3 py-3 text-right font-mono tabular-nums text-white">{m.player_score}</td>
                      <td className="px-5 py-3 text-right text-slate-400">{new Date(m.played_at).toLocaleDateString()}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-white/10 px-5 py-3 text-[13px] text-slate-400">
            <span>Page {page + 1} of {totalPages}</span>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" icon={ChevronLeft} disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Previous</Button>
              <Button size="sm" variant="secondary" disabled={page >= totalPages - 1} onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}>
                Next<ChevronRight className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        )}
      </Panel>
    </AppShell>
  )
}
