import { previewUrl } from './api';
import { isVideoFilename } from './media';
import type { SequenceItem } from './types';

function loadPreview(hash: string): HTMLImageElement {
	const img = new Image();
	img.src = previewUrl(hash);
	return img;
}

/** Keeps the previews of a set of slides loaded, so a slideshow shows them
 * at once: each call loads the slides not yet held and lets go of the rest.
 * Videos are skipped — their full files are too large to prefetch eagerly. */
export function createSlidePreloader(load: (hash: string) => unknown = loadPreview) {
	let held = new Map<string, unknown>();
	return function keep(slides: SequenceItem[]): void {
		const next = new Map<string, unknown>();
		for (const { content_hash: hash, filename } of slides) {
			if (isVideoFilename(filename)) continue;
			next.set(hash, held.has(hash) ? held.get(hash) : load(hash));
		}
		held = next;
	};
}
