/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.{html,js}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        orange: {
          50: '#fff4eb',
          100: '#ffe4d1',
          200: '#ffc4a8',
          300: '#ffa174',
          400: '#ff7e33',
          500: '#ff5700', // Logo Orange
          600: '#e64e00', // Darker for hover
        },
        gray: {
          50: '#fcfcfc',
          100: '#f3f4f6',
          200: '#e5e7eb',
          800: '#2b2626', // Softer charcoal
          900: '#1a1717', // Logo Charcoal
        },
        navy: {
          DEFAULT: '#0B1120',
          800: '#15213A',
          900: '#070B14',
          950: '#05080E',
        },
        surface: {
          canvas: '#0B1120',
          card: '#15213A',
          elevated: '#1E293B',
          highlight: '#233354',
        },
        coral: {
          DEFAULT: '#FF6441',
          light: '#FFA174', // Certified 6.52:1 CR for normal badge text
          dark: '#E04826',
        },
        blue: {
          brand: '#3B82F6',
          glow: 'rgba(59, 130, 246, 0.25)',
        }
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(0, 0, 0, 0.05)',
        'badge': '0 2px 10px -1px rgba(0, 0, 0, 0.04)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glow-coral': '0 0 30px rgba(255, 100, 65, 0.35)',
        'glow-blue': '0 0 30px rgba(59, 130, 246, 0.25)',
        'glass-rim': '0 10px 30px -5px rgba(0, 0, 0, 0.4), inset 0 1px 0 0 rgba(255, 255, 255, 0.15)',
        'conic-halo': '0 0 25px -2px rgba(255, 100, 65, 0.45)',
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'fade-in': 'fadeIn 1s ease-out forwards',
        'marquee-left': 'marqueeLeft 35s linear infinite',
        'marquee-right': 'marqueeRight 35s linear infinite',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: 0, transform: 'translateY(20px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        // Mathematically seamless marquee translation (0px loop jump)
        marqueeLeft: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        marqueeRight: {
          '0%': { transform: 'translateX(-50%)' },
          '100%': { transform: 'translateX(0%)' },
        }
      }
    },
  },
  plugins: [],
}
