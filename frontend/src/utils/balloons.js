// The balloon palette, in the order problems are assigned colours (A, B, C…).
export const BALLOON_NAMES = ['tomato', 'sky', 'grass', 'sun', 'violet', 'tangerine']

/** CSS colour for a balloon name or index, usable in inline styles. */
export function balloonFill(nameOrIndex) {
  const name =
    typeof nameOrIndex === 'number'
      ? BALLOON_NAMES[((nameOrIndex % BALLOON_NAMES.length) + BALLOON_NAMES.length) % BALLOON_NAMES.length]
      : nameOrIndex
  return `rgb(var(--${name}))`
}

/** Text colour that stays legible on top of a balloon fill. */
export function onBalloon(nameOrIndex) {
  const name = typeof nameOrIndex === 'number' ? BALLOON_NAMES[nameOrIndex % BALLOON_NAMES.length] : nameOrIndex
  return name === 'sun' ? 'rgb(20 24 59)' : '#ffffff'
}

/** Stable balloon colour for a string (usernames), so a person keeps their colour. */
export function balloonForString(str = '') {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0
  return BALLOON_NAMES[h % BALLOON_NAMES.length]
}

export const DIFFICULTY = {
  easy: { label: 'Easy', color: 'grass' },
  medium: { label: 'Medium', color: 'sun' },
  hard: { label: 'Hard', color: 'tomato' },
}
