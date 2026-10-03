/**
 * Browser storage that never throws: private windows, blocked site data and
 * quota errors read as "nothing stored" and drop writes. Values are JSON.
 */

type Area = 'local' | 'session';

function area(which: Area): Storage | null {
	try {
		return which === 'local' ? localStorage : sessionStorage;
	} catch {
		return null;
	}
}

/**
 * The stored value, or `fallback` when there is none or it cannot be read.
 * Values written before these helpers existed may be bare strings ("name"
 * rather than "\"name\""); those are returned as-is when a string is expected.
 */
export function readStored<T>(key: string, fallback: T, which: Area = 'local'): T {
	let raw: string | null = null;
	try {
		raw = area(which)?.getItem(key) ?? null;
	} catch {
		return fallback;
	}
	if (raw === null) return fallback;
	try {
		return JSON.parse(raw) as T;
	} catch {
		return (typeof fallback === 'string' ? raw : fallback) as T;
	}
}

export function writeStored(key: string, value: unknown, which: Area = 'local'): void {
	try {
		area(which)?.setItem(key, JSON.stringify(value));
	} catch {
		// Storage unavailable or full: the preference just isn't kept.
	}
}

export function removeStored(key: string, which: Area = 'local'): void {
	try {
		area(which)?.removeItem(key);
	} catch {
		// ignore
	}
}
