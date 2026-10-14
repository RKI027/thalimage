export interface Rect {
	left: number;
	top: number;
	width: number;
	height: number;
}

interface Size {
	width: number;
	height: number;
}

const GAP = 6;
const MARGIN = 8;

/**
 * Where a tooltip of size `tip` goes for an anchor at `anchor` (viewport
 * coordinates): centred above it, below if there is no room above, and
 * kept inside the viewport's edges.
 */
export function placeTooltip(anchor: Rect, tip: Size, viewport: Size): { left: number; top: number } {
	const centred = anchor.left + anchor.width / 2 - tip.width / 2;
	const left = Math.max(MARGIN, Math.min(centred, viewport.width - MARGIN - tip.width));
	const above = anchor.top - GAP - tip.height;
	const top = above >= MARGIN ? above : anchor.top + anchor.height + GAP;
	return { left, top };
}

/**
 * What happened to a tooltip's anchor. `pointer` is the PointerEvent
 * pointerType: "mouse", "touch" or "pen".
 */
export type TooltipEvent =
	| { kind: 'enter' | 'leave' | 'tap'; pointer: string }
	| { kind: 'focus' | 'blur' | 'outside' | 'dismiss' };

/**
 * Whether the tooltip is open after `event`, and whether the event must
 * stop there. A mouse opens it by hovering and its clicks pass through; a
 * touchscreen has no hover, so a tap toggles it and is consumed, keeping
 * a link around the anchor from navigating.
 */
export function tooltipReaction(open: boolean, event: TooltipEvent): { open: boolean; consume: boolean } {
	switch (event.kind) {
		case 'enter':
		case 'leave':
			return { open: event.pointer === 'mouse' ? event.kind === 'enter' : open, consume: false };
		case 'tap':
			return event.pointer === 'mouse' ? { open, consume: false } : { open: !open, consume: true };
		case 'focus':
			return { open: true, consume: false };
		default:
			return { open: false, consume: false };
	}
}
