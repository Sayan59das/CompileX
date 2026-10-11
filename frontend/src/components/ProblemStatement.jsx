import React, { useMemo } from 'react'
import MathText from './MathText'
import { DifficultyTag } from './Avatar'
import { parseSections, parseTestCases, caseIO } from '../utils/problem'

/** Inline `code`, **bold** and $math$ in generated problem text. */
function Inline({ text }) {
  if (!text) return null
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g)
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('`') && p.endsWith('`'))
          return (
            <code key={i} className="rounded border border-line bg-sunken px-1.5 py-0.5 font-mono text-[0.86em] text-ink">
              {p.slice(1, -1)}
            </code>
          )
        if (p.startsWith('**') && p.endsWith('**'))
          return (
            <strong key={i} className="font-semibold text-ink">
              <MathText text={p.slice(2, -2)} />
            </strong>
          )
        if ((p.startsWith('$$') && p.endsWith('$$')) || (p.startsWith('$') && p.endsWith('$')))
          return <MathText key={i} text={p} />
        return <span key={i}>{p}</span>
      })}
    </>
  )
}

const CODE_SECTIONS = new Set(['Input Format', 'Output Format'])
const LABELS = {
  'Input Format': 'Input format',
  'Output Format': 'Output format',
  Constraints: 'Constraints',
  Note: 'Note',
  Explanation: 'Explanation',
}

function Heading({ children }) {
  return <h3 className="mb-2 text-sm font-bold text-ink">{children}</h3>
}

function CodeBlock({ children, tone = 'text-ink' }) {
  return (
    <pre className={`overflow-x-auto whitespace-pre-wrap break-words rounded-md border border-line bg-sunken px-3.5 py-3 font-mono text-[13px] leading-6 ${tone}`}>
      {children}
    </pre>
  )
}

/**
 * The problem as a player reads it: title, difficulty and topic, the
 * description split into its sections, then worked examples taken from the
 * first visible test cases. One renderer for the arena, practice and match.
 */
export default function ProblemStatement({ question, exampleCount = 1, showTitle = true, className = '' }) {
  const text = question?.description || question?.problem_statement || ''
  const { body, sections } = useMemo(() => parseSections(text), [text])
  const examples = useMemo(() => parseTestCases(question?.test_cases).slice(0, exampleCount), [question?.test_cases, exampleCount])

  if (!question) return null

  return (
    <article className={className}>
      {showTitle && (
        <header className="mb-5">
          <h2 className="stretch-narrow text-3xl font-extrabold leading-tight tracking-tight">{question.title}</h2>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {question.difficulty && <DifficultyTag level={question.difficulty} />}
            {question.topic && <span className="chip capitalize">{question.topic}</span>}
          </div>
        </header>
      )}

      {body && (
        <div className="space-y-3 leading-7 text-ink-2">
          {body
            .split('\n')
            .filter(Boolean)
            .map((line, i) => (
              <p key={i}>
                <Inline text={line} />
              </p>
            ))}
        </div>
      )}

      {question.diagram && (
        <figure className="mt-6 overflow-hidden rounded-md border border-line bg-panel">
          <img src={question.diagram} alt="Diagram for the problem" className="mx-auto max-h-96 w-full object-contain" />
        </figure>
      )}

      {examples.map((tc, i) => {
        const { input, output } = caseIO(tc)
        return (
          <section key={i} className="mt-6">
            <Heading>Example {examples.length > 1 ? i + 1 : ''}</Heading>
            <div className="overflow-hidden rounded-md border border-line">
              <div className="border-b border-line bg-sunken px-3.5 py-1.5 text-xs font-medium text-ink-3">Input</div>
              <pre className="whitespace-pre-wrap break-words px-3.5 py-3 font-mono text-[13px] leading-6 text-ink">{input || '(empty)'}</pre>
              <div className="border-y border-line bg-sunken px-3.5 py-1.5 text-xs font-medium text-ink-3">Output</div>
              <pre className="whitespace-pre-wrap break-words px-3.5 py-3 font-mono text-[13px] leading-6 text-grass-ink">{output || '(empty)'}</pre>
            </div>
          </section>
        )
      })}

      {sections.map((s) => (
        <section key={s.name} className="mt-6">
          <Heading>{LABELS[s.name] || s.name}</Heading>
          {CODE_SECTIONS.has(s.name) ? (
            <CodeBlock>{s.content}</CodeBlock>
          ) : (
            <div className="space-y-1.5 leading-7 text-ink-2">
              {s.content.split('\n').filter((l) => l.trim()).map((l, i) => (
                <p key={i}>
                  <Inline text={l.trim()} />
                </p>
              ))}
            </div>
          )}
        </section>
      ))}
    </article>
  )
}
