import { describe, expect, it } from 'vitest';
import { ImageSelection } from './imageSelection.svelte';

const order = ['a', 'b', 'c', 'd', 'e'];

function selection(): ImageSelection {
	return new ImageSelection(() => order);
}

describe('ImageSelection', () => {
	it('starts inactive and empty', () => {
		const s = selection();
		expect(s.active).toBe(false);
		expect(s.count).toBe(0);
	});

	it('toggles an image on each click', () => {
		const s = selection();
		s.start();
		s.click('b');
		s.click('d');
		expect(s.hashes).toEqual(['b', 'd']);
		s.click('b');
		expect(s.hashes).toEqual(['d']);
		expect(s.has('d')).toBe(true);
		expect(s.has('b')).toBe(false);
	});

	it('starts selecting with the first image clicked', () => {
		const s = selection();
		s.click('c');
		expect(s.active).toBe(true);
		expect(s.hashes).toEqual(['c']);
	});

	it('selects a range from the last image clicked, either way', () => {
		const s = selection();
		s.click('b');
		s.click('d', { range: true });
		expect(s.hashes).toEqual(['b', 'c', 'd']);

		const t = selection();
		t.click('d');
		t.click('b', { range: true });
		expect(t.hashes).toEqual(['b', 'c', 'd']);
	});

	it('keeps what a range adds to, and chains ranges from its end', () => {
		const s = selection();
		s.click('a');
		s.click('c');
		s.click('d', { range: true });
		expect(s.hashes).toEqual(['a', 'c', 'd']);
		s.click('e', { range: true });
		expect(s.hashes).toEqual(['a', 'c', 'd', 'e']);
	});

	it('takes a range with nothing clicked before as one image', () => {
		const s = selection();
		s.click('c', { range: true });
		expect(s.hashes).toEqual(['c']);
	});

	it('lists the selection in the grid order', () => {
		const s = selection();
		s.click('e');
		s.click('a');
		expect(s.hashes).toEqual(['a', 'e']);
	});

	it('forgets everything on stop', () => {
		const s = selection();
		s.click('a');
		s.stop();
		expect(s.active).toBe(false);
		expect(s.count).toBe(0);
		s.click('c', { range: true });
		expect(s.hashes).toEqual(['c']);
	});
});
