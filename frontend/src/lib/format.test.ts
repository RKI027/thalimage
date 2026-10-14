import { describe, expect, it } from 'vitest';
import { formatSize, describeBackup } from './format';

describe('formatSize', () => {
	it('picks a unit to suit the size', () => {
		expect(formatSize(512)).toBe('512 B');
		expect(formatSize(1536)).toBe('1.5 KB');
		expect(formatSize(12 * 1024 * 1024)).toBe('12.0 MB');
	});
});

describe('describeBackup', () => {
	const at = '2026-10-14T06:00:00';
	const when = new Date(at).toLocaleString();

	it('says when nothing has run yet', () => {
		expect(describeBackup(null)).toBe('No backup yet');
	});

	it('names the file and its size after a success', () => {
		expect(
			describeBackup({ at, file: 'thalimage-20261014-060000.db', size: 12 * 1024 * 1024, error: null })
		).toBe(`${when} · thalimage-20261014-060000.db · 12.0 MB`);
	});

	it('reports the error after a failure', () => {
		expect(describeBackup({ at, file: null, size: null, error: 'disk full' })).toBe(
			`Failed ${when}: disk full`
		);
	});
});
