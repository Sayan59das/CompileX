export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#05050A',
        surface: {
          DEFAULT: '#0A0A10',
          50: '#101018',
          100: '#141420',
          200: '#1A1A28',
          300: '#202030',
        },
        card: 'rgba(255,255,255,0.03)',
        'card-hover': 'rgba(255,255,255,0.06)',
        border: {
          DEFAULT: 'rgba(255,255,255,0.06)',
          light: 'rgba(255,255,255,0.1)',
          glow: 'rgba(99,102,241,0.5)',
        },
        primary: {
          DEFAULT: '#3b82f6',
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        secondary: {
          DEFAULT: '#06b6d4',
          400: '#22d3ee',
          500: '#06b6d4',
        },
        accent: {
          DEFAULT: '#6366f1',
          400: '#818cf8',
          500: '#6366f1',
        },
        success: {
          DEFAULT: '#10b981',
          400: '#34d399',
          500: '#10b981',
        },
        danger: {
          DEFAULT: '#f43f5e',
          400: '#fb7185',
          500: '#f43f5e',
        },
        warning: {
          DEFAULT: '#f59e0b',
          400: '#fbbf24',
          500: '#f59e0b',
        },
      },
      fontFamily: {
        sans: ['Space Mono', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Space Mono', 'JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Space Mono', 'Poppins', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'glow': '0 0 20px rgba(59, 130, 246, 0.3)',
        'glow-lg': '0 0 40px rgba(59, 130, 246, 0.4)',
        'glow-sm': '0 0 10px rgba(59, 130, 246, 0.2)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 8px 32px rgba(0, 0, 0, 0.5)',
        'inner': 'inset 0 2px 4px rgba(0, 0, 0, 0.2)',
      },
      backgroundImage: {
        'hero-glow': 'radial-gradient(ellipse 100% 60% at 50% -10%, rgba(59,130,246,0.2), transparent)',
        'hero-glow-alt': 'radial-gradient(ellipse 80% 50% at 50% 100%, rgba(99,102,241,0.15), transparent)',
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-primary': 'linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)',
        'gradient-success': 'linear-gradient(135deg, #10b981 0%, #22d3ee 100%)',
        'gradient-danger': 'linear-gradient(135deg, #f43f5e 0%, #818cf8 100%)',
        'gradient-bg': 'linear-gradient(180deg, #05050A 0%, #0A0A10 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'fade-in-up': 'fadeInUp 0.6s ease-out',
        'fade-in-down': 'fadeInDown 0.5s ease-out',
        'slide-in-right': 'slideInRight 0.5s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'gradient': 'gradient 8s ease infinite',
        'bounce-subtle': 'bounceSubtle 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
        fadeInUp: {
          from: { opacity: 0, transform: 'translateY(20px)' },
          to: { opacity: 1, transform: 'translateY(0)' },
        },
        fadeInDown: {
          from: { opacity: 0, transform: 'translateY(-20px)' },
          to: { opacity: 1, transform: 'translateY(0)' },
        },
        slideInRight: {
          from: { opacity: 0, transform: 'translateX(20px)' },
          to: { opacity: 1, transform: 'translateX(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(59, 130, 246, 0.3)' },
          '50%': { boxShadow: '0 0 40px rgba(59, 130, 246, 0.5)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}
