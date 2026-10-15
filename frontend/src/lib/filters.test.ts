import { describe, expect, it } from 'vitest';
import { activeFilterCount } from './filters';

describe('activeFilterCount', () => {
	it('counts nothing when no filter is set', () => {
		expect(activeFilterCount({})).toBe(0);
	});

	it('counts each filter set', () => {
		expect(activeFilterCount({ date_from: '2026-01-01', date_to: '2026-02-01', media_type: 'video' })).toBe(3);
	});

	it('counts the ELO cut once, end and percentage together', () => {
		expect(activeFilterCount({ elo_end: 'top', elo_percent: 10, tags: ['a', 'b'] })).toBe(2);
	});
});
