import { describe, expect, it } from 'vitest';
import { isTextEntry } from './keys';

function element(html: string): Element {
	const host = document.createElement('div');
	host.innerHTML = html;
	return host.firstElementChild as Element;
}

describe('isTextEntry', () => {
	it('is true where keys type text', () => {
		expect(isTextEntry(element('<input>'))).toBe(true);
		expect(isTextEntry(element('<input type="number">'))).toBe(true);
		expect(isTextEntry(element('<textarea></textarea>'))).toBe(true);
		expect(isTextEntry(element('<select></select>'))).toBe(true);
		expect(isTextEntry(element('<div contenteditable="true"><b>x</b></div>').firstElementChild)).toBe(true);
	});

	it('is false on a slider, a checkbox or a button, which keep shortcuts working', () => {
		expect(isTextEntry(element('<input type="range">'))).toBe(false);
		expect(isTextEntry(element('<input type="checkbox">'))).toBe(false);
		expect(isTextEntry(element('<button></button>'))).toBe(false);
		expect(isTextEntry(null)).toBe(false);
	});
});
