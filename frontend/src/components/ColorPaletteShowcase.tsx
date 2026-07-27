import React, { useState } from 'react';
import DarkModeToggle from './DarkModeToggle';
import {
  Eyebrow,
  PageHeader,
  Panel,
  StatTile,
  Tabs,
  Spinner,
  PartyTag,
  Meter,
  FactorBar,
  FACTOR_COLORS,
  FACTOR_LABELS,
  FACTOR_ORDER,
  partyMeta,
} from './ui';

/** Living style guide for the "Scrutiny" design system. Everything here is
 *  driven by the real token classes and palette constants, so it stays honest
 *  and is theme-aware — toggle light/dark with the switch in the corner. */

const TokenSwatch: React.FC<{ box: string; name: string; note?: string }> = ({ box, name, note }) => (
  <div className="space-y-2">
    <div className={`h-16 rounded-md border border-line ${box}`} />
    <p className="font-data text-xs text-content">{name}</p>
    {note && <p className="font-ui text-[11px] text-content-faint">{note}</p>}
  </div>
);

const HexSwatch: React.FC<{ hex: string; name: string; note?: string }> = ({ hex, name, note }) => (
  <div className="space-y-2">
    <div className="h-16 rounded-md border border-line" style={{ background: hex }} />
    <p className="font-data text-xs text-content">{name}</p>
    <p className="font-data text-[11px] uppercase text-content-faint">{hex}</p>
    {note && <p className="font-ui text-[11px] text-content-faint">{note}</p>}
  </div>
);

const Section: React.FC<{ title: React.ReactNode; children: React.ReactNode }> = ({ title, children }) => (
  <div className="mb-8">
    <Panel title={title}>
      <div className="p-5">{children}</div>
    </Panel>
  </div>
);

const SEV = [
  { hex: '#7aa8d6', name: 'sev.info', note: 'steel — cluster / info' },
  { hex: '#d6a24e', name: 'sev.watch', note: 'amber — watch / exchange' },
  { hex: '#d6707b', name: 'sev.flag', note: 'oxblood — flag / sell' },
];

