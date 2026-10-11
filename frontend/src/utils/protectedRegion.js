// Makes the generated "DO NOT MODIFY" harness at the tail of starter code
// read-only.
//
// Monaco has no per-range read-only option, so edits that would alter the
// block are undone the moment they land. Detection compares against a snapshot
// of the block text rather than line numbers, because line numbers shift as the
// user types above it.

const MARKERS = [
  'DO NOT MODIFY',
  '===== TEST HARNESS',
]

export function findProtectedStartLine(model) {
  if (!model) return -1
  const total = model.getLineCount()
  for (let line = 1; line <= total; line++) {
    if (MARKERS.some(m => model.getLineContent(line).includes(m))) return line
  }
  return -1
}

export function attachProtectedRegion(editor, monaco) {
  let protectedText = null
  let reverting = false

  const collection = typeof editor.createDecorationsCollection === 'function'
    ? editor.createDecorationsCollection([])
    : null
  let legacyIds = []

  const setDecorations = (decorations) => {
    if (collection) collection.set(decorations)
    else legacyIds = editor.deltaDecorations(legacyIds, decorations)
  }

  const snapshot = () => {
    const model = editor.getModel()
    const start = findProtectedStartLine(model)
    if (!model || start === -1) {
      protectedText = null
      return
    }
    const lastLine = model.getLineCount()
    protectedText = model.getValueInRange(
      new monaco.Range(start, 1, lastLine, model.getLineMaxColumn(lastLine))
    )
  }

  const paint = () => {
    const model = editor.getModel()
    const start = findProtectedStartLine(model)
    if (!model || start === -1) {
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

  snapshot()
  paint()

  const sub = editor.onDidChangeModelContent((event) => {
    if (reverting) return

    // isFlush means the value was replaced wholesale (new question, language
    // switch) rather than typed — adopt the new block instead of fighting it.
    if (event.isFlush) {
      snapshot()
      paint()
      return
    }

    const model = editor.getModel()
    if (protectedText && model && !model.getValue().includes(protectedText)) {
      reverting = true
      editor.trigger('protected-region', 'undo', null)
      reverting = false
      paint()
      flashRejection()
      return
    }
    paint()
  })

  return {
    resync: () => { snapshot(); paint() },
    dispose: () => {
      sub.dispose()
      clearTimeout(rejectTimer)
      setDecorations([])
    },
  }
}
