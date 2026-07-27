import React, { useEffect, useState } from 'react';
import { apiClient } from '../../services/api';
import type { CongressMember } from '../../types';
import { PartyTag } from '../ui/primitives';

/**
 * Debounced congress-member search + add control. Shared by the Mirror builder
 * and the member Compare page.
 */
export const MemberPicker: React.FC<{
  onAdd: (m: CongressMember) => void;
  excludeIds: Set<string>;
  placeholder?: string;
}> = ({ onAdd, excludeIds, placeholder = 'Search members to add…' }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CongressMember[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setSearching(true);
    const t = setTimeout(async () => {
      try {
        const res = await apiClient.getMembers({ search: q }, 1, 8);
        if (!cancelled) setResults(res.items);
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setSearching(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query]);

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-line bg-surface px-3 py-2 font-ui text-sm text-content placeholder:text-content-faint focus:border-accent focus:outline-none"
      />
      {searching && (
        <div className="mt-2 font-data text-[11px] uppercase tracking-[0.14em] text-content-faint">
          Searching…
        </div>
      )}
      {results.length > 0 && (
        <ul className="mt-2 divide-y divide-line rounded-md border border-line">
          {results.map((m) => {
            const already = excludeIds.has(m.id);
            return (
              <li key={m.id} className="flex items-center justify-between gap-2 px-3 py-2">
                <span className="flex min-w-0 items-center gap-2">
                  <PartyTag party={m.party} />
                  <span className="truncate font-ui text-sm text-content">{m.full_name}</span>
                  <span className="font-data text-[11px] text-content-faint">{m.state || ''}</span>
                </span>
                <button
                  type="button"
                  disabled={already}
                  onClick={() => onAdd(m)}
                  className="shrink-0 rounded-md border border-line px-2 py-1 font-data text-[11px] uppercase tracking-[0.12em] text-content hover:border-accent hover:text-accent disabled:opacity-40"
                >
                  {already ? 'Added' : 'Add'}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export const MemberChip: React.FC<{
  label: string;
  party?: string | null;
  onRemove?: () => void;
}> = ({ label, party, onRemove }) => (
  <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1">
    <PartyTag party={party} />
    <span className="font-ui text-xs text-content">{label}</span>
    {onRemove && (
      <button
        type="button"
        onClick={onRemove}
        className="font-data text-xs text-content-faint hover:text-sev-flag"
        title="Remove member"
      >
        ✕
      </button>
    )}
  </span>
);
