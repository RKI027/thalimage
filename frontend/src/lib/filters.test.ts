import { describe, expect, it } from 'vitest';
import { activeFilterCount, withFilters } from './filters';

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

describe('withFilters', () => {
	it('sets the filters given', () => {
		expect(withFilters({ media_type: 'video' }, { aspect_ratio: 'square' })).toEqual({
			media_type: 'video',
			aspect_ratio: 'square'
		});
	});

	it('drops a filter set back to its default, leaving no filter counted', () => {
		const set = withFilters({}, { media_type: 'video' });
		const unset = withFilters(set, { media_type: undefined });
		expect(unset).toEqual({});
		expect(activeFilterCount(unset)).toBe(0);
	});

	it('drops an emptied value', () => {
		expect(withFilters({ date_from: '2026-01-01' }, { date_from: '' as never })).toEqual({});
	});
});
