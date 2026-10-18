/**
 * Reviewing a group of images: one is the reference, the others are compared
 * with it in turn, and each image can be flagged for an action carried out
 * when the review ends. Flags are only a plan until then.
 */
import type { ComparedImage } from './comparison';
import type { ImageSummary } from './types';

export type ReviewAction = 'archive' | 'merge' | 'delete';

/** What applying the flags does, by key: `merge` goes into `reference`. */
export interface ReviewPlan {
	reference: string;
	merge: string[];
	archive: string[];
	delete: string[];
}

/** The image a review starts from: the most pixels, then the largest file,
 * then the first. */
export function pickReference(images: ComparedImage[]): number {
	let best = 0;
	images.forEach(({ detail }, i) => {
		const top = images[best].detail;
		const pixels = detail.width * detail.height - top.width * top.height;
		if (pixels > 0 || (pixels === 0 && detail.file_size > top.file_size)) best = i;
	});
	return best;
}

/** The keys of the near-duplicate group of the image at `index` in a
 * window of a grouped listing; empty if it is in none. */
export function groupAround(window: ImageSummary[], index: number): string[] {
	const group = window[index]?.duplicate_group;
	if (group == null) return [];
	let start = index;
	while (start > 0 && window[start - 1].duplicate_group === group) start--;
	let end = index;
	while (end < window.length - 1 && window[end + 1].duplicate_group === group) end++;
	return window.slice(start, end + 1).map((image) => image.content_hash);
}

/** The keys of the near-duplicate group listed next, from the images
 * listed `after` the group reviewed (`reviewed`); empty past the last. */
export function nextGroup(after: ImageSummary[], reviewed: string[]): string[] {
	const rest = after.filter((image) => !reviewed.includes(image.content_hash));
	const group = rest[0]?.duplicate_group;
	if (group == null) return [];
	const members: string[] = [];
	for (const image of rest) {
		if (image.duplicate_group !== group) break;
		members.push(image.content_hash);
	}
	return members;
}

const key = (image: ComparedImage) => image.detail.content_hash;

export class ReviewSession {
	// Deeply reactive: editing an image's tags updates its comparison.
	images = $state<ComparedImage[]>([]);
	#reference = $state(0);
	#current = $state(0);
	#flags = $state<Record<string, ReviewAction>>({});
	// Each flag change, with the flag it replaced, for undo.
	#history: { image: string; before: ReviewAction | undefined }[] = [];

	constructor(images: ComparedImage[]) {
		this.images = images;
		this.#reference = pickReference(images);
		this.#current = this.#reference === 0 ? 1 : 0;
	}

	get reference(): ComparedImage {
		return this.images[this.#reference];
	}

	get current(): ComparedImage {
		return this.images[this.#current];
	}

	/** Every image but the reference, in group order. */
	get others(): ComparedImage[] {
		return this.images.filter((_, i) => i !== this.#reference);
	}

	flagOf(image: string): ReviewAction | undefined {
		return this.#flags[image];
	}

	/** Show the image keyed `image` as the current one; the reference is
	 * not, as it is always shown. */
	show(image: string): void {
		const i = this.images.findIndex((candidate) => key(candidate) === image);
		if (i >= 0 && i !== this.#reference) this.#current = i;
	}

	next(): void {
		this.#step(1);
	}

	previous(): void {
		this.#step(-1);
	}

	#step(delta: number): void {
		const n = this.images.length;
		let i = this.#current;
		do i = (i + delta + n) % n;
		while (i === this.#reference);
		this.#current = i;
	}

	/** The current image becomes the reference, and the reference current.
	 * An image made the reference cannot merge into itself: its merge flag
	 * is dropped. */
	makeReference(): void {
		[this.#reference, this.#current] = [this.#current, this.#reference];
		if (this.flagOf(key(this.reference)) === 'merge') this.#set(key(this.reference), undefined);
	}

	/** Flag the current image (or the reference) for `action`, or clear its
	 * flag if it has that one already. False, changing nothing, for merging
	 * the reference into itself. */
	flag(action: ReviewAction, target: 'current' | 'reference' = 'current'): boolean {
		if (target === 'reference' && action === 'merge') return false;
		const image = key(target === 'current' ? this.current : this.reference);
		this.#set(image, this.flagOf(image) === action ? undefined : action);
		return true;
	}

	#set(image: string, action: ReviewAction | undefined): void {
		this.#history.push({ image, before: this.flagOf(image) });
		const { [image]: _, ...rest } = this.#flags;
		this.#flags = action ? { ...rest, [image]: action } : rest;
	}

	/** Take back the last flag change. */
	undo(): void {
		const last = this.#history.pop();
		if (!last) return;
		const { [last.image]: _, ...rest } = this.#flags;
		this.#flags = last.before ? { ...rest, [last.image]: last.before } : rest;
	}

	get flagged(): number {
		return Object.keys(this.#flags).length;
	}

	get plan(): ReviewPlan {
		const by = (action: ReviewAction) =>
			this.images.map(key).filter((image) => this.#flags[image] === action);
		return { reference: key(this.reference), merge: by('merge'), archive: by('archive'), delete: by('delete') };
	}

	/** Why the plan cannot be applied as it stands, or null. */
	get problem(): string | null {
		const plan = this.plan;
		if (plan.merge.length > 0 && plan.delete.includes(plan.reference))
			return 'The reference cannot be deleted while images merge into it.';
		return null;
	}
}
