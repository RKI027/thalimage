/**
 * Two images set against each other: a reference and the current image,
 * shown in one of three views, with their metadata lined up.
 */
import { getImage, getImageCopies, getImageTags } from './api';
import { formatSize } from './format';
import type { ImageCopy, ImageDetail, Tag } from './types';

/** What the comparison knows of one image. */
export interface ComparedImage {
	detail: ImageDetail;
	copies: ImageCopy[];
	tags: Tag[];
}

/** Fetch what the comparison shows of the image keyed `hash`. */
export async function loadCompared(hash: string): Promise<ComparedImage> {
	const [detail, copies, tags] = await Promise.all([getImage(hash), getImageCopies(hash), getImageTags(hash)]);
	return { detail, copies, tags };
}

/** One line of the metadata: the two values, and whether they differ. */
export interface ComparisonRow {
	label: string;
	reference: string;
	current: string;
	differs: boolean;
}

export type CompareMode = 'side' | 'toggle' | 'overlay';
export type OverlayKind = 'blend' | 'wipe';

const MODES: CompareMode[] = ['side', 'toggle', 'overlay'];

/** The view after `mode`, in the order the M key walks them; without
 * `overlay` (a video cannot be overlaid), the overlay is skipped. */
export function nextMode(mode: CompareMode, overlay = true): CompareMode {
	const modes = overlay ? MODES : MODES.filter((m) => m !== 'overlay');
	return modes[(modes.indexOf(mode) + 1) % modes.length];
}

// Each line: what it shows, and the value it compares (when the text alone
// would hide a difference, as rounded sizes do).
const LINES: {
	label: string;
	text: (image: ComparedImage) => string;
	value?: (image: ComparedImage) => unknown;
}[] = [
	{ label: 'Dimensions', text: ({ detail }) => `${detail.width} × ${detail.height}` },
	{
		label: 'File size',
		text: ({ detail }) => formatSize(detail.file_size),
		value: ({ detail }) => detail.file_size
	},
	{ label: 'Format', text: ({ detail }) => detail.format },
	{ label: 'Modified', text: ({ detail }) => date(detail.file_modified), value: ({ detail }) => detail.file_modified },
	{ label: 'Created', text: ({ detail }) => date(detail.file_created), value: ({ detail }) => detail.file_created },
	{
		label: 'Files',
		text: ({ copies }) => copies.map((c) => `${c.source_path.replace(/\/$/, '')}/${c.relative_path}`).join('\n')
	},
	{
		label: 'Tags',
		text: ({ detail, tags }) => [...tags.map((t) => t.name), ...detail.folder_tags].sort().join(', ')
	}
];

function date(iso: string | null): string {
	return iso ? new Date(iso).toLocaleString() : '—';
}

/** The metadata of the two images, line by line. */
export function comparisonRows(reference: ComparedImage, current: ComparedImage): ComparisonRow[] {
	return LINES.map(({ label, text, value = text }) => ({
		label,
		reference: text(reference),
		current: text(current),
		differs: value(reference) !== value(current)
	}));
}
