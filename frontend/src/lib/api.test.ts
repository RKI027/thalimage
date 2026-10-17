import { afterEach, describe, expect, it, vi } from 'vitest';
import {
	decidePossibleEdit,
	deleteSource,
	displaySize,
	getEloPair,
	getEloRankings,
	listingQuery,
	updateSource
} from './api';

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
				tags: ['a b', 'c'],
				archived: true,
				possible_edits: true
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
			tags: 'c',
			archived: 'true',
			possible_edits: 'true'
		});
		expect(q.getAll('tags')).toEqual(['a b', 'c']);
	});

	it('carries the ELO cut', () => {
		const q = listingQuery({ collection_id: 4, filters: { elo_end: 'bottom', elo_percent: 10 } });
		expect(Object.fromEntries(q)).toEqual({ collection_id: '4', elo_end: 'bottom', elo_percent: '10' });
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

describe('updateSource', () => {
	afterEach(() => vi.unstubAllGlobals());

	it("reports the server's reason when it refuses", async () => {
		vi.stubGlobal(
			'fetch',
			vi.fn(async () => new Response(JSON.stringify({ detail: '/x is mounted read-only' }), { status: 409 }))
		);
		await expect(updateSource(1, { writable: true })).rejects.toThrow(/^API error 409: \/x is mounted read-only$/);
	});
});

describe('deleteSource', () => {
	afterEach(() => vi.unstubAllGlobals());

	it("says whether to keep the data of the source's images", async () => {
		const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => new Response(null, { status: 204 }));
		vi.stubGlobal('fetch', fetchMock);
		await deleteSource(4, { keepData: false });
		expect(fetchMock.mock.lastCall![0]).toBe('/api/v1/sources/4?keep_data=false');
		expect(fetchMock.mock.lastCall![1]?.method).toBe('DELETE');
	});
});

describe('ELO requests', () => {
	afterEach(() => vi.unstubAllGlobals());

	/** Stubs fetch; the returned function gives the URL last requested. */
	function requested(): () => string {
		const fetchMock = vi.fn(async (_url: string) => new Response('{}'));
		vi.stubGlobal('fetch', fetchMock);
		return () => fetchMock.mock.lastCall![0];
	}

	it('draws a pair under the collection filters, ELO cut included', async () => {
		const url = requested();
		// Voting never draws archived images, whatever the collection's grid
		// shows, and draws from all images, not only possible edits.
		await getEloPair(
			3,
			{ aspect_ratio: 'portrait', elo_end: 'top', elo_percent: 25, archived: true, possible_edits: true },
			true
		);
		const q = new URL(url(), 'http://x').searchParams;
		expect(Object.fromEntries(q)).toEqual({
			aspect_ratio_filter: 'portrait',
			elo_end: 'top',
			elo_percent: '25',
			show_nsfw: 'true'
		});
	});

	it('pages the rankings', async () => {
		const url = requested();
		await getEloRankings(3, { offset: 100, limit: 50, showNsfw: true });
		expect(url()).toBe('/api/v1/collections/3/elo/rankings?offset=100&limit=50&show_nsfw=true');
	});
});

describe('decidePossibleEdit', () => {
	afterEach(() => vi.unstubAllGlobals());

	it('posts the decision for the image', async () => {
		const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => new Response('{}'));
		vi.stubGlobal('fetch', fetchMock);
		await decidePossibleEdit('abc', 'merge');
		expect(fetchMock.mock.lastCall![0]).toBe('/api/v1/images/abc/possible-edit');
		expect(fetchMock.mock.lastCall![1]?.method).toBe('POST');
		expect(JSON.parse(fetchMock.mock.lastCall![1]?.body as string)).toEqual({ decision: 'merge' });
	});
});
