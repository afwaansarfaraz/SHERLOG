/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14110F",
        soot: "#1D1915",
        ash: "#332D26",
        bone: "#E8E1D2",
        dust: "#8C8576",
        amber: {
          DEFAULT: "#E0A63A",
          sherlog: "#E0A63A",
        },
        vermilion: "#E4572E",
        verdigris: "#4FA38B",
        slate: {
          DEFAULT: "#8FA3C7",
          sherlog: "#8FA3C7",
        },
        oxblood: "#8E2F3C",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
      borderWidth: {
        1: "1px",
      },
    },
  },
  plugins: [],
}
