/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.{html,js}"],
  theme: {
    extend: {
      colors: {
        orange: {
          50: '#fff4eb',
          100: '#ffe4d1',
          200: '#ffc4a8',
          300: '#ffa174',
          400: '#ff7e33',
          500: '#ff5700', // Your exact Logo Orange
          600: '#e64e00', // Slightly darker for hover states
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          800: '#2b2626', // Softer charcoal for secondary text
          900: '#1a1717', // Your exact Logo Charcoal
        }
      }
    },
  },
  plugins: [],
}