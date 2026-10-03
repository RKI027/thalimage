import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ImagePage } from './types';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

const listImages = vi.fn();
vi.mock('./api', () => ({ listImages: (...args: unknown[]) => listImages(...args) }));

const { Gallery } = await import('./gallery.svelte');

function page(hashes: string[], next: string | null = null): ImagePage {
	return {
		items: hashes.map((h) => ({ content_hash: h }) as ImagePage['items'][number]),
		next_cursor: next,
		total_count: hashes.length
	};
}

/** A listImages call that resolves when the test says so. */
function deferred() {
	let resolve!: (p: ImagePage) => void;
	const promise = new Promise<ImagePage>((r) => (resolve = r));
	return { promise, resolve };
}

describe('Gallery', () => {
	beforeEach(() => {
		listImages.mockReset();
		localStorage.clear();
	});

	it('pages forward with the cursor and the current query', async () => {
		let sort = 'name';
		const g = new Gallery(() => ({ sort: sort as 'name' }));
		listImages.mockResolvedValueOnce(page(['a', 'b'], 'c1'));
		await g.reset();
		listImages.mockResolvedValueOnce(page(['c']));
		await g.loadMore();
		expect(g.images.map((i) => i.content_hash)).toEqual(['a', 'b', 'c']);
		expect(listImages.mock.calls[1][0]).toMatchObject({ sort: 'name', cursor: 'c1' });
		await g.loadMore(); // no next page: no request
		expect(listImages).toHaveBeenCalledTimes(2);
		sort = 'size';
		listImages.mockResolvedValueOnce(page(['z']));
		await g.reset();
		expect(listImages.mock.calls[2][0]).toMatchObject({ sort: 'size', cursor: null });
	});

	it('lets a reset supersede a load in flight (GEN-011)', async () => {
		const g = new Gallery(() => ({}));
		listImages.mockResolvedValueOnce(page(['a'], 'c1'));
		await g.reset();

		const slowMore = deferred();
		listImages.mockReturnValueOnce(slowMore.promise);
		const more = g.loadMore();
		listImages.mockResolvedValueOnce(page(['fresh']));
		await g.reset();
		slowMore.resolve(page(['stale']));
		await more;

		expect(g.images.map((i) => i.content_hash)).toEqual(['fresh']);
		expect(g.loading).toBe(false);
		// The superseded request was told to stop.
		expect((listImages.mock.calls[1][1] as RequestInit).signal?.aborted).toBe(true);
	});

	it('keeps only the latest of two racing resets', async () => {
		const g = new Gallery(() => ({}));
		const first = deferred();
		listImages.mockReturnValueOnce(first.promise);
		const a = g.reset();
		listImages.mockResolvedValueOnce(page(['second']));
		await g.reset();
		first.resolve(page(['first']));
		await a;
		expect(g.images.map((i) => i.content_hash)).toEqual(['second']);
	});

	it('reports errors, but not those of superseded requests', async () => {
		const g = new Gallery(() => ({}));
		listImages.mockRejectedValueOnce(new Error('boom'));
		await g.reset();
		expect(g.error).toBe('boom');
		expect(g.loaded).toBe(true);

		const doomed = deferred();
		listImages.mockReturnValueOnce(doomed.promise.then(() => Promise.reject(new Error('late'))));
		const a = g.reset();
		listImages.mockResolvedValueOnce(page(['ok']));
		await g.reset();
		doomed.resolve(page([]));
		await a;
		expect(g.error).toBeNull();
	});

	it('remembers the thumbnail size', async () => {
		const g = new Gallery(() => ({}));
		expect(g.thumbSize).toBe(200);
		g.thumbSize = 320;
		expect(new Gallery(() => ({})).thumbSize).toBe(320);
	});
});
