/**
 * MathText.jsx
 * Renders a string that may contain $...$ (inline) or $$...$$ (display) LaTeX.
 * Falls back to plain text rendering when no math is detected.
 */
import React from 'react'
import { parseMathSegments, hasMath } from '../utils/mathRenderer'
import katex from 'katex'
import 'katex/dist/katex.min.css'

function KatexSpan({ latex, display }) {
  let html = ''
  try {
    html = katex.renderToString(latex, {
      displayMode: display,
      throwOnError: false,
      strict: false,
      trust: false,
    })
  } catch {
    html = latex
  }
  return (
    <span
      className={display ? 'block my-1' : 'inline'}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

/**
 * MathText — renders plain text with embedded LaTeX math.
 *
 * Props:
 *   text      {string}  — the text to render
 *   className {string}  — optional extra class names
 *   as        {string}  — wrapper element tag (default: 'span')
 */
export default function MathText({ text, className = '', as: Tag = 'span' }) {
  if (!text) return null

  if (!hasMath(text)) {
    return <Tag className={className}>{text}</Tag>
  }

  const segments = parseMathSegments(text)

  return (
    <Tag className={className}>
      {segments.map((seg, i) => {
        if (seg.type === 'inline') {
          return <KatexSpan key={i} latex={seg.value} display={false} />
        }
        if (seg.type === 'display') {
          return <KatexSpan key={i} latex={seg.value} display={true} />
        }
        return <React.Fragment key={i}>{seg.value}</React.Fragment>
      })}
    </Tag>
  )
}
