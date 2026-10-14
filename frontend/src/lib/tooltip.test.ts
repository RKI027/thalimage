import { describe, expect, it } from 'vitest';
import { placeTooltip } from './tooltip';

const viewport = { width: 800, height: 600 };
const tip = { width: 100, height: 30 };
const anchor = (left: number, top: number) => ({ left, top, width: 20, height: 20 });

describe('placeTooltip', () => {
	it('centres the tip above its anchor', () => {
		expect(placeTooltip(anchor(390, 300), tip, viewport)).toEqual({ left: 350, top: 264 });
	});

	it('goes below when there is no room above', () => {
		expect(placeTooltip(anchor(390, 10), tip, viewport)).toEqual({ left: 350, top: 36 });
	});

	it('stays inside the left edge', () => {
		expect(placeTooltip(anchor(0, 300), tip, viewport).left).toBe(8);
	});

	it('stays inside the right edge', () => {
		expect(placeTooltip(anchor(790, 300), tip, viewport).left).toBe(692);
	});
});
