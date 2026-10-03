/** The Settings link, carrying the page to return to (none from Settings itself). */
export function settingsHref(url: URL): string {
	if (url.pathname === '/settings') return '/settings';
	return `/settings?returnTo=${encodeURIComponent(url.pathname + url.search)}`;
}
