import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Paleta Gardens Wood
        carbon: "#36454F",
        bone: "#F5F5DC",
        quebracho: "#654321",
        eucalyptus: "#5F8575",
        fire: "#E59500",
      },
      fontFamily: {
        heading: ["'Playfair Display'", "serif"],
        body: ["'Montserrat'", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
