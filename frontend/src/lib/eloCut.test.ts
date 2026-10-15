import { describe, expect, it } from 'vitest';
import { eloCutLabel, withEloCut } from './eloCut';

describe('withEloCut', () => {
	it('sets the cut, keeping the other filters', () => {
		expect(withEloCut({ media_type: 'video' }, 'bottom', 10)).toEqual({
			media_type: 'video',
			elo_end: 'bottom',
			elo_percent: 10
		});
	});

	it('clears the cut without a percentage', () => {
		expect(withEloCut({ media_type: 'video', elo_end: 'top', elo_percent: 5 }, 'top', undefined)).toEqual({
			media_type: 'video'
		});
	});

	it('keeps the percentage between 1 and 100, whole', () => {
		expect(withEloCut({}, 'top', 0).elo_percent).toBe(1);
		expect(withEloCut({}, 'top', 250).elo_percent).toBe(100);
		expect(withEloCut({}, 'top', 12.6).elo_percent).toBe(13);
		expect(withEloCut({}, 'top', NaN)).toEqual({});
	});
});

describe('eloCutLabel', () => {
	it('names the cut, or nothing when there is none', () => {
		expect(eloCutLabel({ elo_end: 'top', elo_percent: 10 })).toBe('Top 10%');
		expect(eloCutLabel({ elo_end: 'bottom', elo_percent: 25 })).toBe('Bottom 25%');
		expect(eloCutLabel({ media_type: 'video' })).toBeNull();
	});
});
