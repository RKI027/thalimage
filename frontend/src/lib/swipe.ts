export interface SwipeHandlers {
	onSwipeLeft?: () => void;
	onSwipeRight?: () => void;
	onSwipeDown?: () => void;
	onTap?: () => void;
}

export interface SwipeOptions {
	/** Minimum px to count as a swipe. Default: 50 */
	threshold?: number;
	/** Max vertical drift allowed for a horizontal swipe (and vice versa). Default: 80 */
	maxVertical?: number;
	/** Max ms elapsed; slower gestures are ignored. Default: 500 */
	maxDuration?: number;
}

/**
 * Attach pointer-event swipe and tap detection to an element.
 * Returns a cleanup function that removes all added listeners.
 */
export function attachSwipe(
	el: HTMLElement,
	handlers: SwipeHandlers,
	options: SwipeOptions = {}
): () => void {
	const threshold = options.threshold ?? 50;
	const maxVertical = options.maxVertical ?? 80;
	const maxDuration = options.maxDuration ?? 500;

	let startX = 0;
	let startY = 0;
	let startTime = 0;

	function onDown(e: PointerEvent) {
		startX = e.clientX;
		startY = e.clientY;
		startTime = Date.now();
	}

	function onUp(e: PointerEvent) {
		const dx = e.clientX - startX;
		const dy = e.clientY - startY;
		const elapsed = Date.now() - startTime;

		// Tap: almost no movement
		if (Math.abs(dx) < 10 && Math.abs(dy) < 10) {
			handlers.onTap?.();
			return;
		}

		// Too slow — treat as a drag, not a swipe
		if (elapsed > maxDuration) return;

		// Horizontal swipe
		if (Math.abs(dx) > threshold && Math.abs(dy) < maxVertical) {
			if (dx < 0) handlers.onSwipeLeft?.();
			else handlers.onSwipeRight?.();
			return;
		}

		// Downward swipe
		if (dy > threshold && Math.abs(dx) < maxVertical) {
			handlers.onSwipeDown?.();
		}
	}

	el.addEventListener('pointerdown', onDown, { passive: true });
	el.addEventListener('pointerup', onUp, { passive: true });

	return () => {
		el.removeEventListener('pointerdown', onDown);
		el.removeEventListener('pointerup', onUp);
	};
}
