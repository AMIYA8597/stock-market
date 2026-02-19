import type { Config } from "tailwindcss";
import preset from "@neuroquant/config/tailwind.preset";

const config: Config = {
  presets: [preset],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
};

export default config;
