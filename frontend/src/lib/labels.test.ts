import { describe, expect, it } from 'vitest';
import { labelCounts, missingNamespaces, nextUnlabelled, toggleLabel, type Namespace } from './labels';

const VOCAB: Namespace[] = [
	{ name: 'medium', multiple: false, values: ['photographic', 'pixel'] },
	{ name: 'overlay', multiple: true, values: ['none', 'anime', 'cinematic'] }
];

describe('toggleLabel', () => {
	it('replaces the value of a single-valued namespace', () => {
		expect(toggleLabel(VOCAB, ['medium:pixel', 'overlay:anime'], 'medium:photographic')).toEqual({
			add: ['medium:photographic'],
			remove: ['medium:pixel']
		});
	});

	it('removes a label the image already has', () => {
		expect(toggleLabel(VOCAB, ['medium:pixel'], 'medium:pixel')).toEqual({ add: [], remove: ['medium:pixel'] });
		expect(toggleLabel(VOCAB, ['overlay:anime'], 'overlay:anime')).toEqual({ add: [], remove: ['overlay:anime'] });
	});

	it('adds to a multi-valued namespace, where none excludes the others', () => {
		expect(toggleLabel(VOCAB, ['overlay:anime'], 'overlay:cinematic')).toEqual({
			add: ['overlay:cinematic'],
			remove: []
		});
		expect(toggleLabel(VOCAB, ['overlay:anime', 'overlay:cinematic'], 'overlay:none')).toEqual({
			add: ['overlay:none'],
			remove: ['overlay:anime', 'overlay:cinematic']
		});
		expect(toggleLabel(VOCAB, ['overlay:none'], 'overlay:anime')).toEqual({
			add: ['overlay:anime'],
			remove: ['overlay:none']
		});
	});
});

describe('missingNamespaces', () => {
	it('lists the namespaces without a label', () => {
		expect(missingNamespaces(VOCAB, ['overlay:none', 'other:x'])).toEqual(['medium']);
		expect(missingNamespaces(VOCAB, ['medium:pixel', 'overlay:anime'])).toEqual([]);
	});
});

describe('labelCounts', () => {
	it('counts each label over the images', () => {
		const counts = labelCounts([
			{ content_hash: 'a', labels: ['medium:pixel', 'overlay:anime'] },
			{ content_hash: 'b', labels: ['medium:pixel'] }
		]);
		expect(counts.get('medium:pixel')).toBe(2);
		expect(counts.get('overlay:anime')).toBe(1);
		expect(counts.get('medium:photographic')).toBeUndefined();
	});
});

describe('nextUnlabelled', () => {
	const images = [
		{ content_hash: 'a', labels: [] },
		{ content_hash: 'b', labels: ['medium:pixel', 'overlay:none'] },
		{ content_hash: 'c', labels: ['medium:pixel'] }
	];

	it('finds the next image missing a namespace, wrapping round', () => {
		expect(nextUnlabelled(VOCAB, images, 0)).toBe(2);
		expect(nextUnlabelled(VOCAB, images, 2)).toBe(0);
	});

	it('is -1 when every image is labelled', () => {
		expect(nextUnlabelled(VOCAB, [images[1]], 0)).toBe(-1);
	});
});