const ColorPaletteShowcase: React.FC = () => {
  const [tab, setTab] = useState<'a' | 'b' | 'c'>('a');

  return (
    <div className="min-h-screen bg-surface font-ui text-content">
      <div className="pointer-events-none fixed inset-x-0 top-0 h-64" style={{ background: 'radial-gradient(120% 60% at 50% 0%, rgba(67,168,151,0.08), transparent 70%)' }} />
      <div className="relative mx-auto max-w-[1200px] px-6 py-10">
        <div className="mb-2 flex justify-end">
          <DarkModeToggle />
        </div>

        <PageHeader
          eyebrow="CapitolScope · Design System"
          title="Style Guide"
          subtitle="The Scrutiny oversight-dossier language: semantic tokens themed for light and dark, domain color-coding, typography, and the shared component primitives. Everything below is live — toggle the theme to see both."
        />

        {/* Semantic surfaces */}
        <Section title="Surfaces & lines">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <TokenSwatch box="bg-surface" name="surface" note="page background" />
            <TokenSwatch box="bg-surface-raised" name="surface-raised" note="cards / panels" />
            <TokenSwatch box="bg-surface-inset" name="surface-inset" note="bar tracks / stripes" />
            <TokenSwatch box="bg-surface border-2 border-line" name="line" note="borders / dividers" />
          </div>
        </Section>

        {/* Text tokens */}
        <Section title="Text">
          <div className="space-y-3">
            <p className="font-ui text-2xl text-content">content — primary text &amp; headings</p>
            <p className="font-ui text-lg text-content-muted">content-muted — body copy</p>
            <p className="font-ui text-sm text-content-faint">content-faint — labels, captions, metadata</p>
          </div>
        </Section>

        {/* Accent */}
        <Section title="Accent (verdigris)">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <TokenSwatch box="bg-accent" name="accent" note="#1f9e88 light / #43a897 dark" />
            <TokenSwatch box="bg-accent-strong" name="accent-strong" note="hover" />
            <TokenSwatch box="bg-accent-2" name="accent-2" note="brass — secondary accent" />
            <div className="space-y-2">
              <div className="flex h-16 items-center justify-center rounded-md bg-accent">
                <span className="font-ui text-sm font-semibold text-[#071310]">Aa buttons</span>
              </div>
              <p className="font-data text-xs text-content">on-accent ink</p>
              <p className="font-ui text-[11px] text-content-faint">#071310</p>
            </div>
          </div>
        </Section>

        {/* Party */}
        <Section title="Party color-coding">
          <div className="flex flex-wrap items-center gap-6">
            {['Democratic', 'Republican', 'Independent'].map((p) => (
              <div key={p} className="flex items-center gap-3">
                <PartyTag party={p} />
                <div className="h-8 w-8 rounded-md border border-line" style={{ background: partyMeta(p).color }} />
                <span className="font-ui text-sm text-content-muted">{p}</span>
              </div>
            ))}
          </div>
        </Section>

        {/* Factor fingerprint */}
        <Section title="Scrutiny factors">
          <div className="mb-4 max-w-md">
            <FactorBar contributions={{ edge: 28, event: 14, conflict: 20, cluster: 12, lag: 16, size: 10 }} height={12} />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {FACTOR_ORDER.map((k) => (
              <div key={k} className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-sm" style={{ background: FACTOR_COLORS[k] }} />
                <span className="font-data text-xs text-content-muted">{FACTOR_LABELS[k]}</span>
              </div>
            ))}
          </div>
        </Section>

        {/* Severity */}
        <Section title="Severity">
          <div className="grid grid-cols-3 gap-4">
            {SEV.map((s) => (
              <HexSwatch key={s.name} hex={s.hex} name={s.name} note={s.note} />
            ))}
          </div>
        </Section>

        {/* Typography */}
        <Section title="Typography">
          <div className="space-y-4">
            <div>
              <Eyebrow>font-display · Newsreader serif</Eyebrow>
              <p className="mt-1 font-display text-4xl font-medium text-content">Congressional Oversight</p>
            </div>
            <div>
              <Eyebrow>font-ui · Public Sans</Eyebrow>
              <p className="mt-1 font-ui text-lg text-content-muted">The quick brown fox jumps over the lazy dog.</p>
            </div>
            <div>
              <Eyebrow>font-data · IBM Plex Mono</Eyebrow>
              <p className="mt-1 font-data text-lg tabular-nums text-content">$1,234,567 · 42.7% · +18.3</p>
            </div>
          </div>
        </Section>

        {/* Components */}
        <Section title="Buttons">
          <div className="flex flex-wrap gap-3">
            <button className="btn-primary">Primary</button>
            <button className="btn-secondary">Secondary</button>
            <button className="btn-outline">Outline</button>
            <button className="btn-ghost">Ghost</button>
          </div>
        </Section>

        <Section title="Inputs">
          <div className="grid max-w-lg gap-3">
            <input className="input-field" placeholder="Text input…" />
            <select className="input-field">
              <option>Select option</option>
            </select>
          </div>
        </Section>

        <Section title="Stat tiles">
          <div className="flex flex-wrap gap-8">
            <StatTile label="Total Trades" value="56,205" />
            <StatTile label="Highest Score" value="87.4" tone="brass" />
            <StatTile label="Members Flagged" value="23" tone="flag" />
            <StatTile label="Avg Alpha 30d" value="+4.2%" tone="accent" />
          </div>
        </Section>

        <Section title="Tabs">
          <Tabs
            items={[
              { id: 'a', label: 'Leaderboard' },
              { id: 'b', label: 'Clusters' },
              { id: 'c', label: 'Conflicts' },
            ]}
            active={tab}
            onChange={setTab}
          />
        </Section>

        <Section title="Meters">
          <div className="max-w-md space-y-3">
            <Meter value={0.85} />
            <Meter value={0.55} color={partyMeta('R').color} />
            <Meter value={0.3} color={FACTOR_COLORS.lag} />
          </div>
        </Section>

        <Section title="Spinner">
          <Spinner label="Computing signals" className="h-32" />
        </Section>

        <footer className="mt-8 border-t border-line pt-4">
          <p className="font-data text-[10px] leading-relaxed text-content-faint">
            One system, two themes. Use the semantic tokens (bg-surface, text-content, border-line,
            text-accent) and the shared components in <span className="text-content">components/ui</span> for
            any new UI — never raw palette colors.
          </p>
        </footer>
      </div>
    </div>
  );
};

export default ColorPaletteShowcase;
