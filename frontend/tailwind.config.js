/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Design tokens from the RAG Workbench (github.com/evangoh122/Rag_workbench,
      // frontend/src/index.css "evidence-first obsidian, silver and gold palette").
      colors: {
        background: "#090A0C",
        surface: "#111317",
        surfaceElevated: "#181B20",
        primary: "#F3F1EA",
        secondary: "#B8BDC5",
        muted: "#818791",
        border: "#32363D",
        borderSubtle: "#22262C",
        accent: "#D6B65A",
        accentBright: "#F1D77A",
        accentFill: "#C9A227",
        accentInk: "#171205",
        silver: "#C7CBD1",
        silverDim: "#8D949E",
        bullish: "#43D19E",
        bearish: "#FF727F",
        // Semantic aliases used across pages (mapped onto the palette above).
        navy: "#111317",
        navy2: "#181B20",
        navy3: "#1D222C",
        ink: "#F3F1EA",
        line: "#32363D",
        paper: "#0C0E11",
        amber: "#D6B65A",
        amberbg: "rgba(214, 182, 90, 0.14)",
        green: "#43D19E",
        greenbg: "rgba(67, 209, 158, 0.12)",
        rose: "#FF727F",
        rosebg: "rgba(255, 114, 127, 0.12)",
        gold: "#D6B65A",
      },
      fontFamily: {
        sans: ["Geist", "Segoe UI Variable", "SF Pro Display", "system-ui", "sans-serif"],
        serif: ["Georgia", "Times New Roman", "serif"],
        mono: ["JetBrains Mono", "SF Mono", "Geist Mono", "Fira Code", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "8px",
      },
    },
  },
  plugins: [],
};
