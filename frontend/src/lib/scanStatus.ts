import type { ScanProgress } from './types';

/** "Done: 3 added, 10 skipped, 0 errors", then the files renamed and the sidecar counts if any is not zero. */
export function scanDoneMessage(p: ScanProgress): string {
	const renamed = p.renamed ? `, ${p.renamed} renamed` : '';
	const files = `Done: ${p.added} added, ${p.skipped} skipped, ${p.errors} errors${renamed}`;
	if (!(p.sidecars_added || p.sidecars_changed || p.sidecars_removed)) return files;
	return `${files}; sidecars: ${p.sidecars_added} added, ${p.sidecars_changed} changed, ${p.sidecars_removed} removed`;
}
