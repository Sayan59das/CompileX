/**
 * mathRenderer.js
 * Renders LaTeX math expressions using KaTeX.
 * Splits text on $...$ (inline) and $$...$$ (display) delimiters.
 */
import katex from 'katex'
import 'katex/dist/katex.min.css'

/**
 * Render a LaTeX string to an HTML string via KaTeX.
 * Returns the original string on failure so nothing breaks.
 */
function renderLatexToHtml(latex, displayMode = false) {
  try {
    return katex.renderToString(latex, {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: false,
    })
  } catch {
    return latex
  }
}

/**
 * Split text into segments: plain text and math ($...$ or $$...$$).
 * Returns an array of { type: 'text'|'inline'|'display', value: string }.
 */
export function parseMathSegments(text) {
  if (!text) return [{ type: 'text', value: '' }]

  const segments = []
  // Match $$...$$ first (display), then $...$ (inline)
  // Use a regex that handles both, prioritising $$
  const re = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g
  let last = 0
  let match

  while ((match = re.exec(text)) !== null) {
    // Push preceding plain text
    if (match.index > last) {
      segments.push({ type: 'text', value: text.slice(last, match.index) })
    }

    const raw = match[0]
    if (raw.startsWith('$$')) {
      segments.push({ type: 'display', value: raw.slice(2, -2) })
    } else {
      segments.push({ type: 'inline', value: raw.slice(1, -1) })
    }
    last = match.index + raw.length
  }

  // Trailing plain text
  if (last < text.length) {
    segments.push({ type: 'text', value: text.slice(last) })
  }

  return segments.length > 0 ? segments : [{ type: 'text', value: text }]
}

/**
 * Returns true if the text contains any LaTeX math delimiters.
 */
export function hasMath(text) {
  return text ? /\$/.test(text) : false
}

/**
 * Render a text string that may contain $...$ or $$...$$ math to an HTML string.
 * Safe to use with dangerouslySetInnerHTML.
 */
export function renderMathToHtml(text) {
  if (!text || !hasMath(text)) return null

  const segments = parseMathSegments(text)
  return segments
    .map(seg => {
      if (seg.type === 'inline') return renderLatexToHtml(seg.value, false)
      if (seg.type === 'display') return renderLatexToHtml(seg.value, true)
      // Escape HTML entities in plain text segments
      return seg.value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
    })
    .join('')
}
