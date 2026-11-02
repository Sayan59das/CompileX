// Makes the generated harness of a starter read-only, so a player only writes the logic.
//
// Locked:
//   * the function signature line, which is where the harness hands in the test input as arguments, and
//   * everything from the marker line to the end of the file: the code that reads the input, calls the function with the
//     parsed arguments and prints what it returns.
// Open: the body of the function, plus helper functions and imports above the marker.
//
// Monaco has no per-range read-only option, so an edit that would alter a locked part is undone the moment it lands.
// What counts as "the locked part" is taken from the starter code of the question on screen (the `getStarter` callback),
// not from whatever happens to be in the editor. That way loading another question or language is never mistaken for an
// edit, and selecting everything and typing over the file cannot replace the harness. The comparison is by text, not by
// line number, because line numbers shift as the player types above the marker.
//
// This is a guard against breaking the harness by accident, not a security boundary: the editor runs in the player's
// browser. The backend is the place to enforce it for graded play.

const MARKERS = [
  'You do not need to edit below', // starters built from a question's declared input structure, in every language
  'DO NOT MODIFY',                 // starters the backend guessed for older questions
  '===== TEST HARNESS',
]
const TYPED_MARKER = MARKERS[0]
const LOGIC_NOTE = 'Write your logic here'

const normalise = (text) => (text || '').replace(/\r\n/g, '\n')

export function findProtectedStartLine(model) {
  if (!model) return -1
  const total = model.getLineCount()
  for (let line = 1; line <= total; line++) {
    if (MARKERS.some(m => model.getLineContent(line).includes(m))) return line
  }
  return -1
}

// The locked parts of a starter text: the harness from its marker line on, and (for starters with a declared structure)
// the signature line, which is the line right above the "Write your logic here" note.
export function lockedParts(text) {
  const lines = normalise(text).split('\n')
  const start = lines.findIndex(line => MARKERS.some(m => line.includes(m)))
  if (start === -1) return { tail: null, signature: null }
  const tail = lines.slice(start).join('\n')
  let signature = null
  if (lines[start].includes(TYPED_MARKER)) {
    const note = lines.findIndex(line => line.includes(LOGIC_NOTE))
    if (note > 0 && note < start && lines[note - 1].trim()) signature = lines[note - 1]
  }
  return { tail, signature }
}

// True when the locked parts are all still there, and the signature is still above the harness.
function isIntact(value, parts) {
  const text = normalise(value)
  const tailAt = parts.tail ? text.indexOf(parts.tail) : -1
  if (parts.tail && tailAt === -1) return false
  if (parts.signature) {
    const signatureAt = text.indexOf(parts.signature)
    if (signatureAt === -1) return false
    if (parts.tail && signatureAt > tailAt) return false
  }
  return true
}

export function attachProtectedRegion(editor, monaco, getStarter) {
  // Without a getter, fall back to locking whatever the editor was loaded with.
  let loaded = { tail: null, signature: null }
  let reverting = false
  let intactBefore = true

  const collection = typeof editor.createDecorationsCollection === 'function'
    ? editor.createDecorationsCollection([])
    : null
  let legacyIds = []

  const setDecorations = (decorations) => {
    if (collection) collection.set(decorations)
    else legacyIds = editor.deltaDecorations(legacyIds, decorations)
  }

  const currentParts = () => (typeof getStarter === 'function' ? lockedParts(getStarter()) : loaded)

  const paint = () => {
    const model = editor.getModel()
    const parts = currentParts()
    const start = model ? findProtectedStartLine(model) : -1
    if (!model || !parts.tail || start === -1) {
      setDecorations([])
      return
    }
    const last = model.getLineCount()
    const hover = { value: 'Read-only. This harness feeds your function the test input.' }

    // The boundary line carries the badge; the rest just carries the rail, so
    // the zone reads as one sealed block with a single entry point.
    const decorations = [{
      range: new monaco.Range(start, 1, start, 1),
      options: {
        isWholeLine: true,
        className: 'cx-protected-line',
        linesDecorationsClassName: 'cx-protected-rail cx-protected-lock',
        hoverMessage: hover,
      },
    }]
    if (last > start) {
      decorations.push({
        range: new monaco.Range(start + 1, 1, last, 1),
        options: {
          isWholeLine: true,
          className: 'cx-protected-line',
          linesDecorationsClassName: 'cx-protected-rail',
          hoverMessage: hover,
        },
      })
    }
    if (parts.signature) {
      for (let line = 1; line < start; line++) {
        if (model.getLineContent(line) === parts.signature) {
          decorations.push({
            range: new monaco.Range(line, 1, line, 1),
            options: {
              isWholeLine: true,
              className: 'cx-protected-line',
              linesDecorationsClassName: 'cx-protected-rail',
              hoverMessage: { value: 'Read-only. The harness passes the test input into your function through these arguments.' },
            },
          })
          break
        }
      }
    }
    setDecorations(decorations)
  }

  // A rejected keystroke is otherwise silent, which reads as a broken editor.
  let rejectTimer = null
  const flashRejection = () => {
    const node = editor.getDomNode()
    if (!node) return
    node.classList.remove('cx-protect-reject')
    void node.offsetWidth // restart the animation on repeated attempts
    node.classList.add('cx-protect-reject')
    clearTimeout(rejectTimer)
    rejectTimer = setTimeout(() => node.classList.remove('cx-protect-reject'), 460)
  }

  const adoptLoaded = () => {
    const model = editor.getModel()
    if (model) loaded = lockedParts(model.getValue())
  }

  const refresh = () => {
    const model = editor.getModel()
    intactBefore = model ? isIntact(model.getValue(), currentParts()) : true
    paint()
  }

  if (typeof getStarter !== 'function') adoptLoaded()
  refresh()

  const sub = editor.onDidChangeModelContent((event) => {
    if (reverting) return

    // Without a getter, a wholesale replacement (new question, language switch) is adopted as the new locked block.
    if (typeof getStarter !== 'function' && event.isFlush) {
      adoptLoaded()
      refresh()
      return
    }

    const model = editor.getModel()
    const intactNow = model ? isIntact(model.getValue(), currentParts()) : true

    // Undo only an edit that broke a locked part that was intact before it. If the editor was never in line with the
    // starter (for instance while a new question is still loading), there is nothing sound to go back to.
    if (!intactNow && intactBefore) {
      reverting = true
      editor.trigger('protected-region', 'undo', null)
      reverting = false
      paint()
      flashRejection()
      return
    }
    intactBefore = intactNow
    paint()
  })

  return {
    resync: refresh,
    dispose: () => {
      sub.dispose()
      clearTimeout(rejectTimer)
      setDecorations([])
    },
  }
}
