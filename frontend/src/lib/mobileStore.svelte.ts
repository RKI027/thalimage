/**
 * Shared mobile UI state — drawer open/close accessible by both the layout
 * (which renders the Sidebar and backdrop) and page-level mobile headers
 * (which contain the hamburger button).
 */

let drawerOpen = $state(false);

export const mobileStore = {
	get drawerOpen() {
		return drawerOpen;
	},
	open() {
		drawerOpen = true;
	},
	close() {
		drawerOpen = false;
	}
};

const GRID_GAP = 8;

/**
 * Calculate the thumb size that produces the desired number of columns
 * for the current viewport width. Uses window.innerWidth, so call only
 * in browser context.
 *
 * Formula: Math.floor((W - (N-1)*gap) / N), which gives a cellSize that
 * fits exactly N columns with N-1 gaps, matching ImageGrid's column
 * calculation with enough margin to survive sub-pixel layout variance.
 */
export function responsiveThumbSize(): number {
	const isPortrait = window.innerHeight > window.innerWidth;
	const cols = isPortrait ? 2 : 3;
	const w = document.documentElement.clientWidth;
	return Math.floor((w - (cols - 1) * GRID_GAP) / cols);
}
