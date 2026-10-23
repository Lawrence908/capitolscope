import React from 'react';
import { Link } from 'react-router-dom';

/* ------------------------------------------------------------------ *
 * Bulletin auth chrome shared by login, register, forgot and reset:
 * a centered ink-ruled panel with the condensed wordmark on a slab,
 * a condensed headline, square inputs and the red primary button.
 * ------------------------------------------------------------------ */

/** Centered auth panel: slab wordmark band, condensed headline, form body. */
export const AuthShell: React.FC<{
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Small print under the panel (beta notes, help text). */
  note?: React.ReactNode;
  children?: React.ReactNode;
}> = ({ eyebrow, title, subtitle, note, children }) => (
  <div className="flex min-h-screen items-center justify-center bg-surface px-4 py-12 sm:px-6">
    <div className="w-full max-w-md">
      <div className="border-2 border-content bg-surface-raised">
        <div className="flex items-center justify-between gap-4 bg-slab px-6 py-4">
          <Link to="/" className="flex shrink-0 items-center gap-2.5" aria-label="CapitolScope home">
            <span aria-hidden="true" className="block h-9 w-1.5 bg-accent" />
            <span className="font-display text-[21px] font-extrabold leading-[0.82] tracking-[0.02em] text-slab-on">
              CAPITOL
              <br />
              SCOPE
            </span>
          </Link>
          {eyebrow != null && (
            <span className="font-ui text-[11px] font-bold uppercase tracking-[0.12em] text-slab-muted">
              {eyebrow}
            </span>
          )}
        </div>
        <div className="px-6 pb-6 pt-6 sm:px-8 sm:pb-8">
          <h1 className="font-display text-5xl font-extrabold leading-[0.9] text-content">{title}</h1>
          {subtitle != null && <p className="mt-3 font-ui text-sm text-content-muted">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </div>
      {note}
    </div>
  </div>
);

/** Inline status message: errors get the red rule, success the ink rule. */
export const AuthAlert: React.FC<{ tone: 'error' | 'success'; children: React.ReactNode }> = ({
  tone,
  children,
}) => (
  <div
    role={tone === 'error' ? 'alert' : 'status'}
    className={`border-l-4 bg-surface-inset px-4 py-3 font-ui text-sm text-content ${
      tone === 'error' ? 'border-accent' : 'border-content'
    }`}
  >
    {children}
  </div>
);

/** Small print block under the auth panel. */
export const AuthNote: React.FC<{ title: React.ReactNode; children: React.ReactNode }> = ({
  title,
  children,
}) => (
  <div className="mt-6 border-t-[3px] border-content pt-3">
    <h3 className="mb-1 font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content">{title}</h3>
    <div className="font-ui text-xs leading-relaxed text-content-faint">{children}</div>
  </div>
);

/** Small spinner for inside the red primary button. */
export const ButtonSpinner: React.FC = () => (
  <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-accent-on border-t-transparent" />
);
