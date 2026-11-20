/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: 'rgb(var(--bg-rgb) / <alpha-value>)',
        surface: {
          DEFAULT: 'rgb(var(--surface-rgb) / <alpha-value>)',
          2: 'rgb(var(--surface-2-rgb) / <alpha-value>)',
        },
        ink: {
          DEFAULT: 'rgb(var(--ink-rgb) / <alpha-value>)',
          muted: 'rgb(var(--ink-muted-rgb) / <alpha-value>)',
        },
        brand: {
          DEFAULT: 'rgb(var(--brand-rgb) / <alpha-value>)',
          2: 'rgb(var(--brand-2-rgb) / <alpha-value>)',
        },
        leaf: 'rgb(var(--leaf-rgb) / <alpha-value>)',
        warn: 'rgb(var(--warn-rgb) / <alpha-value>)',
        danger: 'rgb(var(--danger-rgb) / <alpha-value>)',
        line: 'rgb(var(--line-rgb) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['Fraunces', 'Playfair Display', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      borderRadius: {
        'sm': '8px',
        'DEFAULT': '12px',
        'md': '12px',
        'lg': '20px',
        'packet': '16px 4px 16px 4px', // Signature snack packet status chip shape
      },
      boxShadow: {
        'warm-sm': '0 1px 2px 0 rgba(31, 26, 20, 0.05)',
        'warm-md': '0 4px 6px -1px rgba(31, 26, 20, 0.08), 0 2px 4px -2px rgba(31, 26, 20, 0.04)',
        'warm-lg': '0 10px 15px -3px rgba(31, 26, 20, 0.08), 0 4px 6px -4px rgba(31, 26, 20, 0.04)',
        'warm-xl': '0 20px 25px -5px rgba(31, 26, 20, 0.10), 0 8px 10px -6px rgba(31, 26, 20, 0.05)',
        'warm-inner': 'inset 0 2px 4px 0 rgba(31, 26, 20, 0.06)',
      },
      transitionDuration: {
        'instant': '100ms',
        'fast': '180ms',
        'base': '280ms',
        'slow': '480ms',
        'hero': '900ms',
      },
      transitionTimingFunction: {
        'standard': 'cubic-bezier(0.2, 0, 0, 1)',
        'emphasize': 'cubic-bezier(0.05, 0.7, 0.1, 1)',
        'exit': 'cubic-bezier(0.3, 0, 0.8, 0.15)',
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      spacing: {
        'touch': '44px', // WCAG 2.2 AA minimum touch target size
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms')({
      strategy: 'class',
    }),
    require('@tailwindcss/typography'),
  ],
};
