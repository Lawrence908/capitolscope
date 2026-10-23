import { useEffect, useState } from 'react';
import { Chart as ChartJS } from 'chart.js';

/**
 * Bulletin chart theming for chart.js.
 *
 * Canvas can't consume CSS custom properties directly, so colors are read
 * from the design-system variables in index.css at render time
 * (getComputedStyle on <html>). `useChartTheme()` re-reads them whenever the
 * <html> class list changes, so charts recolor on the dark-mode toggle.
 *
 * Encodings: data marks are ink, benchmarks are the gray `--bench`, and the
 * brand red is reserved for highlights. Parties are never color-coded.
 */
export interface ChartTheme {
  ink: string; // --content: data marks, titles
  muted: string; // --content-muted
  faint: string; // --content-faint: ticks, captions
  line: string; // --line: hairline gridlines
  inset: string; // --surface-inset
  surface: string; // --surface: slice separators
  accent: string; // --accent: highlights only
  bench: string; // --bench: benchmark (SPY) line
  slab: string; // tooltip background
  onSlab: string; // tooltip text
  slabMuted: string;
}

export const UI_FONT = '"Libre Franklin", system-ui, -apple-system, "Segoe UI", sans-serif';
export const DISPLAY_FONT = '"Big Shoulders Display", "Arial Narrow", Impact, sans-serif';

// Light-theme fallbacks (used only before the stylesheet is available).
const FALLBACK: ChartTheme = {
  ink: '#121417',
  muted: '#4a4f57',
  faint: '#6b7079',
  line: '#d5d7db',
  inset: '#ecedef',
  surface: '#ffffff',
  accent: '#c5302a',
  bench: '#9ca1a9',
  slab: '#121417',
  onSlab: '#ffffff',
  slabMuted: '#a9aeb6',
};

export function readChartTheme(): ChartTheme {
  if (typeof window === 'undefined' || typeof document === 'undefined') return FALLBACK;
  const css = getComputedStyle(document.documentElement);
  const v = (name: string, fb: string) => css.getPropertyValue(name).trim() || fb;
  return {
    ink: v('--content', FALLBACK.ink),
    muted: v('--content-muted', FALLBACK.muted),
    faint: v('--content-faint', FALLBACK.faint),
    line: v('--line', FALLBACK.line),
    inset: v('--surface-inset', FALLBACK.inset),
    surface: v('--surface', FALLBACK.surface),
    accent: v('--accent', FALLBACK.accent),
    bench: v('--bench', FALLBACK.bench),
    slab: v('--slab', FALLBACK.slab),
    onSlab: v('--on-slab', FALLBACK.onSlab),
    slabMuted: v('--slab-muted', FALLBACK.slabMuted),
  };
}

/** Current chart theme; updates when the theme class on <html> changes. */
export function useChartTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(readChartTheme);
  useEffect(() => {
    const el = document.documentElement;
    const obs = new MutationObserver(() => setTheme(readChartTheme()));
    obs.observe(el, { attributes: true, attributeFilter: ['class', 'style'] });
    return () => obs.disconnect();
  }, []);
  return theme;
}

/** `#rrggbb` or `rgb()` color with alpha, for fills under ink lines. */
export function withAlpha(color: string, alpha: number): string {
  const hex = color.trim();
  if (/^#[0-9a-f]{6}$/i.test(hex)) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  }
  if (/^#[0-9a-f]{3}$/i.test(hex)) {
    const [r, g, b] = hex.slice(1).split('').map((c) => parseInt(c + c, 16));
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  return hex;
}

/**
 * Neutral categorical ramp for pies/doughnuts (no hues): ink, bench gray,
 * muted, faint, inset. Label slices directly; never rely on color alone.
 */
export function neutralRamp(t: ChartTheme, n: number): string[] {
  const ramp = [t.ink, t.bench, t.muted, t.faint, t.inset];
  return Array.from({ length: n }, (_, i) => ramp[i % ramp.length]);
}

// ---- shared option fragments ----------------------------------------------

export const titleOptions = (t: ChartTheme, text?: string) => ({
  display: !!text,
  text,
  color: t.ink,
  align: 'start' as const,
  padding: { top: 0, bottom: 12 },
  font: { family: DISPLAY_FONT, size: 18, weight: 800 as const },
});

export const legendOptions = (t: ChartTheme, position: 'top' | 'right' | 'bottom' = 'top') => ({
  position,
  align: 'start' as const,
  labels: {
    color: t.muted,
    boxWidth: 12,
    boxHeight: 12,
    padding: 14,
    font: { family: UI_FONT, size: 12, weight: 600 as const },
  },
});

export const tooltipOptions = (t: ChartTheme) => ({
  backgroundColor: t.slab,
  titleColor: t.onSlab,
  bodyColor: t.onSlab,
  borderColor: t.slab,
  borderWidth: 0,
  cornerRadius: 0,
  padding: 10,
  boxPadding: 4,
  titleFont: { family: UI_FONT, size: 12, weight: 700 as const },
  bodyFont: { family: UI_FONT, size: 12 },
});

const tickFont = { family: UI_FONT, size: 11 };

/** Category axis: no gridlines, ink baseline. */
export const categoryAxis = (t: ChartTheme) => ({
  ticks: { color: t.faint, font: tickFont },
  grid: { display: false },
  border: { display: true, color: t.ink, width: 1 },
});

/** Value axis: hairline gridlines only, heavier ink at zero, no axis line. */
export const valueAxis = (t: ChartTheme) => ({
  ticks: { color: t.faint, font: tickFont, maxTicksLimit: 5 },
  grid: {
    color: (ctx: { tick?: { value?: number } }) => (ctx.tick?.value === 0 ? t.ink : t.line),
    drawTicks: false,
  },
  border: { display: false },
});

// Global default: Libre Franklin for any text a chart draws.
// (Element defaults such as square bars and dot-less lines are set per chart
// in options, since element defaults only exist once registered.)
ChartJS.defaults.font.family = UI_FONT;
