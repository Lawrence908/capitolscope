import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useScrutiny } from '../../hooks/useScrutiny';
import type { ScrutinyMember } from '../../types/scrutiny';
import { Leaderboard, LegendRow } from '../../components/scrutiny/Leaderboard';
import { MemberDossier } from '../../components/scrutiny/MemberDossier';
import { ClusterFeed, ConflictsView, LagView } from '../../components/scrutiny/SignalViews';
import { Eyebrow } from '../../components/scrutiny/primitives';

type Tab = 'leaderboard' | 'clusters' | 'conflicts' | 'lag';

const TABS: { id: Tab; label: string; section: 'scrutiny' | 'clusters' | 'conflicts' | 'lag' }[] = [
  { id: 'leaderboard', label: 'Leaderboard', section: 'scrutiny' },
  { id: 'clusters', label: 'Clusters', section: 'clusters' },
  { id: 'conflicts', label: 'Conflicts', section: 'conflicts' },
  { id: 'lag', label: 'Disclosure Lag', section: 'lag' },
];

const Spinner: React.FC<{ label?: string }> = ({ label = 'Computing signals' }) => (
  <div className="flex h-72 flex-col items-center justify-center gap-4">
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-ink-600 border-t-verdigris-500" />
    <span className="font-data text-[11px] uppercase tracking-[0.2em] text-fog-500">{label}</span>
  </div>
);

