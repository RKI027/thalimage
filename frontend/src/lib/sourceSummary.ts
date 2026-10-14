import type { SourceSummary } from './types';

export type SummaryKind = 'duplicates' | 'failures' | 'archived';

function count(n: number, one: string, many: string): string {
	return `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`;
}

/** "1,390 files → 954 images" */
export function summaryHeadline(s: SourceSummary): string {
	return `${count(s.files, 'file', 'files')} → ${count(s.images, 'image', 'images')}`;
}

/** The reasons a source's files and images differ, one line each, only those that apply. */
export function summaryLines(s: SourceSummary): { kind: SummaryKind; label: string }[] {
	const copies = s.duplicates.reduce((n, group) => n + group.paths.length - 1, 0);
	const lines: { kind: SummaryKind; label: string }[] = [];
	if (copies > 0) {
		lines.push({
			kind: 'duplicates',
			label: `${count(copies, 'duplicate file', 'duplicate files')} (same content as another file)`
		});
	}
	if (s.failures.length > 0) {
		lines.push({
			kind: 'failures',
			label: `${count(s.failures.length, 'file', 'files')} not indexed (the last scan failed on ${s.failures.length === 1 ? 'it' : 'them'})`
		});
	}
	if (s.archived.length > 0) {
		lines.push({
			kind: 'archived',
			label: `${count(s.archived.length, 'archived image', 'archived images')} (not shown when browsing)`
		});
	}
	return lines;
}
