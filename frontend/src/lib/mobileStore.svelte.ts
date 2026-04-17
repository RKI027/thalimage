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

/**
 * Calculate the thumb size that produces the desired number of columns
 * for the current viewport width. Uses window.innerWidth, so call only
 * in browser context.
 */
export function responsiveThumbSize(): number {
	const isPortrait = window.innerHeight > window.innerWidth;
	const cols = isPortrait ? 2 : 3;
	return Math.floor((window.innerWidth + 8) / cols);
}
