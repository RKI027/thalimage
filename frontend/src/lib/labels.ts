/**
 * Labelling a set of images by hand with namespaced tags
 * (`medium:photographic`), for measuring the auto-tagging models (#164).
 */

export interface Namespace {
	name: string;
	/** Several values at once; then `none` says the image has none of them. */
	multiple: boolean;
	values: string[];
}

export interface ImageLabels {
	content_hash: string;
	labels: string[];
}

/** The labels of #126: each image gets one value of each namespace, or
 * one or more of a multi-valued one. */
export const VOCABULARY: Namespace[] = [
	{
		name: 'medium',
		multiple: false,
		values: ['photographic', 'rendered-3d', 'traditional-painted', 'ink-line', '2d-line-fill', 'flat-vector', 'pixel-voxel']
	},
	{
		name: 'style',
		multiple: false,
		values: ['naturalistic', 'semi-stylized', 'cel-shaded', 'stylized', 'flattened']
	},
	{
		name: 'overlay',
		multiple: true,
		values: [
			'none',
			'cinematic',
			'anime-manga',
			'western-comic',
			'cartoon',
			'ukiyo-e',
			'cyberpunk',
			'fantasy',
			'analog-film',
			'retro-8bit'
		]
	},
	{ name: 'rating', multiple: false, values: ['sfw', 'suggestive', 'erotic', 'porn'] },
	{ name: 'age', multiple: true, values: ['none', 'child', 'teen', 'adult', 'senior'] }
];

function namespaceOf(label: string): string {
	return label.slice(0, label.indexOf(':'));
}

/** The tags to add and remove when `label` is clicked on an image. */
export function toggleLabel(
	vocabulary: Namespace[],
	current: string[],
	label: string
): { add: string[]; remove: string[] } {
	if (current.includes(label)) return { add: [], remove: [label] };
	const ns = vocabulary.find((n) => n.name === namespaceOf(label));
	const sameNamespace = current.filter((l) => namespaceOf(l) === ns?.name);
	if (!ns || !ns.multiple) return { add: [label], remove: sameNamespace };
	const none = `${ns.name}:none`;
	return {
		add: [label],
		remove: label === none ? sameNamespace : sameNamespace.filter((l) => l === none)
	};
}

/** The namespaces in which the image has no label yet. */
export function missingNamespaces(vocabulary: Namespace[], labels: string[]): string[] {
	const present = new Set(labels.map(namespaceOf));
	return vocabulary.map((n) => n.name).filter((n) => !present.has(n));
}

/** How many images carry each label. */
export function labelCounts(images: ImageLabels[]): Map<string, number> {
	const counts = new Map<string, number>();
	for (const image of images) {
		for (const label of image.labels) counts.set(label, (counts.get(label) ?? 0) + 1);
	}
	return counts;
}

/** The index of the next image after `from` missing a namespace, wrapping
 * round to the start; -1 when every image is labelled. */
export function nextUnlabelled(vocabulary: Namespace[], images: ImageLabels[], from: number): number {
	for (let step = 1; step <= images.length; step++) {
		const i = (from + step) % images.length;
		if (missingNamespaces(vocabulary, images[i].labels).length > 0) return i;
	}
	return -1;
}
