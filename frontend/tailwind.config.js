/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f0ff',
          100: '#e4e3fe',
          200: '#cccbfd',
          500: '#7F77DD',
          600: '#6259c7',
          700: '#534AB7',
        },
      },
    },
  },
  plugins: [],
}