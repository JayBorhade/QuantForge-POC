/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        forge: {
          black: "#080C14",
          dark: "#0D1421",
          panel: "#111827",
          border: "#1E2D45",
          blue: "#0EA5E9",
          emerald: "#10B981",
          amber: "#F59E0B",
          red: "#EF4444"
        }
      }
    }
  },
  plugins: []
};
