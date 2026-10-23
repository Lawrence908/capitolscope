import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

/**
 * Bulletin theme toggle: a square 2px box in the current text color with a
 * half-filled disc. Works on the ink masthead slab and on the page surface
 * because it only uses currentColor. `showLabel` adds "Dark mode" / "Light mode".
 */
const DarkModeToggle: React.FC<{ showLabel?: boolean; className?: string }> = ({
  showLabel = false,
  className = '',
}) => {
  const { isDarkMode, toggleDarkMode } = useTheme();
  const label = isDarkMode ? 'Light mode' : 'Dark mode';

  return (
    <button
      type="button"
      onClick={toggleDarkMode}
      aria-pressed={isDarkMode}
      aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
      title={label}
      className={`inline-flex items-center gap-2 border-2 border-current px-2.5 py-1.5 font-ui text-sm font-semibold transition-opacity hover:opacity-80 ${className}`}
    >
      <span
        aria-hidden="true"
        className="inline-block h-3.5 w-3.5 rounded-full border-2 border-current"
        style={{ background: 'linear-gradient(90deg, currentColor 50%, transparent 50%)' }}
      />
      {showLabel && <span>{label}</span>}
    </button>
  );
};

export default DarkModeToggle;
