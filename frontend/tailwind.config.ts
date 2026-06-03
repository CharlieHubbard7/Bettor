import type { Config } from "tailwindcss";

// Dark theme by default — Bloomberg Terminal aesthetic. Phase 2 wires this up.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        positive: "#34d399", // emerald-400
        negative: "#f87171", // red-400
        neutral: "#fbbf24", // amber-400
      },
    },
  },
  plugins: [],
} satisfies Config;
