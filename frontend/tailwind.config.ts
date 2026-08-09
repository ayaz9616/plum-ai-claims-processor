import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#101828',
        mist: '#f7f4ef',
        panel: '#fffaf4',
        line: '#e7ded2',
        accent: '#2f6f68',
        accentSoft: '#d9ece8',
      },
      boxShadow: {
        soft: '0 18px 50px rgba(16, 24, 40, 0.08)',
      },
    },
  },
  plugins: [],
};

export default config;
