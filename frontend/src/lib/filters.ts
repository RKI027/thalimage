import type { FilterState } from './types';

/** How many filters are set; the ELO cut's end and percentage count as one. */
export function activeFilterCount(filters: FilterState): number {
	return Object.keys(filters).filter((k) => k !== 'elo_end').length;
}

/** `filters` with `patch` applied. A filter patched to undefined or an empty
 * string is unset, and removed so it no longer counts as set. */
export function withFilters(filters: FilterState, patch: Partial<FilterState>): FilterState {
	const next: Record<string, unknown> = { ...filters, ...patch };
	for (const k of Object.keys(next)) {
		if (next[k] === undefined || next[k] === '') delete next[k];
	}
	return next as FilterState;
}
