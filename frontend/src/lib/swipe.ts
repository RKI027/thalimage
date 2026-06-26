export interface SwipeHandlers {
	onSwipeLeft?: () => void;
	onSwipeRight?: () => void;
	onSwipeDown?: () => void;
	onTap?: () => void;
}

export interface SwipeOptions {
	/** Minimum px to count as a swipe. Default: 50 */
	threshold?: number;
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
	const maxDuration = options.maxDuration ?? 500;

	let startX = 0;
	let startY = 0;
	let startTime = 0;
	let activePointer: number | null = null;

	function onDown(e: PointerEvent) {
		// Ignore secondary touches (e.g. pinch) once a gesture is in progress.
		if (activePointer !== null) return;
		activePointer = e.pointerId;
		startX = e.clientX;
		startY = e.clientY;
		startTime = Date.now();
		// Keep receiving events even if the pointer leaves the element.
		try {
			el.setPointerCapture(e.pointerId);
		} catch {
			// Capture is best-effort; ignore if unsupported.
		}
	}

	function onCancel(e: PointerEvent) {
		if (e.pointerId === activePointer) activePointer = null;
	}

	function onUp(e: PointerEvent) {
		if (e.pointerId !== activePointer) return;
		activePointer = null;

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

		// Classify by the dominant axis so diagonal flicks still register as the
		// gesture the user mostly intended, rather than being dropped.
		if (Math.abs(dx) >= Math.abs(dy)) {
			if (Math.abs(dx) > threshold) {
				if (dx < 0) handlers.onSwipeLeft?.();
				else handlers.onSwipeRight?.();
			}
		} else if (dy > threshold) {
			handlers.onSwipeDown?.();
		}
	}

	el.addEventListener('pointerdown', onDown, { passive: true });
	el.addEventListener('pointerup', onUp, { passive: true });
	el.addEventListener('pointercancel', onCancel, { passive: true });

	return () => {
		el.removeEventListener('pointerdown', onDown);
		el.removeEventListener('pointerup', onUp);
		el.removeEventListener('pointercancel', onCancel);
	};
}
