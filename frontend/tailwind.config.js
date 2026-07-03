/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-blue': '#2563eb',
        'brand-navy': '#0f172a',
        'brand-navy-mid': '#1e3a8a',
      },
    },
  },
  plugins: [],
}