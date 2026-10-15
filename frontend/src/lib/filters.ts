import type { FilterState } from './types';

/** How many filters are set; the ELO cut's end and percentage count as one. */
export function activeFilterCount(filters: FilterState): number {
	return Object.keys(filters).filter((k) => k !== 'elo_end').length;
}
