import React from 'react';
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../contexts/ThemeContext';

const DarkModeToggle: React.FC = () => {
  const { isDarkMode, toggleDarkMode } = useTheme();

  return (
    <button
      onClick={toggleDarkMode}
      className="rounded-md border border-line bg-surface-inset p-2 transition-colors duration-200 hover:border-accent"
      aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDarkMode ? (
        <SunIcon className="h-5 w-5 text-accent-2" />
      ) : (
        <MoonIcon className="h-5 w-5 text-accent" />
      )}
    </button>
  );
};

export default DarkModeToggle; 