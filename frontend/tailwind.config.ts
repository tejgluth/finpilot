import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14202b",
        mist: "#f5f1e8",
        slate: "#edf2f5",
        tide: "#2f6f6d",
        ember: "#ca5f3f",
        pine: "#244038",
        gold: "#b8923c",
      },
      fontFamily: {
        display: ["'Avenir Next Condensed'", "'Trebuchet MS'", "sans-serif"],
        body: ["'Avenir Next'", "'Segoe UI'", "sans-serif"],
        mono: ["'SFMono-Regular'", "'Menlo'", "monospace"],
      },
      boxShadow: {
        soft: "0 18px 50px rgba(20, 32, 43, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
