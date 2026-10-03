import { afterEach, describe, expect, it, vi } from 'vitest';
import { displaySize, listingQuery } from './api';

describe('listingQuery', () => {
	it('is empty for a default listing', () => {
		expect(listingQuery({}).toString()).toBe('');
	});

	it('carries order, scope, filters and the NSFW switch', () => {
		const q = listingQuery({
			sort: 'date_created',
			dir: 'desc',
			collection_id: 4,
			show_nsfw: true,
			filters: {
				date_from: '2024-01-01',
				date_to: '2024-01-31',
				aspect_ratio: 'portrait',
				media_type: 'video',
				tags: ['a b', 'c']
			}
		});
		expect(Object.fromEntries(q)).toEqual({
			sort: 'date_created',
			dir: 'desc',
			collection_id: '4',
			show_nsfw: 'true',
			date_from: '2024-01-01',
			date_to: '2024-01-31',
			aspect_ratio_filter: 'portrait',
			media_type: 'video',
			tags: 'c'
		});
		expect(q.getAll('tags')).toEqual(['a b', 'c']);
	});

	it('omits what is unset', () => {
		const q = listingQuery({ source_id: 2, filters: { tags: [] } });
		expect(q.toString()).toBe('source_id=2');
	});
});

describe('displaySize', () => {
	afterEach(() => vi.unstubAllGlobals());

	function screen(w: number, h: number, dpr: number) {
		vi.stubGlobal('innerWidth', w);
		vi.stubGlobal('innerHeight', h);
		vi.stubGlobal('devicePixelRatio', dpr);
	}

	it('asks for the long edge in device pixels, dpr capped at 2', () => {
		screen(390, 844, 3);
		expect(displaySize()).toBe(1688);
	});

	it('never asks for more than the largest preview (GEN-004)', () => {
		screen(1512, 982, 2);
		expect(displaySize()).toBe(2560);
	});
});
