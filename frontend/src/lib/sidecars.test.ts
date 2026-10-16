import { describe, expect, it } from 'vitest';
import { distinctSidecars } from './sidecars';

const sidecar = (relative_path: string, text: string | null, size = 9) => ({
	source_id: 1,
	relative_path,
	size,
	text
});

describe('distinctSidecars', () => {
	it('shows sidecars that say the same thing once, under all their names', () => {
		expect(
			distinctSidecars([
				sidecar('a.txt', 'steps: 20'),
				sidecar('b.txt', 'steps: 30'),
				sidecar('sub/a.txt', 'steps: 20')
			])
		).toEqual([
			{ names: ['a.txt', 'sub/a.txt'], size: 9, text: 'steps: 20' },
			{ names: ['b.txt'], size: 9, text: 'steps: 30' }
		]);
	});

	it('keeps each sidecar without text on its own', () => {
		expect(distinctSidecars([sidecar('a.bin', null, 3), sidecar('sub/a.bin', null, 3)])).toEqual([
			{ names: ['a.bin'], size: 3, text: null },
			{ names: ['sub/a.bin'], size: 3, text: null }
		]);
	});
});
