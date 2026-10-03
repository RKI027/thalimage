import { describe, expect, it } from 'vitest';
import { settingsHref } from './settingsLink';

describe('settingsHref', () => {
	it('returns to the current page, query included', () => {
		expect(settingsHref(new URL('http://x/collections/3?sort=name'))).toBe(
			'/settings?returnTo=%2Fcollections%2F3%3Fsort%3Dname'
		);
	});

	it('does not point Settings back at itself', () => {
		expect(settingsHref(new URL('http://x/settings?returnTo=%2F'))).toBe('/settings');
	});
});
