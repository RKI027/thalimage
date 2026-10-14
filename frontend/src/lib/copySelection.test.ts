import { describe, expect, it } from 'vitest';
import { allButFirst, canSelect, toggled } from './copySelection';

const groups = [
	{ content_hash: 'a', paths: ['a.png', 'a2.png', 'a3.png'] },
	{ content_hash: 'b', paths: ['b.png', 'b2.png'] }
];

describe('canSelect', () => {
	it('allows any copy while others in its group stay', () => {
		expect(canSelect(groups[0], new Set(['a.png']), 'a2.png')).toBe(true);
	});

	it('refuses the last unselected copy of a group', () => {
		expect(canSelect(groups[1], new Set(['b.png']), 'b2.png')).toBe(false);
	});

	it('always allows unselecting', () => {
		expect(canSelect(groups[1], new Set(['b.png']), 'b.png')).toBe(true);
	});
});

describe('toggled', () => {
	it('adds and removes a path without touching the original', () => {
		const start = new Set(['a.png']);
		expect([...toggled(start, 'a2.png')]).toEqual(['a.png', 'a2.png']);
		expect([...toggled(start, 'a.png')]).toEqual([]);
		expect([...start]).toEqual(['a.png']);
	});
});

describe('allButFirst', () => {
	it('selects every copy except the first of each group', () => {
		expect([...allButFirst(groups)]).toEqual(['a2.png', 'a3.png', 'b2.png']);
	});
});
