/** @type {import('tailwindcss').Config} */
// UDYOGSETU redesign (Step 1): palette + motion tokens borrowed from NER Logistics.
// `blue` and `gray` are REMAPPED so every existing page picks up the new theme
// (navy primary, warm cream/ink neutrals) without editing each file.
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './features/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        border: 'hsl(var(--border))',
        cream: { DEFAULT: '#FFFFE3', soft: '#FFF9C9', deep: '#F4F3D8' },
        navy: { DEFAULT: '#173A59', 2: '#245477', ink: '#102A43' },
        coral: '#F07C61',
        sun: '#F2C94C',
        teal: { DEFAULT: '#2F9C84', 50: '#E8F6F2', 100: '#CDEBE3', 600: '#2F9C84', 700: '#237A67' },
        blue: {
          50: '#EEF4FC', 100: '#DCE8F8', 200: '#B9D1F1', 300: '#8FB4E7', 400: '#6497DD',
          500: '#3F7FD6', 600: '#1D4A72', 700: '#173A59', 800: '#122E47', 900: '#0D2236', 950: '#08182A',
        },
        gray: {
          50: '#FAFAEC', 100: '#F4F3D8', 200: '#E3E1C4', 300: '#CBC9AA', 400: '#93A0AB',
          500: '#617486', 600: '#4A6074', 700: '#33495D', 800: '#1F3A52', 900: '#102A43', 950: '#0A1B2C',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'ui-sans-serif', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: { '4xl': '2rem' },
      boxShadow: {
        soft: '0 18px 45px rgba(25, 54, 77, .10)',
        card: '0 8px 25px rgba(23, 58, 89, .06)',
        lift: '0 18px 34px rgba(23, 58, 89, .14)',
      },
      spacing: { '4.5': '1.125rem' },
      transitionTimingFunction: { out: 'cubic-bezier(0.22, 1, 0.36, 1)' },
      keyframes: {
        floaty: { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-10px)' } },
        drift: { to: { transform: 'translate(-35px,45px) scale(1.08)' } },
        pulseRing: { '50%': { boxShadow: '0 0 0 12px rgba(47,156,132,0)' } },
        gradientMove: { '0%': { backgroundPosition: '0% 50%' }, '100%': { backgroundPosition: '200% 50%' } },
        viewIn: { from: { opacity: 0, transform: 'translateY(10px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
      animation: {
        floaty: 'floaty 6s ease-in-out infinite',
        drift: 'drift 9s ease-in-out infinite alternate',
        'pulse-ring': 'pulseRing 2s infinite',
        'grad-move': 'gradientMove 6s linear infinite',
        'view-in': 'viewIn .4s cubic-bezier(0.22,1,0.36,1) both',
      },
    },
  },
  plugins: [],
}
