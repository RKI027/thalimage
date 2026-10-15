import { describe, expect, it } from 'vitest';
import { createSlidePreloader } from './slidePreloader';

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
