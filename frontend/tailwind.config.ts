import type { Config } from "tailwindcss";

// Dark theme by default — Bloomberg Terminal aesthetic, an operator's tool.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#18181b", // zinc-900 — page background
          card: "#27272a", // zinc-800 — card backgrounds
          border: "#3f3f46", // zinc-700 — borders
          muted: "#52525b", // zinc-600 — muted text
        },
        signal: {
          profit: "#34d399", // emerald-400
          loss: "#f87171", // red-400
          warn: "#fbbf24", // amber-400
          neutral: "#94a3b8", // slate-400
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
