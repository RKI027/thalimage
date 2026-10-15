import type { EloEnd, FilterState } from './types';

/** `filters` with the ELO cut set to the top or bottom `percent`, kept
 * whole and within 1–100; without a usable percentage, with no cut. */
export function withEloCut(filters: FilterState, end: EloEnd, percent: number | undefined): FilterState {
	const { elo_end: _end, elo_percent: _percent, ...rest } = filters;
	if (percent === undefined || Number.isNaN(percent)) return rest;
	return { ...rest, elo_end: end, elo_percent: Math.min(100, Math.max(1, Math.round(percent))) };
}

/** "Top 10%", or null when the filters hold no ELO cut. */
export function eloCutLabel(filters: FilterState): string | null {
	if (!filters.elo_percent) return null;
	return `${filters.elo_end === 'bottom' ? 'Bottom' : 'Top'} ${filters.elo_percent}%`;
}
