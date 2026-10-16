import { describe, expect, it } from 'vitest';
import { needsMoreImages } from './gridPaging';

// 3,000 images, 500 loaded, 5 per row of 100px: the loaded rows end at 10,000px
// of a 60,000px grid.
const grid = { loaded: 500, total: 3000, columns: 5, cellSize: 100, viewportHeight: 800 };

describe('needsMoreImages', () => {
	it('waits while the loaded images reach well below the viewport', () => {
		expect(needsMoreImages({ ...grid, scrollTop: 0 })).toBe(false);
	});

	it('asks for more within a viewport of the last loaded row', () => {
		expect(needsMoreImages({ ...grid, scrollTop: 8500 })).toBe(true);
	});

	it('asks for more when the viewport is past the loaded images', () => {
		expect(needsMoreImages({ ...grid, scrollTop: 40000 })).toBe(true);
	});

	it('asks for more when the loaded images do not fill the viewport', () => {
		expect(needsMoreImages({ ...grid, loaded: 10, scrollTop: 0 })).toBe(true);
	});

	it('never asks once everything is loaded', () => {
		expect(needsMoreImages({ ...grid, loaded: 3000, scrollTop: 59200 })).toBe(false);
	});
});
