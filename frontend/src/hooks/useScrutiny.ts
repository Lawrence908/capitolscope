import { useCallback, useEffect, useState } from 'react';
import apiClient from '../services/api';
import type {
  ScrutinyResponse,
  ClusterEvent,
  ConflictMember,
  TopConflict,
  DisclosureLag,
} from '../types/scrutiny';

interface State {
  scrutiny?: ScrutinyResponse;
  clusters?: { clusters_found: number; clusters: ClusterEvent[] };
  conflicts?: {
    total_conflict_trades: number;
    members_flagged: number;
    leaderboard: ConflictMember[];
    top_conflicts: TopConflict[];
  };
  lag?: DisclosureLag;
}

type Section = keyof State;

export function useScrutiny() {
  const [data, setData] = useState<State>({});
  const [loading, setLoading] = useState<Partial<Record<Section, boolean>>>({});
  const [error, setError] = useState<string | null>(null);

  const fetchers: Record<Section, () => Promise<any>> = {
    scrutiny: () => apiClient.getScrutinyScores(10, 200),
    clusters: () => apiClient.getClusters({ limit: 80 }),
    conflicts: () => apiClient.getConflicts(3, 80),
    lag: () => apiClient.getDisclosureLag(),
  };

  const load = useCallback(async (section: Section) => {
    setLoading((l) => ({ ...l, [section]: true }));
    setError(null);
    try {
      const result = await fetchers[section]();
      setData((d) => ({ ...d, [section]: result }));
    } catch (e: any) {
      setError(e?.response?.data?.error?.message || e?.message || 'Failed to load analytics');
    } finally {
      setLoading((l) => ({ ...l, [section]: false }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Scrutiny is the landing view; load it up front.
  useEffect(() => {
    load('scrutiny');
  }, [load]);

  return { data, loading, error, load };
}
