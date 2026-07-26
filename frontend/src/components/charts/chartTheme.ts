/**
 * Theme-aware colors for chart chrome (axes, grid, legend, tooltip).
 * Canvas can't read CSS vars, so we resolve fixed hexes from the current theme.
 * Charts call this with `isDarkMode` from `useTheme()` so they recolor on toggle.
 */
export interface ChartTheme {
  title: string;
  label: string;
  tick: string;
  grid: string;
  tooltipBg: string;
  tooltipTitle: string;
  tooltipBody: string;
  tooltipBorder: string;
}

export function chartTheme(isDark: boolean): ChartTheme {
  return isDark
    ? {
        title: '#e7eeec', // fog-200
        label: '#c3cec9', // fog-300
        tick: '#90a29d', // fog-500
        grid: 'rgba(144,162,157,0.14)',
        tooltipBg: '#17211d', // ink-800
        tooltipTitle: '#e7eeec',
        tooltipBody: '#c3cec9',
        tooltipBorder: '#24322d', // ink-600 / line
      }
    : {
        title: '#1a201e', // content
        label: '#4c554f', // content-muted
        tick: '#737b76', // content-faint
        grid: 'rgba(26,32,30,0.08)',
        tooltipBg: '#ffffff',
        tooltipTitle: '#1a201e',
        tooltipBody: '#4c554f',
        tooltipBorder: '#e0ded5', // line
      };
}
