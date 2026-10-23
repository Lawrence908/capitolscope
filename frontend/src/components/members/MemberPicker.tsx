import React, { useEffect, useState } from 'react';
import { apiClient } from '../../services/api';
import type { CongressMember } from '../../types';
import { PartyTag } from '../ui/primitives';
import { affiliation, partyMeta } from '../ui/format';

/**
 * Debounced congress-member search + add control. Shared by the Mirror builder
 * and the member Compare page.
 */
export const MemberPicker: React.FC<{
  onAdd: (m: CongressMember) => void;
  excludeIds: Set<string>;
  placeholder?: string;
}> = ({ onAdd, excludeIds, placeholder = 'Search members to add' }) => {
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
        aria-label={placeholder}
        className="input-field py-2 text-sm"
      />
      {searching && (
        <div className="mt-2 font-ui text-xs font-semibold text-content-faint">Searching</div>
      )}
      {results.length > 0 && (
        <ul className="mt-2 border-t-[3px] border-content">
          {results.map((m) => {
            const already = excludeIds.has(m.id);
            const known = partyMeta(m.party).label !== '?';
            return (
              <li key={m.id} className="flex items-center justify-between gap-2 border-b border-line py-2">
                <span className="flex min-w-0 items-center gap-2">
                  {known && <PartyTag party={m.party} />}
                  <span className="truncate font-ui text-sm font-semibold text-content">{m.full_name}</span>
                  <span className="shrink-0 font-ui text-xs text-content-faint">{affiliation(m.party, m.state)}</span>
                </span>
                <button
                  type="button"
                  disabled={already}
                  onClick={() => onAdd(m)}
                  className="shrink-0 border-2 border-content px-2.5 py-0.5 font-ui text-xs font-bold text-content hover:bg-content hover:text-surface disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-content"
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
  <span className="inline-flex items-center gap-1.5 border-2 border-content bg-surface px-2 py-0.5">
    {partyMeta(party).label !== '?' && <PartyTag party={party} />}
    <span className="font-ui text-xs font-semibold text-content">{label}</span>
    {onRemove && (
      <button
        type="button"
        onClick={onRemove}
        className="font-ui text-xs font-bold text-content-faint hover:text-accent"
        title="Remove member"
        aria-label={`Remove ${label}`}
      >
        ✕
      </button>
    )}
  </span>
);
