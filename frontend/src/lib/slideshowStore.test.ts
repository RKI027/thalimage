import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { SequenceItem } from './types';

function images(n: number, score: number | null = null): SequenceItem[] {
	return Array.from({ length: n }, (_, i) => ({ content_hash: `h${i}`, filename: `f${i}.png`, score }));
}

const hashes = (items: SequenceItem[]) => items.map((i) => i.content_hash);

// The store is a module singleton that reads localStorage on creation.
async function freshStore() {
	vi.resetModules();
	return (await import('./slideshowStore.svelte')).slideshowStore;
}

describe('slideshowStore', () => {
	beforeEach(() => {
		localStorage.clear();
		vi.useFakeTimers();
	});
	afterEach(() => vi.useRealTimers());

	it('advances in order on its timer and stops at the end', async () => {
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(3), 0, (h) => shown.push(h));
		expect(store.status).toBe('playing');

		vi.advanceTimersByTime(5000 * 4);
		expect(shown).toEqual(['h1', 'h2']);
	});

	it('uses the stored interval and pauses the timer', async () => {
		localStorage.setItem('slideshow:interval', '1000');
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(5), 0, (h) => shown.push(h));
		vi.advanceTimersByTime(1000);
		store.pause();
		vi.advanceTimersByTime(5000);
		expect(shown).toEqual(['h1']);
		store.play();
		vi.advanceTimersByTime(1000);
		expect(shown).toEqual(['h1', 'h2']);
	});

	it('shows every image once per cycle in random mode, and rewinds', async () => {
		localStorage.setItem('slideshow:mode', '"random"');
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(6), 2, (h) => shown.push(h));
		for (let i = 0; i < 5; i++) store.advance();
		expect(new Set(['h2', ...shown]).size).toBe(6);

		store.back();
		store.back();
		expect(shown.slice(-2)).toEqual([shown[3], shown[2]]);
		// Forward again replays the same trail before drawing anew.
		store.advance();
		expect(shown.at(-1)).toBe(shown[3]);
	});

	it('walks ELO mode as random where no scores exist, keeping the preference', async () => {
		localStorage.setItem('slideshow:mode', '"elo"');
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(4), 3, (h) => shown.push(h));
		for (let i = 0; i < 3; i++) store.advance();
		expect(new Set(['h3', ...shown]).size).toBe(4);
		expect(store.config.mode).toBe('elo');
		store.toggleWeighted(); // unavailable here: no change
		expect(store.config.mode).toBe('elo');
	});

	it('toggles shuffle back to the last weighted mode', async () => {
		const store = await freshStore();
		store.enter(images(4, 1500), 0, () => {});
		store.setMode('elo');
		store.toggleShuffle();
		expect(store.config.mode).toBe('sequential');
		store.toggleShuffle();
		expect(store.config.mode).toBe('elo');
		expect(localStorage.getItem('slideshow:mode')).toBe('"elo"');
	});

	it('resumes sorted order from the image shown when shuffle is turned off', async () => {
		localStorage.setItem('slideshow:mode', '"random"');
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(2000), 0, (h) => shown.push(h));
		store.advance();
		store.advance();
		const at = Number(shown[1].slice(1));
		expect(store.position).toBe(at);
		store.toggleShuffle();
		store.advance();
		expect(shown[2]).toBe(`h${at + 1}`);
	});

	it('steps back through the listing in sequential order', async () => {
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(5), 3, (h) => shown.push(h));
		store.back();
		expect(shown).toEqual(['h2']);
		expect([store.position, store.total]).toEqual([2, 5]);
	});

	it('draws better-scored images more often in ELO mode', async () => {
		localStorage.setItem('slideshow:mode', '"elo"');
		const store = await freshStore();
		const items = images(50, 1500);
		items[49] = { ...items[49], score: 5000 };
		const shown: string[] = [];
		store.enter(items, 0, (h) => shown.push(h));
		for (let i = 0; i < 100; i++) store.advance();
		expect(shown.filter((h) => h === 'h49').length).toBeGreaterThan(50);
	});

	it('announces the slides it will show next, in every mode', async () => {
		for (const mode of ['sequential', 'random', 'elo']) {
			localStorage.setItem('slideshow:mode', JSON.stringify(mode));
			const store = await freshStore();
			const shown: string[] = [];
			store.enter(images(30, 1500), 5, (h) => shown.push(h));
			const next = hashes(store.upcoming(2));
			store.advance();
			store.advance();
			expect(shown, mode).toEqual(next);
		}
	});

	it('announces the slides behind the current one, nearest first', async () => {
		localStorage.setItem('slideshow:mode', '"random"');
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(30), 5, (h) => shown.push(h));
		for (let i = 0; i < 3; i++) store.advance();
		expect(hashes(store.recent(2))).toEqual([shown[1], shown[0]]);
		// After a rewind, what lies ahead is the trail already shown.
		store.back();
		expect(hashes(store.upcoming(1))).toEqual([shown[2]]);
	});

	it('migrates the legacy shuffle flag once', async () => {
		localStorage.setItem('slideshow:shuffle', 'true');
		const store = await freshStore();
		expect(store.config.mode).toBe('random');
		expect(localStorage.getItem('slideshow:shuffle')).toBeNull();
	});

	it('exit resets to idle and stops advancing', async () => {
		const store = await freshStore();
		const shown: string[] = [];
		store.enter(images(3), 0, (h) => shown.push(h));
		store.exit();
		vi.advanceTimersByTime(20000);
		expect(store.status).toBe('idle');
		expect(shown).toEqual([]);
	});
});
