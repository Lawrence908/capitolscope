/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        // Supabase-inspired palette
        bg: {
          primary: '#0d1117',      // GitHub dark background
          secondary: '#161b22',   // Slightly lighter for cards/sections
          tertiary: '#21262d',    // Even lighter for elevated elements
        },
        // Light mode backgrounds - matching landing page style
        'bg-light': {
          primary: '#ffffff',      // Pure white background
          secondary: '#f9fafb',   // Light gray for cards (matching landing page)
          tertiary: '#f3f4f6',    // Slightly darker for elevated elements
        },
        // Primary accent - subtle blue for interactive elements
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',    // Main accent blue
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Secondary accent - subtle green for success states
        secondary: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',    // Success green
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        // Neutral grays - matching landing page style
        neutral: {
          50: '#ffffff',      // Pure white
          100: '#f9fafb',     // Light background gray
          200: '#f3f4f6',     // Card background
          300: '#e5e7eb',     // Light border
          400: '#d1d5db',     // Muted text
          500: '#9ca3af',     // Medium gray
          600: '#6b7280',     // Light gray text
          700: '#374151',     // Dark gray text
          800: '#1f2937',     // Very dark gray
          900: '#111827',     // Almost black
        },
        // Semantic colors - minimal and clean
        success: '#22c55e',
        warning: '#f59e0b',
        error: '#ef4444',
        info: '#3b82f6',
        // Border colors - matching landing page style
        border: {
          light: '#e5e7eb',      // Light gray border (matching landing page)
          dark: '#30363d',       // Dark mode border
          muted: '#d1d5db',      // Muted border for light mode
        }
      },
      // Clean shadows - subtle and minimal
      boxShadow: {
        'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
      },
      // Clean gradients
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
      // Typography
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Monaco', 'Consolas', 'monospace'],
      },
      // Spacing for clean layouts
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      // Border radius for clean, modern look
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      }
    },
  },
  plugins: [],
} 