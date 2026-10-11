// Every colour is a CSS variable holding space-separated RGB channels (see
// src/index.css), so `bg-panel/60` style opacity modifiers work and the whole
// palette flips with `[data-theme="dark"]` without any `dark:` variants.
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        paper: token('paper'),
        panel: token('panel'),
        sunken: token('sunken'),
        line: { DEFAULT: token('line'), strong: token('line-strong') },
        ink: { DEFAULT: token('ink'), 2: token('ink-2'), 3: token('ink-3') },

        // Balloon palette: fills, plus an "-ink" variant legible as text.
        tomato: { DEFAULT: token('tomato'), ink: token('tomato-ink') },
        sun: { DEFAULT: token('sun'), ink: token('sun-ink') },
        grass: { DEFAULT: token('grass'), ink: token('grass-ink') },
        sky: { DEFAULT: token('sky'), ink: token('sky-ink') },
        violet: { DEFAULT: token('violet'), ink: token('violet-ink') },
        tangerine: { DEFAULT: token('tangerine'), ink: token('tangerine-ink') },

        // Code slabs stay dark in both themes.
        slab: {
          DEFAULT: token('slab'),
          2: token('slab-2'),
          line: token('slab-line'),
          ink: token('slab-ink'),
          dim: token('slab-dim'),
        },
      },
      fontFamily: {
        sans: ['Archivo', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        md: '8px',
        lg: '10px',
      },
      boxShadow: {
        float: '0 12px 32px rgb(var(--shadow) / 0.18), 0 2px 6px rgb(var(--shadow) / 0.08)',
      },
      // Motion is reserved for things that change state: spinners (built in),
      // and a short fade for menus and toasts that appear on demand.
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
      },
      animation: {
        'fade-in': 'fade-in 120ms ease-out both',
      },
    },
  },
  plugins: [],
}
