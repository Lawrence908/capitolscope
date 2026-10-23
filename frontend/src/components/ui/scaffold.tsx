import React from 'react';
import { Eyebrow } from './primitives';

/* ------------------------------------------------------------------ *
 * Page scaffolding shared across the whole app ("Bulletin"): condensed
 * headline masthead (PageHeader), stat tiles, ruled panels, tab bar, spinner.
 * ------------------------------------------------------------------ */

export type Tone = 'default' | 'accent' | 'brass' | 'flag' | 'steel' | 'coral';

const TONE_TEXT: Record<Tone, string> = {
  default: 'text-content',
  accent: 'text-accent',
  brass: 'text-accent-2',
  flag: 'text-sev-flag',
  steel: 'text-sev-info',
  coral: 'text-sev-watch',
};

// ---- stat tile (mono tabular figure + label) ----
export const StatTile: React.FC<{
  label: React.ReactNode;
  value: React.ReactNode;
  tone?: Tone;
  hint?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}> = ({ label, value, tone = 'default', hint, size = 'md' }) => {
  const figure = size === 'lg' ? 'text-4xl' : size === 'sm' ? 'text-xl' : 'text-3xl';
  return (
    <div>
      <div className="font-ui text-[11px] font-semibold uppercase tracking-[0.08em] text-content-faint">
        {label}
      </div>
      <div className={`mt-1 font-display ${figure} font-extrabold leading-none tabular-nums ${TONE_TEXT[tone]}`}>
        {value}
      </div>
      {hint != null && (
        <div className="mt-0.5 font-ui text-[11px] text-content-faint">{hint}</div>
      )}
    </div>
  );
};

// ---- page masthead (eyebrow + serif title + subtitle + stat rail) ----
export const PageHeader: React.FC<{
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  stats?: { label: React.ReactNode; value: React.ReactNode; tone?: Tone; hint?: React.ReactNode }[];
  actions?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}> = ({ eyebrow, title, subtitle, stats, actions, children, className = '' }) => (
  <header className={`mb-8 border-b-[3px] border-content pb-6 ${className}`}>
    <div className="flex flex-wrap items-end justify-between gap-6">
      <div>
        {eyebrow != null && <Eyebrow>{eyebrow}</Eyebrow>}
        <h1 className="mt-2 font-display text-5xl font-extrabold leading-[0.92] tracking-[-0.005em] text-content sm:text-6xl">
          {title}
        </h1>
        {subtitle != null && (
          <p className="mt-3 max-w-[60ch] font-ui text-[15px] leading-relaxed text-content-muted">
            {subtitle}
          </p>
        )}
      </div>
      {(stats?.length || actions) && (
        <div className="flex flex-wrap items-end gap-6">
          {stats?.map((s, i) => (
            <StatTile key={i} label={s.label} value={s.value} tone={s.tone} hint={s.hint} size="sm" />
          ))}
          {actions}
        </div>
      )}
    </div>
    {children}
  </header>
);

// ---- bordered panel with optional eyebrow header ----
export const Panel: React.FC<{
  title?: React.ReactNode;
  right?: React.ReactNode;
  className?: string;
  bodyClassName?: string;
  children: React.ReactNode;
}> = ({ title, right, className = '', bodyClassName = '', children }) => (
  <section className={`overflow-hidden border-t-[3px] border-content bg-surface-raised ${className}`}>
    {(title != null || right != null) && (
      <div className="flex items-baseline justify-between gap-3 border-b border-line px-1 py-3">
        {title != null ? (
          <h2 className="font-display text-2xl font-extrabold leading-none text-content">{title}</h2>
        ) : (
          <span />
        )}
        {right}
      </div>
    )}
    <div className={bodyClassName}>{children}</div>
  </section>
);

// ---- mono tab bar ----
export const Tabs = <T extends string>({
  items,
  active,
  onChange,
  className = '',
}: {
  items: { id: T; label: React.ReactNode }[];
  active: T;
  onChange: (id: T) => void;
  className?: string;
}): React.ReactElement => (
  <nav className={`flex flex-wrap gap-1 ${className}`}>
    {items.map((t) => (
      <button
        key={t.id}
        type="button"
        onClick={() => onChange(t.id)}
        className={`font-display text-lg font-extrabold uppercase tracking-[0.02em] px-3 py-1.5 border-b-[3px] transition-colors ${
          active === t.id
            ? 'border-accent text-content'
            : 'border-transparent text-content-faint hover:text-content'
        }`}
      >
        {t.label}
      </button>
    ))}
  </nav>
);

// ---- loading spinner ----
export const Spinner: React.FC<{ label?: string; className?: string }> = ({
  label = 'Loading',
  className = '',
}) => (
  <div className={`flex h-72 flex-col items-center justify-center gap-4 ${className}`}>
    <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-line border-t-accent" />
    <span className="font-ui text-[11px] font-semibold uppercase tracking-[0.14em] text-content-faint">
      {label}
    </span>
  </div>
);
