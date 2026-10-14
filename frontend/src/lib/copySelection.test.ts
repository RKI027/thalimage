import { describe, expect, it } from 'vitest';
import { allButFirst, canSelect, toggled, unmatchedSidecars } from './copySelection';

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

describe('unmatchedSidecars', () => {
	const sidecar = (relative_path: string, digest: string) => ({ relative_path, digest });
	const group = {
		content_hash: 'c',
		paths: ['c.png', 'c2.png', 'c3.png'],
		sidecars: {
			'c.png': [sidecar('c.txt', 'x')],
			'c2.png': [sidecar('c2.txt', 'x'), sidecar('c2.json', 'w')],
			'c3.png': []
		}
	};

	it('lists sidecars of deleted copies that no kept copy has', () => {
		expect(unmatchedSidecars([group], new Set(['c2.png']))).toEqual(['c2.json']);
	});

	it('is empty when kept copies have identical sidecars', () => {
		expect(unmatchedSidecars([group], new Set(['c.png']))).toEqual([]);
	});

	it('compares within a group only', () => {
		const other = { content_hash: 'd', paths: ['d.png', 'd2.png'], sidecars: { 'd.png': [sidecar('d.txt', 'w')], 'd2.png': [] } };
		expect(unmatchedSidecars([group, other], new Set(['c2.png', 'd.png']))).toEqual([
			'c2.json',
			'd.txt'
		]);
	});
});
