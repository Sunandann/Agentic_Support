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
  ink: { DEFAULT: '#3A1F2E', soft: '#6B4559', faint: '#836676' }, // text
  paper: '#F8F4E9',    // page background (cream)
  surface: '#FFFBF3',  // cards, panels, inputs
  line: '#F6DBC0',     // borders and dividers (peach)
  signal: { DEFAULT: '#935073', tint: '#F6DBC0', dark: '#7A3F5E' }, // accent (plum)
  flag: { DEFAULT: '#B8402F', tint: '#FBE0D8' },
  done: { DEFAULT: '#5E7A5A', tint: '#E6EEDF' },
},
    },
  },
  plugins: [],
}
