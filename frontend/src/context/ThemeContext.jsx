import React, { createContext, useCallback, useContext, useState } from 'react'
import Icon from '../components/Icons'

// The initial theme is applied by the inline script in index.html, so this
// provider only reads it back and handles toggling.
const ThemeContext = createContext({ theme: 'light', toggle: () => {} })

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() =>
    document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
  )

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark'
      document.documentElement.setAttribute('data-theme', next)
      try { localStorage.setItem('cx-theme', next) } catch { /* private mode */ }
      return next
    })
  }, [])

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>
}

export const useTheme = () => useContext(ThemeContext)

/** Monaco theme name matching the app theme (defined in utils/monacoTheme.js). */
export function useEditorTheme() {
  const { theme } = useTheme()
  return theme === 'dark' ? 'cx-dark' : 'cx-light'
}

export function ThemeToggle({ className = '' }) {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      onClick={toggle}
      className={`btn btn-quiet btn-icon ${className}`}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
    </button>
  )
}
