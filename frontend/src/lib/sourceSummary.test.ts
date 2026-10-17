import { describe, expect, it } from 'vitest';
import { summaryHeadline, summaryLines } from './sourceSummary';
import type { SourceSummary } from './types';

const empty: SourceSummary = { files: 0, images: 0, duplicates: [], archived: [], failures: [], orphans: [] };

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
			{ content_hash: 'a', paths: ['a.png', 'a2.png', 'a3.png'], sidecars: {}, file_hashes: {} },
			{ content_hash: 'b', paths: ['b.png', 'b2.png'], sidecars: {}, file_hashes: {} }
		];
		expect(summaryLines({ ...empty, duplicates })).toEqual([
			{ kind: 'duplicates', label: '3 duplicate files (same picture as another file)' }
		]);
	});

	it('counts the copies whose metadata differs from the first', () => {
		const duplicates = [
			{
				content_hash: 'a',
				paths: ['a.png', 'a2.png', 'a3.png'],
				sidecars: {},
				file_hashes: { 'a.png': 'x', 'a2.png': 'x', 'a3.png': 'y' }
			}
		];
		expect(summaryLines({ ...empty, duplicates })).toEqual([
			{
				kind: 'duplicates',
				label: '2 duplicate files (same picture as another file, 1 with different metadata)'
			}
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

	it('lists the orphan files last', () => {
		const lines = summaryLines({
			...empty,
			archived: [{ content_hash: 'c', relative_path: 'c.png' }],
			orphans: ['readme.txt']
		});
		expect(lines.map((l) => l.kind)).toEqual(['archived', 'orphans']);
		expect(lines[1].label).toBe('1 orphan file (no image or video is named after it)');
	});
});
