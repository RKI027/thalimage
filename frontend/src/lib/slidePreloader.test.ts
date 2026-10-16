import { describe, expect, it } from 'vitest';
import { createSlidePreloader, neighborsToPreload } from './slidePreloader';

const slide = (hash: string, filename = `${hash}.png`) => ({ content_hash: hash, filename, score: null });

describe('createSlidePreloader', () => {
	it('loads each slide kept once, skipping videos', () => {
		const loaded: string[] = [];
		const keep = createSlidePreloader((h) => loaded.push(h));
		keep([slide('a'), slide('b'), slide('v', 'v.mp4')]);
		keep([slide('b'), slide('c')]);
		expect(loaded).toEqual(['a', 'b', 'c']);
	});

	it('loads again a slide it let go of', () => {
		const loaded: string[] = [];
		const keep = createSlidePreloader((h) => loaded.push(h));
		keep([slide('a')]);
		keep([slide('b')]);
		keep([slide('a')]);
		expect(loaded).toEqual(['a', 'b', 'a']);
	});
});

describe('neighborsToPreload', () => {
	const listing = ['a', 'b', 'c', 'd', 'e'];

	it('holds only the next image while the one shown loads', () => {
		expect(neighborsToPreload(listing, 2, false)).toEqual(['d']);
	});

	it('adds the one after and the previous once the image shown has loaded', () => {
		expect(neighborsToPreload(listing, 2, true)).toEqual(['d', 'e', 'b']);
	});

	it('skips the neighbours past either end of the listing', () => {
		expect(neighborsToPreload(listing, 0, true)).toEqual(['b', 'c']);
		expect(neighborsToPreload(listing, 4, true)).toEqual(['d']);
	});

	it('holds nothing off the listing', () => {
		expect(neighborsToPreload(listing, -1, true)).toEqual([]);
	});
});
