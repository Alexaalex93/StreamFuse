import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Manrope", "ui-sans-serif", "sans-serif"],
        display: ["Space Grotesk", "Plus Jakarta Sans", "ui-sans-serif", "sans-serif"],
      },
      colors: {
        bg: "rgb(var(--color-bg) / <alpha-value>)",
        fg: "rgb(var(--color-fg) / <alpha-value>)",
        "fg-muted": "rgb(var(--color-fg-muted) / <alpha-value>)",
        card: "rgb(var(--color-card) / <alpha-value>)",
        sidebar: "rgb(var(--color-sidebar) / <alpha-value>)",
        topbar: "rgb(var(--color-topbar) / <alpha-value>)",
        primary: "rgb(var(--color-primary) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
      },
      backgroundImage: {
        "app-gradient": "var(--gradient-app)",
      },
      boxShadow: {
        premium: "0 22px 40px -24px rgba(4, 8, 18, 0.9), 0 12px 28px -20px rgba(34, 211, 238, 0.28)",
      },
    },
  },
  plugins: [],
} satisfies Config;
