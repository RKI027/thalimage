import { describe, expect, it } from 'vitest';
import { scanDoneMessage } from './scanStatus';
import type { ScanProgress } from './types';

const done: ScanProgress = {
	source_id: 1,
	phase: 'complete',
	current: 3,
	total: 3,
	added: 1,
	skipped: 2,
	errors: 0,
	sidecars_added: 0,
	sidecars_changed: 0,
	sidecars_removed: 0,
	renamed: 0,
	message: ''
};

describe('scanDoneMessage', () => {
	it('counts the files', () => {
		expect(scanDoneMessage(done)).toBe('Done: 1 added, 2 skipped, 0 errors');
	});

	it('counts the sidecars when any changed', () => {
		expect(scanDoneMessage({ ...done, sidecars_added: 2, sidecars_removed: 1 })).toBe(
			'Done: 1 added, 2 skipped, 0 errors; sidecars: 2 added, 0 changed, 1 removed'
		);
	});

	it('counts the files renamed to their picture hash', () => {
		expect(scanDoneMessage({ ...done, renamed: 3, sidecars_added: 1 })).toBe(
			'Done: 1 added, 2 skipped, 0 errors, 3 renamed; sidecars: 1 added, 0 changed, 0 removed'
		);
	});
});
