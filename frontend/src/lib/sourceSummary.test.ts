import { describe, expect, it } from 'vitest';
import { summaryHeadline, summaryLines } from './sourceSummary';
import type { SourceSummary } from './types';

const empty: SourceSummary = { files: 0, images: 0, duplicates: [], archived: [], failures: [] };

describe('summaryHeadline', () => {
	it('sets files against images', () => {
		expect(summaryHeadline({ ...empty, files: 1390, images: 954 })).toBe('1,390 files → 954 images');
	});

	it('uses the singular for one', () => {
		expect(summaryHeadline({ ...empty, files: 1, images: 1 })).toBe('1 file → 1 image');
	});
});

describe('summaryLines', () => {
	it('is empty for a source with nothing to explain', () => {
		expect(summaryLines({ ...empty, files: 3, images: 3 })).toEqual([]);
	});

	it('counts the extra copies, not the groups', () => {
		const duplicates = [
			{ content_hash: 'a', paths: ['a.png', 'a2.png', 'a3.png'], sidecars: {} },
			{ content_hash: 'b', paths: ['b.png', 'b2.png'], sidecars: {} }
		];
		expect(summaryLines({ ...empty, duplicates })).toEqual([
			{ kind: 'duplicates', label: '3 duplicate files (same content as another file)' }
		]);
	});

	it('lists failures and archived images in that order, singular where one', () => {
		const lines = summaryLines({
			...empty,
			failures: [{ relative_path: 'x.png', reason: 'bad' }],
			archived: [
				{ content_hash: 'c', relative_path: 'c.png' },
				{ content_hash: 'd', relative_path: 'd.png' }
			]
		});
		expect(lines).toEqual([
			{ kind: 'failures', label: '1 file not indexed (the last scan failed on it)' },
			{ kind: 'archived', label: '2 archived images (not shown when browsing)' }
		]);
	});
});
