import { describe, expect, it } from 'vitest';
import { copyPath, readOnlySources } from './imageCopies';

const copy = (source_path: string, relative_path: string, writable = true) => ({
	source_id: source_path.length,
	source_path,
	relative_path,
	writable,
	sidecars: []
});

describe('copyPath', () => {
	it('joins the source folder and the relative path', () => {
		expect(copyPath(copy('/images', 'sub/a.png'))).toBe('/images/sub/a.png');
	});

	it('does not double a trailing slash', () => {
		expect(copyPath(copy('/images/', 'a.png'))).toBe('/images/a.png');
	});
});

describe('readOnlySources', () => {
	it('names each read-only source once', () => {
		const copies = [
			copy('/ro', 'a.png', false),
			copy('/ro', 'b.png', false),
			copy('/rw', 'a.png', true)
		];
		expect(readOnlySources(copies)).toEqual(['/ro']);
	});

	it('is empty when every source is writable', () => {
		expect(readOnlySources([copy('/rw', 'a.png')])).toEqual([]);
	});
});
