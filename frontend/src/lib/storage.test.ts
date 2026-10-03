import { afterEach, describe, expect, it, vi } from 'vitest';
import { readStored, removeStored, writeStored } from './storage';

describe('storage', () => {
	afterEach(() => {
		localStorage.clear();
		sessionStorage.clear();
	});

	it('round-trips JSON values in either area', () => {
		writeStored('n', 200);
		writeStored('f', { media_type: 'video' }, 'session');
		expect(readStored('n', 0)).toBe(200);
		expect(readStored('f', {}, 'session')).toEqual({ media_type: 'video' });
		expect(readStored('f', {})).toEqual({});
	});

	it('reads bare strings written before the helpers existed', () => {
		localStorage.setItem('sort', 'date_modified');
		localStorage.setItem('loop', 'true');
		expect(readStored('sort', 'name')).toBe('date_modified');
		expect(readStored('loop', false)).toBe(true);
	});

	it('falls back on corrupt values', () => {
		localStorage.setItem('f', '{oops');
		expect(readStored('f', { a: 1 })).toEqual({ a: 1 });
	});

	it('never throws when storage refuses', () => {
		const boom = () => {
			throw new DOMException('denied', 'SecurityError');
		};
		vi.spyOn(Storage.prototype, 'getItem').mockImplementation(boom);
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(boom);
		vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(boom);
		expect(readStored('x', 5)).toBe(5);
		expect(() => writeStored('x', 1)).not.toThrow();
		expect(() => removeStored('x')).not.toThrow();
	});
});
