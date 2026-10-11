// Helpers shared by the game, practice and skill-assessment screens.

export function parseTestCases(raw) {
  try {
    const a = typeof raw === 'string' ? JSON.parse(raw) : raw
    return Array.isArray(a) ? a : []
  } catch {
    return []
  }
}

/** Starter code for one language, from the JSON map the generator returns. */
export function parseStarterCode(raw, lang) {
  try {
    const m = typeof raw === 'string' ? JSON.parse(raw) : raw
    return (m && m[lang]) || ''
  } catch {
    return ''
  }
}

const SECTION_NAMES = ['Input Format', 'Output Format', 'Constraints', 'Note', 'Explanation', 'Sample Input', 'Sample Output']
// Sample sections repeat the worked examples we render from the test cases.
const SKIPPED = new Set(['Sample Input', 'Sample Output'])

/** Split a generated description into its intro text and named sections. */
export function parseSections(description) {
  if (!description) return { body: '', sections: [] }
  const parts = description.split(new RegExp(`\\*\\*(${SECTION_NAMES.join('|')})\\*\\*`, 'gi'))
  const body = parts[0].trim()
  const sections = []
  for (let i = 1; i < parts.length; i += 2) {
    const name = parts[i]
    const content = (parts[i + 1] || '').trim()
    if (name && content && !SKIPPED.has(name)) sections.push({ name, content })
  }
  return { body, sections }
}

/** Normalised view of a test case, whichever field names the backend used. */
export function caseIO(tc) {
  return {
    input: tc?.input ?? tc?.input_data ?? tc?.stdin ?? '',
    output: tc?.output ?? tc?.expected_output ?? '',
  }
}
