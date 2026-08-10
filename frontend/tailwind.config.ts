import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        plum: {
          950: '#190516', // Dark Plum
          900: '#2A0822', // Primary Plum
          800: '#3A0C2E', // Surface Plum
          700: '#48103A', // Elevated Plum
        },
        coral: {
          400: '#FF6B7F', // Soft Accent
          500: '#FF3F5F', // Primary Accent
        },
        cream: {
          50: '#FFF8F3', // Warm White
          100: '#F7EDE8', // Muted Cream
        },
        text: {
          primary: '#241722', // Primary Text on Light
          secondary: '#6E5D68', // Secondary Text
        },
        border: {
          plum: 'rgba(42, 8, 34, 0.10)',
        },
        success: '#10B981', // Restrained green
        warning: '#F59E0B', // Warm amber
        danger: '#FF3F5F', // Coral/red
        info: '#6366F1', // Muted blue/purple
      },
      fontFamily: {
        serif: ['var(--font-dm-serif)', 'serif'],
        sans: ['var(--font-inter)', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 4px 20px rgba(42, 8, 34, 0.05)',
        elevated: '0 10px 40px rgba(42, 8, 34, 0.1)',
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '24px',
      },
      backgroundImage: {
        'plum-gradient': 'radial-gradient(circle at top left, rgba(255, 63, 95, 0.15), transparent 40%), linear-gradient(180deg, #2A0822 0%, #190516 100%)',
      }
    },
  },
  plugins: [],
};

export default config;
