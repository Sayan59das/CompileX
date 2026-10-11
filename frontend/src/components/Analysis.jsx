import React from 'react'
import Icon from './Icons'

/* Colour for a 0–100 score. */
export function scoreColor(v) {
  return v >= 70 ? 'grass' : v >= 40 ? 'sun' : 'tomato'
}

export function Spinner({ className = '' }) {
  return (
    <span
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-ink ${className}`}
      role="status"
      aria-label="Loading"
    />
  )
}

/** Centered message for panels that have nothing to show yet. */
export function PanelNote({ title, children, action }) {
  return (
    <div className="px-6 py-12 text-center">
      <p className="font-semibold">{title}</p>
      {children && <p className="mx-auto mt-1.5 max-w-xs text-sm text-ink-2">{children}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

function Bar({ value }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-line">
      <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: `rgb(var(--${scoreColor(value)}))` }} />
    </div>
  )
}

export function BreakdownBars({ breakdown }) {
  const entries = Object.entries(breakdown || {})
  if (!entries.length) return null
  return (
    <div className="space-y-3">
      {entries.map(([k, v]) => (
        <div key={k}>
          <div className="mb-1 flex items-baseline justify-between text-sm">
            <span className="capitalize text-ink-2">{k.replace(/_/g, ' ')}</span>
            <span className="tnum font-semibold">{v}%</span>
          </div>
          <Bar value={v} />
        </div>
      ))}
    </div>
  )
}

export function SuggestionList({ title, items }) {
  if (!items?.length) return null
  return (
    <div>
      <h4 className="mb-2 text-sm font-bold">{title}</h4>
      <ul className="space-y-2">
        {items.map((s, i) => (
          <li key={i} className="flex gap-2.5 text-sm leading-6 text-ink-2">
            <span className="dot mt-2.5" style={{ background: 'rgb(var(--sun))' }} />
            <span>{s}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Result of the AI logic review: score, explanation, breakdown and hints. */
export function LogicReport({ data, showPredicted = true }) {
  if (!data) return null
  const pct = data.logic_correctness
  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="text-sm text-ink-3">{data.is_pre_submission ? 'Run the tests to get a score' : 'Logic score'}</div>
          {!data.is_pre_submission && <div className="numeral text-5xl">{pct}%</div>}
        </div>
        {showPredicted && !data.is_pre_submission && data.predicted_score != null && (
          <div className="text-right">
            <div className="text-sm text-ink-3">Score if you submit now</div>
            <div className="numeral text-3xl">
              {data.predicted_score}
              <span className="text-base font-medium text-ink-3"> / 100</span>
            </div>
          </div>
        )}
      </div>
      {!data.is_pre_submission && <Bar value={pct} />}
      {data.analysis && <p className="text-sm leading-6 text-ink-2">{data.analysis}</p>}
      <BreakdownBars breakdown={data.breakdown} />
      <SuggestionList title="What to try next" items={data.suggestions?.slice(0, 4)} />
    </div>
  )
}

/* ─── Complexity ─────────────────────────────────────────────────────────── */

const CURVES = [
  { label: 'O(1)', color: 'grass' },
  { label: 'O(log n)', color: 'sky' },
  { label: 'O(n)', color: 'violet' },
  { label: 'O(n log n)', color: 'sun' },
  { label: 'O(n²)', color: 'tomato' },
]
const N = 20

function growth(notation, n) {
  switch (notation) {
    case 'O(1)': return 1
    case 'O(log n)': return Math.log2(n + 1)
    case 'O(sqrt n)': return Math.sqrt(n)
    case 'O(n)': return n
    case 'O(n log n)': return n * Math.log2(n + 1)
    case 'O(n²)': return n * n
    case 'O(2^n)': return Math.min(Math.pow(2, n), N * N * 4)
    case 'O(n!)': return Math.min(n <= 8 ? [1, 1, 2, 6, 24, 120, 720, 5040, 40320][n] || N * N * 4 : N * N * 4, N * N * 4)
    default: return n
  }
}

/** Growth curves for common complexities, with the player's curve emphasised. */
export function ComplexityChart({ userComplexity }) {
  const W = 340, H = 190
  const PAD = { top: 12, right: 14, bottom: 34, left: 34 }
  const cw = W - PAD.left - PAD.right
  const ch = H - PAD.top - PAD.bottom
  const max = Math.max(...CURVES.flatMap((c) => Array.from({ length: N }, (_, i) => growth(c.label, i + 1))), 1)
  const x = (n) => PAD.left + ((n - 1) / (N - 1)) * cw
  const y = (v) => PAD.top + ch - (Math.min(v, max) / max) * ch
  const path = (label) => 'M' + Array.from({ length: N }, (_, i) => `${x(i + 1).toFixed(1)},${y(growth(label, i + 1)).toFixed(1)}`).join('L')
  const mid = Math.floor(N * 0.6)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" role="img" aria-label="Growth curves for common time complexities">
      {[0, 25, 50, 75, 100].map((p) => {
        const yy = PAD.top + ch - (p / 100) * ch
        return <line key={p} x1={PAD.left} x2={PAD.left + cw} y1={yy} y2={yy} stroke="rgb(var(--line))" />
      })}
      <line x1={PAD.left} x2={PAD.left} y1={PAD.top} y2={PAD.top + ch} stroke="rgb(var(--line-strong))" />
      <line x1={PAD.left} x2={PAD.left + cw} y1={PAD.top + ch} y2={PAD.top + ch} stroke="rgb(var(--line-strong))" />
      {[1, 5, 10, 15, 20].map((n) => (
        <text key={n} x={x(n)} y={PAD.top + ch + 14} textAnchor="middle" fontSize="9" fill="rgb(var(--ink-3))">{n}</text>
      ))}
      <text x={PAD.left + cw / 2} y={H - 4} textAnchor="middle" fontSize="9" fill="rgb(var(--ink-3))">Input size (n)</text>
      <text x={10} y={PAD.top + ch / 2} textAnchor="middle" fontSize="9" fill="rgb(var(--ink-3))" transform={`rotate(-90, 10, ${PAD.top + ch / 2})`}>Operations</text>
      {CURVES.map((c) => {
        const mine = userComplexity === c.label
        return <path key={c.label} d={path(c.label)} fill="none" stroke={`rgb(var(--${c.color}))`} strokeWidth={mine ? 3 : 1.4} strokeOpacity={mine ? 1 : 0.5} />
      })}
      {userComplexity && !CURVES.find((c) => c.label === userComplexity) && (
        <path d={path(userComplexity)} fill="none" stroke="rgb(var(--ink))" strokeWidth="3" />
      )}
      {userComplexity && (
        <g>
          <circle cx={x(mid)} cy={y(growth(userComplexity, mid))} r="3.5" fill="rgb(var(--ink))" />
          <text x={x(mid) + 6} y={y(growth(userComplexity, mid)) - 6} fontSize="10" fontWeight="700" fill="rgb(var(--ink))">Your code</text>
        </g>
      )}
    </svg>
  )
}

function ChartLegend({ userComplexity }) {
  return (
    <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
      {CURVES.map((c) => (
        <li key={c.label} className={`flex items-center gap-1.5 text-xs ${userComplexity === c.label ? 'font-bold text-ink' : 'text-ink-3'}`}>
          <span className="h-0.5 w-4 rounded" style={{ background: `rgb(var(--${c.color}))` }} />
          {c.label}
        </li>
      ))}
    </ul>
  )
}

const VERDICTS = {
  optimal: { label: 'Optimal', color: 'grass' },
  acceptable: { label: 'Acceptable', color: 'sun' },
  needs_improvement: { label: 'Needs improvement', color: 'tangerine' },
  poor: { label: 'Poor', color: 'tomato' },
}
const PRIORITY = { high: 'tomato', medium: 'sun', low: 'grass' }

function Block({ title, children }) {
  return (
    <section className="border-t border-line pt-5">
      <h4 className="mb-3 text-sm font-bold">{title}</h4>
      {children}
    </section>
  )
}

function fmtMemory(kb) {
  if (kb == null) return '—'
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(1)} KB`
}

/** Time and space report for a solution. Every part except the table is optional. */
export function ComplexityReport({ data }) {
  if (!data) return null
  const verdict = data.verdict && data.verdict !== 'unknown' ? VERDICTS[data.verdict] || VERDICTS.acceptable : null
  const tc = data.time_complexity || {}
  const sc = data.space_complexity || {}
  const stats = data.execution_stats

  return (
    <div className="space-y-5">
      {verdict && (
        <div className="flex items-start gap-3 rounded-md border border-line bg-sunken p-4">
          <span className="dot mt-2" style={{ background: `rgb(var(--${verdict.color}))` }} />
          <div>
            <div className="font-bold">{verdict.label}</div>
            {data.verdict_explanation && <p className="mt-0.5 text-sm leading-6 text-ink-2">{data.verdict_explanation}</p>}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-sm text-ink-3">Time, worst case</div>
          <div className="numeral mt-1 text-4xl">{tc.worst || 'N/A'}</div>
        </div>
        <div>
          <div className="text-sm text-ink-3">Space, worst case</div>
          <div className="numeral mt-1 text-4xl">{sc.worst || 'N/A'}</div>
        </div>
      </div>

      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-ink-3">
            <th className="py-2 font-medium" />
            <th className="py-2 font-medium">Best</th>
            <th className="py-2 font-medium">Average</th>
            <th className="py-2 font-medium">Worst</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {[['Time', tc], ['Space', sc]].map(([name, c]) => (
            <tr key={name} className="border-b border-line last:border-b-0">
              <td className="py-2.5 font-sans font-medium text-ink-2">{name}</td>
              <td className="py-2.5">{c.best || '—'}</td>
              <td className="py-2.5">{c.average || '—'}</td>
              <td className="py-2.5">{c.worst || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {stats && (
        <Block title="Measured on your tests">
          <dl className="grid grid-cols-3 gap-3">
            {[
              ['Memory', fmtMemory(stats.memory_kb)],
              ['CPU time', stats.cpu_time_ms != null ? `${Math.round(stats.cpu_time_ms)} ms` : '—'],
              ['Wall time', stats.wall_time_ms != null ? `${Math.round(stats.wall_time_ms)} ms` : '—'],
            ].map(([k, v]) => (
              <div key={k}>
                <dd className="numeral text-2xl">{v}</dd>
                <dt className="mt-1 text-xs text-ink-3">{k}</dt>
              </div>
            ))}
          </dl>
        </Block>
      )}

      <Block title="How it grows">
        <ComplexityChart userComplexity={tc.worst} />
        <ChartLegend userComplexity={tc.worst} />
      </Block>

      {data.analysis && (
        <Block title="Analysis">
          <p className="text-sm leading-6 text-ink-2">{data.analysis}</p>
        </Block>
      )}

      {data.structured_suggestions?.length > 0 ? (
        <Block title="Ways to improve">
          <ul className="space-y-3">
            {data.structured_suggestions.map((s, i) => (
              <li key={i} className="flex gap-3">
                <span className="dot mt-2" style={{ background: `rgb(var(--${PRIORITY[s.priority] || 'sun'}))` }} />
                <div>
                  <div className="text-sm font-semibold">
                    {s.title} <span className="font-normal text-ink-3">({s.priority || 'medium'} priority)</span>
                  </div>
                  <p className="text-sm leading-6 text-ink-2">{s.description}</p>
                </div>
              </li>
            ))}
          </ul>
        </Block>
      ) : (
        data.suggestions?.length > 0 && (
          <Block title="Ways to improve">
            <SuggestionList title="" items={data.suggestions} />
          </Block>
        )
      )}
    </div>
  )
}

/* ─── Test cases ─────────────────────────────────────────────────────────── */

function Labelled({ label, tone = 'text-ink', box = 'border-line bg-sunken', children }) {
  return (
    <div>
      <div className="mb-1.5 text-sm font-medium text-ink-3">{label}</div>
      <pre className={`overflow-x-auto whitespace-pre-wrap break-words rounded-md border px-3.5 py-2.5 font-mono text-[13px] leading-6 ${box} ${tone}`}>{children}</pre>
    </div>
  )
}

/**
 * Case list on the left, details on the right. `cases` items are
 * { input, expected_output, actual_output, passed (null until run), error, hidden }.
 */
export function TestCaseViewer({ cases, selected, onSelect, onHint, hint, loadingHint, className = '' }) {
  if (!cases.length) {
    return <p className="px-6 py-10 text-center text-sm text-ink-2">Test cases appear once the problem is ready.</p>
  }
  const tc = cases[selected] || cases[0]
  const ran = tc.passed !== null && tc.passed !== undefined

  return (
    <div className={`flex h-full min-h-0 ${className}`}>
      <ul className="w-36 shrink-0 space-y-1 overflow-y-auto border-r border-line p-2.5">
        {cases.map((c, i) => {
          const done = c.passed !== null && c.passed !== undefined
          return (
            <li key={i}>
              <button
                onClick={() => onSelect(i)}
                aria-pressed={selected === i}
                className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm font-semibold transition-colors ${
                  selected === i ? 'bg-sunken text-ink' : 'text-ink-2 hover:bg-sunken'
                }`}
              >
                <Icon
                  name={!done ? 'circle' : c.passed ? 'check-circle' : 'x-circle'}
                  size={16}
                  className={!done ? 'text-line-strong' : c.passed ? 'text-grass-ink' : 'text-tomato-ink'}
                />
                Case {i + 1}
                {c.hidden && <Icon name="lock" size={12} className="ml-auto text-ink-3" />}
              </button>
            </li>
          )
        })}
      </ul>

      <div className="min-w-0 flex-1 space-y-4 overflow-y-auto p-4">
        {tc.hidden ? (
          <div className="py-4">
            <div className="flex items-center gap-2 font-semibold">
              <Icon name="lock" size={16} /> Hidden test case
            </div>
            <p className="mt-1.5 max-w-sm text-sm text-ink-2">
              Its input and expected output are not shown. Cover the edge cases and it will pass.
            </p>
          </div>
        ) : (
          <>
            <Labelled label="Input">{tc.input || '(empty)'}</Labelled>
            <Labelled label="Expected output" tone="text-grass-ink">{tc.expected_output || '(empty)'}</Labelled>
          </>
        )}

        {ran && (
          <>
            {!tc.hidden && (
              <Labelled
                label="Your output"
                tone={tc.passed && !tc.error ? 'text-grass-ink' : 'text-tomato-ink'}
                box={tc.passed && !tc.error ? 'border-grass-ink/40 bg-grass/10' : 'border-tomato-ink/40 bg-tomato/10'}
              >
                {tc.error || tc.actual_output || '(no output)'}
              </Labelled>
            )}
            <div className={`flex items-center gap-2 font-semibold ${tc.passed ? 'text-grass-ink' : 'text-tomato-ink'}`}>
              <Icon name={tc.passed ? 'check-circle' : 'x-circle'} size={18} />
              {tc.passed ? 'This case passed' : 'This case failed'}
            </div>
            {tc.hidden && !tc.passed && tc.error && <Labelled label="Error" tone="text-tomato-ink" box="border-tomato-ink/40 bg-tomato/10">{tc.error}</Labelled>}
            {!tc.passed && onHint && (
              <div>
                <button onClick={onHint} disabled={loadingHint} className="btn btn-secondary btn-sm">
                  <Icon name="bulb" size={14} />
                  {loadingHint ? 'Looking at your code…' : 'Get a hint'}
                </button>
                {hint && (
                  <div className="mt-3 space-y-1.5 rounded-md border border-sun-ink/40 bg-sun/10 p-4 text-sm leading-6">
                    <div className="font-bold">{hint.status}</div>
                    {hint.line && <div className="text-ink-2">Look at line {hint.line}.</div>}
                    <p>{hint.message}</p>
                    <p className="font-semibold">{hint.hint}</p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
        {!ran && <p className="text-sm text-ink-3">Run or submit your code to see how this case goes.</p>}
      </div>
    </div>
  )
}
