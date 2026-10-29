/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cl: {
          bg: '#070708',
          surface: '#0D0E10',
          card: '#151619',
          'card-hover': '#1E1F22',
          text: '#F6F6F3',
          'text-muted': '#B9B9B3',
          gold: '#D9B15F',
          'gold-hover': '#E7C479',
          'gold-dark': '#9A7A38',
          'chart-blue': '#438AF5',
          'chart-amber': '#E6A63B',
          'chart-purple': '#A17CF2',
          border: 'rgba(255, 255, 255, 0.13)',
          'border-gold': 'rgba(217, 177, 95, 0.35)',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Cinzel', 'Trajan Pro', 'Georgia', 'serif'],
      },
      boxShadow: {
        'gold-glow': '0 0 25px rgba(217, 177, 95, 0.25)',
        'gold-pill': '0 0 15px rgba(217, 177, 95, 0.18)',
      }
    },
  },
  plugins: [],
}
