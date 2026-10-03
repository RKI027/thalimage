import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ImageSummary } from './types';

function images(n: number): ImageSummary[] {
	return Array.from({ length: n }, (_, i) => ({ content_hash: `h${i}` }) as ImageSummary);
}

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
		store.enter(images(4), 0, () => {}, { eloAvailable: false });
		expect(store.isShuffle).toBe(true);
		expect(store.config.mode).toBe('elo');
		store.toggleWeighted(); // unavailable here: no change
		expect(store.config.mode).toBe('elo');
	});

	it('toggles shuffle back to the last weighted mode', async () => {
		const store = await freshStore();
		store.enter(images(4), 0, () => {}, { eloAvailable: true });
		store.setMode('elo');
		store.toggleShuffle();
		expect(store.config.mode).toBe('sequential');
		store.toggleShuffle();
		expect(store.config.mode).toBe('elo');
		expect(localStorage.getItem('slideshow:mode')).toBe('"elo"');
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
