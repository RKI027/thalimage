import { describe, expect, it } from 'vitest';
import { placeTooltip, tooltipReaction } from './tooltip';

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

describe('tooltipReaction', () => {
	it('opens and closes as a mouse enters and leaves', () => {
		expect(tooltipReaction(false, { kind: 'enter', pointer: 'mouse' })).toEqual({ open: true, consume: false });
		expect(tooltipReaction(true, { kind: 'leave', pointer: 'mouse' })).toEqual({ open: false, consume: false });
	});

	it('ignores the hover a touchscreen fakes on tap', () => {
		expect(tooltipReaction(false, { kind: 'enter', pointer: 'touch' }).open).toBe(false);
		expect(tooltipReaction(true, { kind: 'leave', pointer: 'touch' }).open).toBe(true);
	});

	it('toggles on a touch tap and keeps the tap from reaching a link around it', () => {
		expect(tooltipReaction(false, { kind: 'tap', pointer: 'touch' })).toEqual({ open: true, consume: true });
		expect(tooltipReaction(true, { kind: 'tap', pointer: 'touch' })).toEqual({ open: false, consume: true });
		expect(tooltipReaction(false, { kind: 'tap', pointer: 'pen' })).toEqual({ open: true, consume: true });
	});

	it('lets a mouse click through untouched', () => {
		expect(tooltipReaction(true, { kind: 'tap', pointer: 'mouse' })).toEqual({ open: true, consume: false });
	});

	it('opens on focus and closes on blur, an outside tap or Escape', () => {
		expect(tooltipReaction(false, { kind: 'focus' }).open).toBe(true);
		for (const kind of ['blur', 'outside', 'dismiss'] as const) {
			expect(tooltipReaction(true, { kind }).open).toBe(false);
		}
	});
});
