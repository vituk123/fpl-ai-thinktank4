/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        retro: {
          primary: '#1D1D1B',
          secondary: '#C1C1BF',
          bg: '#DADAD3',
          error: '#E84C3D',
          text: '#1D1D1B',
          textSec: 'rgba(29, 29, 27, 0.7)',
        }
      },
      boxShadow: {
        'retro': '-0.6rem 0.6rem 0 rgba(29, 30, 28, 0.26)',
        'retro-hover': '-0.4rem 0.4rem 0 rgba(29, 30, 28, 0.26)',
        'retro-active': '0 0 0 rgba(29, 30, 28, 0.26)',
      },
      borderWidth: {
        'retro': '2.5px',
      },
      fontFamily: {
        sans: ['Roboto', 'system-ui', 'sans-serif'],
      }
    }
  },
  plugins: [],
}
