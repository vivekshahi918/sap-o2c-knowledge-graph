/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sapGray: '#111827',
        sapPanel: '#1f2937',
        sapBlue: '#3b82f6',
        sapOrange: '#f97316',
        sapGreen: '#22c55e',
        sapText: '#f3f4f6',
      },
    },
  },
  plugins: [],
}