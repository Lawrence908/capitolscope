import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useScrutiny } from '../../hooks/useScrutiny';
import type { ScrutinyMember } from '../../types/scrutiny';
import { Leaderboard, LegendRow } from '../../components/scrutiny/Leaderboard';
import { MemberDossier } from '../../components/scrutiny/MemberDossier';
import { ClusterFeed, ConflictsView, LagView } from '../../components/scrutiny/SignalViews';
import { Eyebrow, PageHeader, Tabs, Spinner } from '../../components/ui';
import { TickerDrawer } from '../../components/scrutiny/TickerDrawer';
import type { DossierOrigin } from '../../types/scrutiny';

type Tab = 'leaderboard' | 'clusters' | 'conflicts' | 'lag';
type Section = 'scrutiny' | 'clusters' | 'conflicts' | 'lag';

const TABS: { id: Tab; label: string; section: Section }[] = [
  { id: 'leaderboard', label: 'Leaderboard', section: 'scrutiny' },
  { id: 'clusters', label: 'Clusters', section: 'clusters' },
  { id: 'conflicts', label: 'Conflicts', section: 'conflicts' },
  { id: 'lag', label: 'Disclosure Lag', section: 'lag' },
];

const ScrutinyCommand: React.FC = () => {
  const { data, loading, error, load } = useScrutiny();
  const [tab, setTab] = useState<Tab>('leaderboard');
  const [selected, setSelected] = useState<ScrutinyMember | null>(null);
  const [missingName, setMissingName] = useState<string | null>(null);
  const [origin, setOrigin] = useState<DossierOrigin | null>(null);
  const [openTicker, setOpenTicker] = useState<string | null>(null);

  // lazy-load a section the first time its tab is opened
  useEffect(() => {
    const t = TABS.find((x) => x.id === tab)!;
    if (t.section !== 'scrutiny' && !data[t.section] && !loading[t.section]) {
      load(t.section);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  const scores = useMemo(() => data.scrutiny?.scores || [], [data.scrutiny]);
  useEffect(() => {
    if (!selected && !missingName && scores.length) setSelected(scores[0]);
  }, [scores, selected, missingName]);

  // Deep-link from any signal view into a member's dossier.
  const selectByName = useCallback(
    (name: string, from?: DossierOrigin) => {
      const match = scores.find((s) => s.member === name);
      if (match) {
        setSelected(match);
        setMissingName(null);
      } else {
        setSelected(null);
        setMissingName(name);
      }
      setOrigin(from ?? null);
      setTab('leaderboard');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [scores],
  );

  const goBack = useCallback(() => {
    if (origin) setTab(origin.tab);
    setOrigin(null);
  }, [origin]);

  const summary = useMemo(() => {
    const n = data.scrutiny?.members_scored ?? 0;
    const top = scores[0];
    return { n, top };
  }, [data.scrutiny, scores]);

  return (
    <div>
      <PageHeader
        eyebrow="Composite Signal"
        title="Scrutiny"
        subtitle="A single, explainable read on who is worth a closer look. Four signals — trading edge, committee conflict, herding, and filing delay — blended and ranked across public STOCK Act disclosures. Leads for scrutiny, not verdicts."
        stats={
          summary.top
            ? [
                { label: 'Members scored', value: summary.n },
                { label: 'Highest score', value: summary.top.scrutiny_score.toFixed(1), tone: 'brass' },
              ]
            : undefined
        }
      >
        <Tabs
          className="mt-8"
          items={TABS.map((t) => ({ id: t.id, label: t.label }))}
          active={tab}
          onChange={setTab}
        />
      </PageHeader>

      {error && (
        <div className="mb-4 rounded-md border border-sev-flag/40 px-4 py-3 font-ui text-sm status-error">
          {error}
        </div>
      )}

      {tab === 'leaderboard' &&
        (loading.scrutiny && !scores.length ? (
          <Spinner label="Computing signals" />
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.35fr_1fr]">
            <section className="overflow-hidden rounded-md border border-line bg-surface-raised">
              <LegendRow />
              <div className="max-h-[72vh] overflow-y-auto">
                <Leaderboard
                  members={scores}
                  selected={selected?.member}
                  onSelect={(m) => {
                    setSelected(m);
                    setMissingName(null);
                    setOrigin(null);
                  }}
                />
              </div>
            </section>
            <aside className="h-fit rounded-md border border-line bg-surface-raised lg:sticky lg:top-6 lg:min-h-[60vh]">
              <MemberDossier
                member={selected}
                missingName={missingName}
                origin={origin}
                onBack={goBack}
              />
            </aside>
          </div>
        ))}

      {tab === 'clusters' &&
        (loading.clusters || !data.clusters ? (
          <Spinner label="Detecting herds" />
        ) : (
          <section className="overflow-hidden rounded-md border border-line bg-surface-raised">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <Eyebrow>{data.clusters.clusters_found} cluster events · ranked by notability</Eyebrow>
              <span className="font-ui text-[11px] text-content-faint">
                N members trading the same ticker &amp; side within 14 days
              </span>
            </div>
            <ClusterFeed
              clusters={data.clusters.clusters}
              onSelectMember={selectByName}
              onSelectTicker={setOpenTicker}
            />
          </section>
        ))}

      {tab === 'conflicts' &&
        (loading.conflicts || !data.conflicts ? (
          <Spinner label="Mapping committees" />
        ) : (
          <section className="overflow-hidden rounded-md border border-line bg-surface-raised">
            <div className="border-b border-line px-4 py-3">
              <Eyebrow>
                {data.conflicts.total_conflict_trades.toLocaleString()} conflict trades ·{' '}
                {data.conflicts.members_flagged} members
              </Eyebrow>
            </div>
            <ConflictsView
              leaderboard={data.conflicts.leaderboard}
              topConflicts={data.conflicts.top_conflicts}
              onSelectMember={selectByName}
              onSelectTicker={setOpenTicker}
            />
          </section>
        ))}

      {tab === 'lag' &&
        (loading.lag || !data.lag ? (
          <Spinner label="Reading the clock" />
        ) : (
          <section className="overflow-hidden rounded-md border border-line bg-surface-raised">
            <LagView lag={data.lag} onSelectMember={selectByName} />
          </section>
        ))}

      <TickerDrawer
        ticker={openTicker}
        onClose={() => setOpenTicker(null)}
        onSelectMember={(name) => {
          setOpenTicker(null);
          selectByName(name);
        }}
      />

      <p className="mt-8 border-t border-line pt-4 font-data text-[10px] leading-relaxed text-content-faint">
        Built on public STOCK Act disclosures. Amounts are disclosed-range midpoints. Scores are
        percentile-ranked prioritisation aids, not accusations.
      </p>
    </div>
  );
};

export default ScrutinyCommand;
