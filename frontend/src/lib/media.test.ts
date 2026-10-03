import { describe, expect, it } from 'vitest';
import { isVideoFilename } from './media';

describe('isVideoFilename', () => {
	it('recognises video extensions in any case', () => {
		for (const name of ['a.mp4', 'b.MOV', 'c.webm', 'clip.final.avi']) {
			expect(isVideoFilename(name)).toBe(true);
		}
	});

	it('rejects stills and extension-less names', () => {
		for (const name of ['a.png', 'mp4', 'movie.mp4.png', '']) {
			expect(isVideoFilename(name)).toBe(false);
		}
	});
});
