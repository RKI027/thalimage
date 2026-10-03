import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { attachSwipe } from './swipe';

// jsdom has no PointerEvent; a MouseEvent carrying pointerId is enough here.
function pointer(type: string, x: number, y: number, target: Element, id = 1): void {
	const e = new MouseEvent(type, { clientX: x, clientY: y, bubbles: true });
	Object.defineProperty(e, 'pointerId', { value: id });
	target.dispatchEvent(e);
}

function gesture(el: Element, from: [number, number], to: [number, number], ms = 100, target = el) {
	pointer('pointerdown', ...from, target);
	vi.advanceTimersByTime(ms);
	pointer('pointerup', ...to, target);
}

describe('attachSwipe', () => {
	let el: HTMLElement;
	const h = {
		onSwipeLeft: vi.fn(),
		onSwipeRight: vi.fn(),
		onSwipeDown: vi.fn(),
		onTap: vi.fn()
	};

	beforeEach(() => {
		vi.useFakeTimers();
		el = document.createElement('div');
		document.body.append(el);
		Object.values(h).forEach((f) => f.mockClear());
	});
	afterEach(() => {
		vi.useRealTimers();
		el.remove();
	});

	it('classifies horizontal swipes past the threshold', () => {
		attachSwipe(el, h);
		gesture(el, [200, 100], [100, 110]);
		gesture(el, [100, 100], [200, 90]);
		expect(h.onSwipeLeft).toHaveBeenCalledOnce();
		expect(h.onSwipeRight).toHaveBeenCalledOnce();
	});

	it('ignores movement under the threshold, and taps on near-zero movement', () => {
		attachSwipe(el, h);
		gesture(el, [100, 100], [140, 100]);
		gesture(el, [100, 100], [104, 103]);
		expect(h.onSwipeLeft).not.toHaveBeenCalled();
		expect(h.onSwipeRight).not.toHaveBeenCalled();
		expect(h.onTap).toHaveBeenCalledOnce();
	});

	it('honours a custom threshold', () => {
		attachSwipe(el, h, { threshold: 30 });
		gesture(el, [100, 100], [100, 140]);
		expect(h.onSwipeDown).toHaveBeenCalledOnce();
	});

	it('drops gestures slower than maxDuration', () => {
		attachSwipe(el, h);
		gesture(el, [200, 100], [50, 100], 600);
		expect(h.onSwipeLeft).not.toHaveBeenCalled();
	});

	it('classifies a diagonal flick by its dominant axis', () => {
		attachSwipe(el, h);
		gesture(el, [200, 100], [80, 170]);
		expect(h.onSwipeLeft).toHaveBeenCalledOnce();
		expect(h.onSwipeDown).not.toHaveBeenCalled();
	});

	it('leaves gestures that start on a control to the control', () => {
		const button = document.createElement('button');
		el.append(button);
		attachSwipe(el, h);
		gesture(el, [200, 100], [50, 100], 100, button);
		expect(h.onSwipeLeft).not.toHaveBeenCalled();
	});

	it('stops listening after cleanup', () => {
		const detach = attachSwipe(el, h);
		detach();
		gesture(el, [200, 100], [50, 100]);
		expect(h.onSwipeLeft).not.toHaveBeenCalled();
	});
});
