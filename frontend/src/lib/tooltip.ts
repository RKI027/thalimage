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
