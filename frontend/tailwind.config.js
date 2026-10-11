/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Theme: "Grand Tourer" (Midnight Navy & Champagne)
        midnight: {
          950: '#06080B',
          DEFAULT: '#0A0C10', // Midnight Ink Background
          surface: '#14171E', // Deep Navy Slate Surface
          raised: '#1B1F28',  // Hover / Raised Surface
          elevated: '#222733',
        },
        champagne: {
          50: '#FAF7F2',
          100: '#F4ECE0',
          200: '#E7D9C3',
          DEFAULT: '#D4C4A8', // Champagne / Silk Accent
          400: '#D4C4A8',
          500: '#C5B293',
          600: '#A99472',
          glow: 'rgba(212, 196, 168, 0.25)',
          subtle: 'rgba(212, 196, 168, 0.12)',
        },
        silver: {
          DEFAULT: '#E5E7EB', // Cool Silver Primary Text
          muted: '#9CA3AF',   // Muted Text (~60%)
          subtle: '#6B7280',  // Subtle Text (~40%)
        },
        gunmetal: {
          DEFAULT: '#4B5563', // Brushed Gunmetal Secondary / Status
          border: 'rgba(75, 85, 99, 0.35)',
          light: '#374151',
          subtle: '#1F2937',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'champagne-sm': '0 0 15px -3px rgba(212, 196, 168, 0.18)',
        'champagne-md': '0 0 25px -5px rgba(212, 196, 168, 0.28)',
        'champagne-lg': '0 0 35px -5px rgba(212, 196, 168, 0.38)',
        'gt-card': '0 10px 30px -10px rgba(0, 0, 0, 0.6)',
      },
    },
  },
  plugins: [],
}
