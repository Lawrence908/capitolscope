/* ------------------------------------------------------------------ *
 * Member display helpers shared by the member directory and profile:
 * state names, role lines ("Senator, Alabama" / "Representative, NJ-5"),
 * committee short names and date formatting. Non-component exports only.
 * ------------------------------------------------------------------ */

export const STATE_NAMES: Record<string, string> = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California', CO: 'Colorado',
  CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia', HI: 'Hawaii', ID: 'Idaho',
  IL: 'Illinois', IN: 'Indiana', IA: 'Iowa', KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana',
  ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota',
  MS: 'Mississippi', MO: 'Missouri', MT: 'Montana', NE: 'Nebraska', NV: 'Nevada',
  NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico', NY: 'New York', NC: 'North Carolina',
  ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania',
  RI: 'Rhode Island', SC: 'South Carolina', SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas',
  UT: 'Utah', VT: 'Vermont', VA: 'Virginia', WA: 'Washington', WV: 'West Virginia',
  WI: 'Wisconsin', WY: 'Wyoming', DC: 'District of Columbia', PR: 'Puerto Rico', GU: 'Guam',
  VI: 'U.S. Virgin Islands', AS: 'American Samoa', MP: 'Northern Mariana Islands',
};

const TERRITORIES = new Set(['DC', 'PR', 'GU', 'VI', 'AS', 'MP']);

export const stateName = (code: string | null | undefined): string =>
  (code && STATE_NAMES[code.toUpperCase()]) || code || '';

export const isSenate = (chamber: string | null | undefined): boolean =>
  (chamber || '').toLowerCase().startsWith('s');
export const isHouse = (chamber: string | null | undefined): boolean =>
  (chamber || '').toLowerCase().startsWith('h');

/** "NJ-5", "WY-AL" (at-large), or just the state code. */
export const districtTag = (state: string | null | undefined, district: string | null | undefined): string => {
  if (!state) return '';
  const d = (district || '').trim();
  if (!d) return state;
  if (d === '0' || d === '00' || /^at[- ]?large$/i.test(d) || d.toUpperCase() === 'AL') return `${state}-AL`;
  return `${state}-${d.replace(/^0+(?=\d)/, '')}`;
};

/** Role line for a member: "Senator, Alabama" / "Representative, NJ-5". */
export const memberRole = (
  chamber: string | null | undefined,
  state: string | null | undefined,
  district: string | null | undefined,
): string => {
  if (isSenate(chamber)) return state ? `Senator, ${stateName(state)}` : 'Senator';
  if (isHouse(chamber)) {
    if (state && TERRITORIES.has(state.toUpperCase())) {
      return `${state.toUpperCase() === 'PR' ? 'Resident Commissioner' : 'Delegate'}, ${stateName(state)}`;
    }
    return state ? `Representative, ${districtTag(state, district)}` : 'Representative';
  }
  return state ? `Member of Congress, ${stateName(state)}` : 'Member of Congress';
};

/** "House Committee on the Budget" -> "Budget"; joint committees keep their name. */
export const shortCommittee = (name: string): string => {
  const m = name.match(/^(?:House|Senate)\s+(?:Permanent\s+Select\s+|Select\s+|Special\s+)?Committee\s+on\s+(?:the\s+)?(.+)$/i);
  if (!m) return name;
  const rest = m[1].trim();
  return rest.charAt(0).toUpperCase() + rest.slice(1);
};

/** ISO date (YYYY-MM-DD...) -> "Oct 6, 2026" without timezone drift. */
export const fmtDate = (iso: string | null | undefined, withYear = true): string => {
  if (!iso) return '';
  const d = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-US', withYear ? { month: 'short', day: 'numeric', year: 'numeric' } : { month: 'short', day: 'numeric' });
};

export const yearOf = (iso: string | null | undefined): string => (iso ? iso.slice(0, 4) : '');

/** Days rounded for display: 40.2 -> "40", null -> null. */
export const roundDays = (n: number | null | undefined): number | null => (n == null ? null : Math.round(n));
