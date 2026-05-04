/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        gold: {
          400: '#FBBF24',
          500: '#F59E0B',
        },
        darkblue: {
          800: '#1E3A8A',
          900: '#1E40AF',
        }
      }
    },
  },
  plugins: [],
}
