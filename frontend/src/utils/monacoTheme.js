// Monaco themes that match the app palette. Register once via `beforeMount`
// and select with `useEditorTheme()` from the theme context.
let registered = false

export function registerEditorThemes(monaco) {
  if (registered) return
  registered = true

  monaco.editor.defineTheme('cx-light', {
    base: 'vs',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '8A90AE', fontStyle: 'italic' },
      { token: 'keyword', foreground: '5B3CD6' },
      { token: 'string', foreground: '0A7450' },
      { token: 'number', foreground: 'A85F00' },
      { token: 'type', foreground: 'C42820' },
      { token: 'function', foreground: '1862C8' },
      { token: 'identifier', foreground: '14183B' },
      { token: 'delimiter', foreground: '4A5070' },
    ],
    colors: {
      'editor.background': '#FFFFFF',
      'editor.foreground': '#14183B',
      'editorLineNumber.foreground': '#A4A9C2',
      'editorLineNumber.activeForeground': '#14183B',
      'editor.lineHighlightBackground': '#F3F4F6',
      'editor.selectionBackground': '#F7B50066',
      'editorCursor.foreground': '#F0483E',
      'editorIndentGuide.background1': '#E4E6EE',
      'editorIndentGuide.activeBackground1': '#B8BECC',
      'editorWidget.background': '#FFFFFF',
      'editorWidget.border': '#DEE1E8',
    },
  })

  monaco.editor.defineTheme('cx-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6F76A8', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'B79CFF' },
      { token: 'string', foreground: '7EE0B5' },
      { token: 'number', foreground: 'FFC857' },
      { token: 'type', foreground: 'FF8A80' },
      { token: 'function', foreground: '8CC4FF' },
      { token: 'identifier', foreground: 'E8EBFF' },
      { token: 'delimiter', foreground: 'AAB0D8' },
    ],
    colors: {
      'editor.background': '#0B0D20',
      'editor.foreground': '#E8EBFF',
      'editorLineNumber.foreground': '#4B5190',
      'editorLineNumber.activeForeground': '#AAB0D8',
      'editor.lineHighlightBackground': '#14173A',
      'editor.selectionBackground': '#FFC82855',
      'editorCursor.foreground': '#FF6358',
      'editorIndentGuide.background1': '#1D2150',
      'editorIndentGuide.activeBackground1': '#3A4088',
      'editorWidget.background': '#161936',
      'editorWidget.border': '#282D58',
    },
  })
}

export const EDITOR_FONT = '"JetBrains Mono", ui-monospace, Menlo, monospace'