const ScrutinyCommand: React.FC = () => {
  const { data, loading, error, load } = useScrutiny();
  const [tab, setTab] = useState<Tab>('leaderboard');
  const [selected, setSelected] = useState<ScrutinyMember | null>(null);
  const [missingName, setMissingName] = useState<string | null>(null);

  // lazy-load a section the first time its tab is opened
  useEffect(() => {
    const t = TABS.find((x) => x.id === tab)!;
    if (t.section !== 'scrutiny' && !(data as any)[t.section] && !loading[t.section]) {
      load(t.section);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const scores = data.scrutiny?.scores || [];
  useEffect(() => {
    if (!selected && !missingName && scores.length) setSelected(scores[0]);
  }, [scores, selected, missingName]);

  // Deep-link from any signal view into a member's dossier.
  const selectByName = useCallback(
    (name: string) => {
      const match = scores.find((s) => s.member === name);
      if (match) {
        setSelected(match);
        setMissingName(null);
      } else {
        setSelected(null);
        setMissingName(name);
      }
      setTab('leaderboard');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [scores],
  );

  const summary = useMemo(() => {
    const n = data.scrutiny?.members_scored ?? 0;
    const top = scores[0];
    return { n, top };
  }, [data.scrutiny, scores]);

  return (
    <div className="min-h-screen bg-ink-950 font-ui text-fog-300 antialiased">
      {/* grain / atmosphere via subtle top gradient */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-64"
        style={{ background: 'radial-gradient(120% 60% at 50% 0%, rgba(67,168,151,0.08), transparent 70%)' }}
      />

      {/* Masthead */}
      <header className="relative border-b border-ink-600">
        <div className="mx-auto max-w-[1400px] px-6 pb-6 pt-10">
          <Eyebrow>CapitolScope · Congressional Oversight</Eyebrow>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-6">
            <div>
              <h1 className="font-display text-5xl font-500 leading-[0.95] tracking-[-0.01em] text-fog-200">
                Scrutiny
              </h1>
              <p className="mt-3 max-w-[46ch] font-ui text-sm leading-relaxed text-fog-500">
                A single, explainable read on who is worth a closer look. Four signals — trading
                edge, committee conflict, herding, and filing delay — blended and ranked across
                public STOCK Act disclosures. Leads for scrutiny, not verdicts.
              </p>
            </div>
            {summary.top && (
              <div className="flex gap-8 pb-1">
                <div>
                  <div className="font-data text-[10px] uppercase tracking-[0.14em] text-fog-500">
                    Members scored
                  </div>
                  <div className="mt-1 font-data text-3xl font-500 tabular-nums text-fog-200">
                    {summary.n}
                  </div>
                </div>
                <div>
                  <div className="font-data text-[10px] uppercase tracking-[0.14em] text-fog-500">
                    Highest score
                  </div>
                  <div className="mt-1 font-data text-3xl font-500 tabular-nums text-brass-500">
                    {summary.top.scrutiny_score.toFixed(1)}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Tabs */}
          <nav className="mt-8 flex gap-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`font-data text-xs uppercase tracking-[0.12em] px-4 py-2 rounded-t-md border-b-2 transition-colors ${
                  tab === t.id
                    ? 'border-verdigris-500 text-fog-200 bg-ink-900'
                    : 'border-transparent text-fog-500 hover:text-fog-300'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Body */}
      <main className="relative mx-auto max-w-[1400px] px-6 py-6">
        {error && (
          <div className="mb-4 rounded-md border border-sev-flag/40 bg-[#331a1e] px-4 py-3 font-ui text-sm text-sev-flag">
            {error}
          </div>
        )}

        {tab === 'leaderboard' &&
          (loading.scrutiny && !scores.length ? (
            <Spinner />
          ) : (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.35fr_1fr]">
              <section className="overflow-hidden rounded-md border border-ink-600 bg-ink-900">
                <LegendRow />
                <div className="max-h-[72vh] overflow-y-auto">
                  <Leaderboard
                    members={scores}
                    selected={selected?.member}
                    onSelect={(m) => {
                      setSelected(m);
                      setMissingName(null);
                    }}
                  />
                </div>
              </section>
              <aside className="lg:sticky lg:top-6 h-fit rounded-md border border-ink-600 bg-ink-900 lg:min-h-[60vh]">
                <MemberDossier member={selected} missingName={missingName} />
              </aside>
            </div>
          ))}

        {tab === 'clusters' &&
          (loading.clusters || !data.clusters ? (
            <Spinner label="Detecting herds" />
          ) : (
            <section className="overflow-hidden rounded-md border border-ink-600 bg-ink-900">
              <div className="flex items-center justify-between border-b border-ink-600 px-4 py-3">
                <Eyebrow>{data.clusters.clusters_found} cluster events · ranked by notability</Eyebrow>
                <span className="font-ui text-[11px] text-fog-500">
                  N members trading the same ticker &amp; side within 14 days
                </span>
              </div>
              <ClusterFeed clusters={data.clusters.clusters} onSelectMember={selectByName} />
            </section>
          ))}

        {tab === 'conflicts' &&
          (loading.conflicts || !data.conflicts ? (
            <Spinner label="Mapping committees" />
          ) : (
            <section className="overflow-hidden rounded-md border border-ink-600 bg-ink-900">
              <div className="border-b border-ink-600 px-4 py-3">
                <Eyebrow>
                  {data.conflicts.total_conflict_trades.toLocaleString()} conflict trades ·{' '}
                  {data.conflicts.members_flagged} members
                </Eyebrow>
              </div>
              <ConflictsView
                leaderboard={data.conflicts.leaderboard}
                topConflicts={data.conflicts.top_conflicts}
                onSelectMember={selectByName}
              />
            </section>
          ))}

        {tab === 'lag' &&
          (loading.lag || !data.lag ? (
            <Spinner label="Reading the clock" />
          ) : (
            <section className="overflow-hidden rounded-md border border-ink-600 bg-ink-900">
              <LagView lag={data.lag} onSelectMember={selectByName} />
            </section>
          ))}
      </main>

      <footer className="mx-auto max-w-[1400px] px-6 pb-10 pt-4">
        <p className="font-data text-[10px] leading-relaxed text-fog-500">
          Built on public STOCK Act disclosures. Amounts are disclosed-range midpoints. Scores are
          percentile-ranked prioritisation aids, not accusations.
        </p>
      </footer>
    </div>
  );
};

export default ScrutinyCommand;
