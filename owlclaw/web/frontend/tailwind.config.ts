import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(220 16% 9%)",
        foreground: "hsl(210 20% 96%)",
        card: "hsl(222 16% 12%)",
        border: "hsl(220 12% 24%)",
        primary: "hsl(174 90% 36%)",
        muted: "hsl(220 12% 18%)",
        danger: "hsl(0 72% 52%)",
        warning: "hsl(38 92% 52%)",
      },
    },
  },
  plugins: [],
} satisfies Config;
