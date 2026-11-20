/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Instrument Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        ink: { DEFAULT: '#14222E', soft: '#4A5B6A', faint: '#7B8996' },
        paper: '#F2F5F7',
        line: '#D8DFE5',
        signal: { DEFAULT: '#0B7A75', tint: '#DCF0EE' },
        flag: { DEFAULT: '#C8450F', tint: '#FBE5DA' },
        done: { DEFAULT: '#3B4F8C', tint: '#E1E6F5' },
      },
    },
  },
  plugins: [],
}
