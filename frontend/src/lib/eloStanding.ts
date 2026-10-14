import type { EloStanding } from './types';

/** 1st, 2nd, 3rd, 4th … 11th, 12th, 13th … 21st. */
export function ordinal(n: number): string {
	const teen = n % 100 >= 11 && n % 100 <= 13;
	const suffix = teen ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th';
	return `${n}${suffix}`;
}

/** "12th of 954". */
export function rankText(s: EloStanding): string {
	return `${ordinal(s.rank)} of ${s.ranked}`;
}

/** The standing in the collection being browsed, if any, apart from the rest. */
export function splitStandings(
	standings: EloStanding[],
	collectionId: number | undefined
): { current: EloStanding | null; others: EloStanding[] } {
	const current = standings.find((s) => s.collection_id === collectionId) ?? null;
	return { current, others: standings.filter((s) => s !== current) };
}
