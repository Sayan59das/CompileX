// CompileX design tokens.
//
// Palette, picked for a competitive-coding arena:
//   ground   deep midnight navy         (the dark a code editor lives in)
//   arc      electric cyan              YOU: your cursor, your side of a match, the main action
//   rival    ultraviolet                the other player
//   pass     mint                       tests passing
//   fail     coral                      tests failing
// The pages were written against Tailwind's default slate / blue / cyan / indigo / violet scales, so those scales are
// re-pointed here instead of editing every class: greys become a cool navy ramp, blue becomes electric blue, cyan is the
// arc, indigo and violet are the rival colour.

const navy = {
  50:  '#F5F5F5',
  100: '#E6E6E6',
  200: '#D0D0D0',
  300: '#B0B0B0',
  400: '#8C8C8C',
  500: '#737373',
  600: '#525252',
  700: '#333333',
  800: '#1C1C1C',
  900: '#0F0F0F',
  950: '#050505',
}

const blue = {
  50: '#EBF4FF', 100: '#D6E8FF', 200: '#ADD0FF', 300: '#84B8FF', 400: '#5AA2FF',
  500: '#3B8CFF', 600: '#2B70E8', 700: '#2158BD', 800: '#1D4691', 900: '#1B3A73', 950: '#112448',
}

const cyan = {
  50: '#E6FBFF', 100: '#C7F6FF', 200: '#96EEFF', 300: '#66E6FF', 400: '#3DE0FF',
  500: '#17CDEF', 600: '#0FA6C6', 700: '#0C7F9B', 800: '#0B5C73', 900: '#0A3F50', 950: '#052A36',
}

const violet = {
  50: '#F3EFFF', 100: '#E7DFFF', 200: '#CFBFFF', 300: '#B8A0FF', 400: '#A387FF',
  500: '#8B6CFF', 600: '#7050EA', 700: '#5A3EC2', 800: '#453096', 900: '#352570', 950: '#1F1544',
}

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        slate: navy, gray: navy, zinc: navy, neutral: navy, stone: navy,
        blue, sky: cyan, cyan, teal: cyan,
        indigo: violet, violet, purple: violet, fuchsia: violet,

        ink: '#000000',
        arc: { DEFAULT: '#3DE0FF', ...cyan },
        rival: { DEFAULT: '#9B7BFF', ...violet },
        pass: '#35F2A0',
        fail: '#FF5C7A',

        bg: '#000000',
        surface: { DEFAULT: '#0A0A0A', 50: '#0F0F0F', 100: '#141414', 200: '#1A1A1A', 300: '#262626' },
        card: 'rgba(255,255,255,0.04)',
        'card-hover': 'rgba(255,255,255,0.08)',
        border: { DEFAULT: 'rgba(255,255,255,0.12)', light: 'rgba(255,255,255,0.2)', glow: 'rgba(61,224,255,0.5)' },
        primary: { DEFAULT: '#3B8CFF', ...blue },
        secondary: { DEFAULT: '#17CDEF', 400: '#3DE0FF', 500: '#17CDEF' },
        accent: { DEFAULT: '#8B6CFF', 400: '#A387FF', 500: '#8B6CFF' },
        success: { DEFAULT: '#35F2A0', 400: '#35F2A0', 500: '#18D68A' },
        danger: { DEFAULT: '#FF5C7A', 400: '#FF7E96', 500: '#FF5C7A' },
        warning: { DEFAULT: '#FFC857', 400: '#FFD479', 500: '#FFC857' },
      },
      fontFamily: {
        sans: ['"Onest Variable"', 'Onest', 'system-ui', 'sans-serif'],
        display: ['"Sora Variable"', 'Sora', '"Onest Variable"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono Variable"', '"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 24px rgba(61, 224, 255, 0.25)',
        'glow-lg': '0 0 44px rgba(61, 224, 255, 0.32)',
        'glow-sm': '0 0 12px rgba(61, 224, 255, 0.2)',
        card: '0 4px 24px rgba(0, 0, 0, 0.45)',
        'card-hover': '0 10px 36px rgba(0, 0, 0, 0.55)',
      },
      backgroundImage: {
        'hero-glow': 'radial-gradient(ellipse 100% 60% at 50% -10%, rgba(61,224,255,0.14), transparent)',
        'hero-glow-alt': 'radial-gradient(ellipse 80% 50% at 50% 100%, rgba(139,108,255,0.12), transparent)',
        'gradient-primary': 'linear-gradient(135deg, #3B8CFF 0%, #17CDEF 100%)',
        'gradient-success': 'linear-gradient(135deg, #18D68A 0%, #3DE0FF 100%)',
        'gradient-danger': 'linear-gradient(135deg, #FF5C7A 0%, #A387FF 100%)',
        'gradient-bg': 'linear-gradient(180deg, #000000 0%, #0A0A0A 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s cubic-bezier(0.16,1,0.3,1)',
        'fade-in-up': 'fadeInUp 0.6s cubic-bezier(0.16,1,0.3,1)',
        'fade-in-down': 'fadeInDown 0.5s cubic-bezier(0.16,1,0.3,1)',
        'slide-in-right': 'slideInRight 0.5s cubic-bezier(0.16,1,0.3,1)',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        float: 'float 6s ease-in-out infinite',
        gradient: 'gradient 8s ease infinite',
        'bounce-subtle': 'bounceSubtle 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        fadeInUp: { from: { opacity: 0, transform: 'translateY(20px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        fadeInDown: { from: { opacity: 0, transform: 'translateY(-20px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        slideInRight: { from: { opacity: 0, transform: 'translateX(20px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
        pulseGlow: { '0%, 100%': { boxShadow: '0 0 20px rgba(61,224,255,0.25)' }, '50%': { boxShadow: '0 0 40px rgba(61,224,255,0.45)' } },
        float: { '0%, 100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-10px)' } },
        gradient: { '0%, 100%': { backgroundPosition: '0% 50%' }, '50%': { backgroundPosition: '100% 50%' } },
        bounceSubtle: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-5px)' } },
      },
      backdropBlur: { xs: '2px' },
    },
  },
  plugins: [],
}
