/** Where a virtual grid stands: how many images it holds of the listing,
 * how they are laid out, and what the viewport shows. */
export interface GridPosition {
	loaded: number;
	total: number;
	columns: number;
	cellSize: number;
	scrollTop: number;
	viewportHeight: number;
}

/** Whether the grid should fetch the next page: images remain, and the
 * viewport's bottom is within one viewport of the last loaded row (or past
 * it). Measured against the loaded rows, not the whole listing, whose full
 * height the grid reserves up front. */
export function needsMoreImages(g: GridPosition): boolean {
	if (g.loaded >= g.total) return false;
	const loadedBottom = Math.ceil(g.loaded / g.columns) * g.cellSize;
	return g.scrollTop + 2 * g.viewportHeight >= loadedBottom;
}
