/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#0A0B0E',
        secondary: '#111318',
        card: '#161B24',
        border: '#1E2532',
        primary: '#00D4FF',
        bull: '#00E676',
        bear: '#FF3B3B',
        warning: '#FFB800',
        text: {
          primary: '#E8EAED',
          secondary: '#8B9BB4',
        },
      },
      fontFamily: {
        heading: ['Clash Display', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        body: ['Cabinet Grotesk', 'sans-serif'],
      },
    },
  },
  plugins: [],
};