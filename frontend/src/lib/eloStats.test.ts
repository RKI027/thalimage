import { describe, expect, it } from 'vitest';
import { balancedBand, gini, headToHead, lorenz, matchCounts, showsImage } from './eloStats';
import type { CoveredImage } from './types';

describe('gini', () => {
	it('is 0 when every image has played as often', () => {
		expect(gini([3, 3, 3])).toBe(0);
	});

	it('grows as a few images take the matches', () => {
		expect(gini([0, 0, 0, 4])).toBeCloseTo(0.75);
		expect(gini([1, 2, 3])).toBeCloseTo(2 / 9);
	});

	it('is 0 with no matches at all, or no images', () => {
		expect(gini([0, 0])).toBe(0);
		expect(gini([])).toBe(0);
	});
});

describe('lorenz', () => {
	it('runs from the least-played images up, as cumulative shares', () => {
		expect(lorenz([3, 0, 1])).toEqual([
			{ images: 0, matches: 0 },
			{ images: 1 / 3, matches: 0 },
			{ images: 2 / 3, matches: 0.25 },
			{ images: 1, matches: 1 }
		]);
	});

	it('follows the diagonal with no matches', () => {
		expect(lorenz([0, 0]).map((p) => p.matches)).toEqual([0, 0.5, 1]);
	});
});

describe('balancedBand', () => {
	it('spans the whole numbers around the average', () => {
		expect(balancedBand([1, 2, 4])).toEqual({ mean: 7 / 3, low: 2, high: 3 });
		expect(balancedBand([2, 2])).toEqual({ mean: 2, low: 2, high: 2 });
	});
});

describe('matchCounts', () => {
	it('counts images per number of matches, gaps included', () => {
		expect(matchCounts([0, 2, 2, 3])).toEqual([
			{ matches: 0, images: 1 },
			{ matches: 1, images: 0 },
			{ matches: 2, images: 2 },
			{ matches: 3, images: 1 }
		]);
	});
});

describe('headToHead', () => {
	it("gives every ordered pair of the top the row's record against the column", () => {
		const cells = headToHead(['a', 'b', 'c'], [
			{ winner: 'a', loser: 'b', count: 2 },
			{ winner: 'b', loser: 'a', count: 1 }
		]);
		expect(cells).toHaveLength(6);
		expect(cells.find((c) => c.row === 'a' && c.col === 'b')).toEqual({ row: 'a', col: 'b', wins: 2, losses: 1 });
		expect(cells.find((c) => c.row === 'b' && c.col === 'a')).toEqual({ row: 'b', col: 'a', wins: 1, losses: 2 });
		expect(cells.find((c) => c.row === 'a' && c.col === 'c')).toEqual({ row: 'a', col: 'c', wins: 0, losses: 0 });
	});
});

describe('showsImage', () => {
	const image = (nsfw: boolean) => ({ nsfw }) as CoveredImage;

	it('shows a safe image always, an NSFW one only while NSFW is shown', () => {
		expect(showsImage(image(false), false)).toBe(true);
		expect(showsImage(image(true), false)).toBe(false);
		expect(showsImage(image(true), true)).toBe(true);
	});
});
