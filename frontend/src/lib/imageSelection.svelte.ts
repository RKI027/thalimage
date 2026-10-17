/**
 * The images selected in a grid, to act on at once. A click toggles one
 * image; a range click selects every image from the last one clicked to
 * this one, in the order the grid shows them.
 */
import { toggled } from './copySelection';

export class ImageSelection {
	active = $state(false);
	#selected = $state(new Set<string>());
	#anchor: string | null = null;
	#order: () => string[];

	/** `order` is the grid's images, as their hashes. */
	constructor(order: () => string[]) {
		this.#order = order;
	}

	get count(): number {
		return this.#selected.size;
	}

	/** The selected hashes, in grid order. */
	get hashes(): string[] {
		return this.#order().filter((h) => this.#selected.has(h));
	}

	has(hash: string): boolean {
		return this.#selected.has(hash);
	}

	start(): void {
		this.active = true;
	}

	/** Stop selecting and forget the selection. */
	stop(): void {
		this.active = false;
		this.#selected = new Set();
		this.#anchor = null;
	}

	/** Toggle `hash`, or with `range` select up to it; starts selecting. */
	click(hash: string, { range = false }: { range?: boolean } = {}): void {
		this.active = true;
		const order = this.#order();
		const from = this.#anchor === null ? -1 : order.indexOf(this.#anchor);
		const to = order.indexOf(hash);
		if (range && from >= 0 && to >= 0) {
			const [lo, hi] = from < to ? [from, to] : [to, from];
			this.#selected = new Set([...this.#selected, ...order.slice(lo, hi + 1)]);
		} else {
			this.#selected = toggled(this.#selected, hash);
		}
		this.#anchor = hash;
	}
}
