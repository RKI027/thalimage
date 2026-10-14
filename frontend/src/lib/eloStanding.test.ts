import { describe, expect, it } from 'vitest';
import { ordinal, rankText, splitStandings } from './eloStanding';
import type { EloStanding } from './types';

const standing = (collection_id: number, rank = 1, ranked = 10): EloStanding => ({
	collection_id,
	collection_name: `c${collection_id}`,
	score: 1500,
	rank,
	ranked,
	matches: 0,
	wins: 0,
	losses: 0
});

describe('ordinal', () => {
	it.each([
		[1, '1st'], [2, '2nd'], [3, '3rd'], [4, '4th'], [11, '11th'], [12, '12th'], [13, '13th'],
		[21, '21st'], [22, '22nd'], [103, '103rd'], [111, '111th'], [954, '954th']
	])('%i is %s', (n, text) => {
		expect(ordinal(n)).toBe(text);
	});
});

describe('rankText', () => {
	it('places the image among the ranked ones', () => {
		expect(rankText(standing(1, 12, 954))).toBe('12th of 954');
	});
});

describe('splitStandings', () => {
	const all = [standing(1), standing(2), standing(3)];

	it('separates the collection being browsed from the others', () => {
		expect(splitStandings(all, 2)).toEqual({ current: all[1], others: [all[0], all[2]] });
	});

	it('has no current standing outside a collection, or in one never voted in', () => {
		expect(splitStandings(all, undefined)).toEqual({ current: null, others: all });
		expect(splitStandings(all, 9)).toEqual({ current: null, others: all });
	});
});
