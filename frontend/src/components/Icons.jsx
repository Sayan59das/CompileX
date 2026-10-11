import React from 'react'

// One small, consistent icon set: 24px grid, 1.8 stroke, square caps and mitred
// joins so everything reads as drawn with the same pen. Replaces emoji.
const SHAPES = {
  play: <path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none" />,
  check: <path d="M4.5 12.5l5 5 10-11" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  plus: <path d="M12 5v14M5 12h14" />,
  minus: <path d="M5 12h14" />,
  'arrow-right': <path d="M4 12h15M13 6l6 6-6 6" />,
  'arrow-left': <path d="M20 12H5M11 6l-6 6 6 6" />,
  'chevron-down': <path d="M6 9l6 6 6-6" />,
  'chevron-up': <path d="M6 15l6-6 6 6" />,
  'chevron-right': <path d="M9 6l6 6-6 6" />,
  copy: (
    <>
      <rect x="8.5" y="8.5" width="11.5" height="11.5" />
      <path d="M15.5 8.5V4H4v11.5h4.5" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7v5.2l3.4 2" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8.5" r="3.5" />
      <path d="M2.5 20c0-3.5 2.9-5.8 6.5-5.8s6.5 2.3 6.5 5.8" />
      <path d="M15.6 5.2a3.5 3.5 0 010 6.6M18 14.6c2 .8 3.5 2.5 3.5 5.4" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 20.5c0-4 3.2-6.5 7.5-6.5s7.5 2.5 7.5 6.5" />
    </>
  ),
  trophy: (
    <>
      <path d="M7 4h10v6a5 5 0 01-10 0z" />
      <path d="M7 6H3.5v1.5A3.5 3.5 0 007 11M17 6h3.5v1.5A3.5 3.5 0 0117 11" />
      <path d="M12 15v4M8 20h8" />
    </>
  ),
  code: <path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13.6 5l-3.2 14" />,
  terminal: (
    <>
      <rect x="3" y="4.5" width="18" height="15" />
      <path d="M7 9.5l3 2.5-3 2.5M12.5 15H17" />
    </>
  ),
  bars: <path d="M5 20V12M12 20V4M19 20v-9M3 20.5h18" />,
  trend: <path d="M3 17l6-6 4 4 8-9M15 6h6v6" />,
  lock: (
    <>
      <rect x="5" y="10.5" width="14" height="10" />
      <path d="M8 10.5V8a4 4 0 018 0v2.5" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" />
      <circle cx="12" cy="12" r="2.8" />
    </>
  ),
  'eye-off': (
    <>
      <path d="M2 12s3.6-6.5 10-6.5c1.3 0 2.5.3 3.6.7M22 12s-3.6 6.5-10 6.5c-1.3 0-2.5-.3-3.6-.7" />
      <path d="M4 4l16 16" />
    </>
  ),
  refresh: <path d="M20 11a8 8 0 10-.8 5M20 4v7h-7" />,
  send: <path d="M21 3L10.5 13.5M21 3l-6.5 18-4-7.5L3 9.5z" />,
  flag: <path d="M5 21V4M5 4h13l-2.5 4.5L18 13H5" />,
  bolt: <path d="M13.5 2.5L5 13.5h6l-1 8 8.5-11h-6z" />,
  menu: <path d="M3.5 6.5h17M3.5 12h17M3.5 17.5h17" />,
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8" />
    </>
  ),
  moon: <path d="M20 14.5A8.5 8.5 0 019.5 4 8.5 8.5 0 1020 14.5z" />,
  upload: <path d="M12 16V4M7 9l5-5 5 5M4 17v3h16v-3" />,
  download: <path d="M12 4v12M7 11l5 5 5-5M4 17v3h16v-3" />,
  file: (
    <>
      <path d="M6 3h8l5 5v13H6z" />
      <path d="M14 3v5h5" />
    </>
  ),
  logout: <path d="M9 4H4v16h5M16 8l4 4-4 4M20 12H9" />,
  duel: (
    <>
      <path d="M4 20L16 8M13 5l6-1-1 6" />
      <path d="M20 20L8 8M11 5L5 4l1 6" />
    </>
  ),
  bracket: <path d="M3 5h5v5h4M3 19h5v-5h4M12 10v4M12 12h9" />,
  gauge: (
    <>
      <path d="M3.5 17a8.5 8.5 0 1117 0" />
      <path d="M12 17l4-6" />
    </>
  ),
  bulb: (
    <>
      <path d="M9 17.5h6M10 21h4" />
      <path d="M12 3a6 6 0 00-3.5 10.9c.6.5 1 1.2 1 2V17.5h5v-1.6c0-.8.4-1.5 1-2A6 6 0 0012 3z" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7.2v.1" />
    </>
  ),
  alert: (
    <>
      <path d="M12 3.5l10 17.5H2z" />
      <path d="M12 10v5M12 17.8v.1" />
    </>
  ),
  search: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M15.5 15.5L21 21" />
    </>
  ),
  history: <path d="M3.5 12a8.5 8.5 0 108.5-8.5c-2.7 0-5 1.2-6.6 3.2M3.5 4v4.5H8M12 8v4.5l3 1.8" />,
  layers: <path d="M12 3l9 5-9 5-9-5zM3 12.5l9 5 9-5M3 16.5l9 5 9-5" />,
  list: <path d="M8.5 6.5H21M8.5 12H21M8.5 17.5H21M3.5 6.5h.1M3.5 12h.1M3.5 17.5h.1" />,
  message: <path d="M4 5h16v11H9.5L5 20v-4H4z" />,
  target: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4" />
      <path d="M12 12h.1" />
    </>
  ),
  pencil: <path d="M4 20l1-4.5L16.5 4l3.5 3.5L8.5 19z" />,
  sidebar: (
    <>
      <rect x="3" y="4" width="18" height="16" />
      <path d="M9.5 4v16" />
    </>
  ),
  'panel-bottom': (
    <>
      <rect x="3" y="4" width="18" height="16" />
      <path d="M3 14.5h18" />
    </>
  ),
  home: <path d="M3.5 11L12 3.5 20.5 11M6 9.5V20.5h12V9.5" />,
  circle: <circle cx="12" cy="12" r="8.5" />,
  'check-circle': (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M7.5 12.5l3 3 6-7" />
    </>
  ),
  'x-circle': (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9 9l6 6M15 9l-6 6" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" />
      <path d="M3 6l9 7 9-7" />
    </>
  ),
  key: (
    <>
      <circle cx="8" cy="15" r="4.5" />
      <path d="M11.5 11.5L20 3M16 7l3 3" />
    </>
  ),
  medal: (
    <>
      <circle cx="12" cy="14.5" r="5.5" />
      <path d="M8.5 10L6 3h4l2 4 2-4h4l-2.5 7" />
    </>
  ),
}

export default function Icon({ name, size = 18, strokeWidth = 1.8, className = '', ...rest }) {
  const shape = SHAPES[name]
  if (!shape) return null
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="square"
      strokeLinejoin="miter"
      className={`shrink-0 ${className}`}
      aria-hidden="true"
      {...rest}
    >
      {shape}
    </svg>
  )
}

// Brand marks keep their own colours, so they live outside the stroke set.
export function GoogleMark({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  )
}

export function GithubMark({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  )
}
