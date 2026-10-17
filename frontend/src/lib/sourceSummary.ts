import { differsFromFirst } from './copySelection';
import type { SourceSummary } from './types';

export type SummaryKind = 'duplicates' | 'failures' | 'archived' | 'orphans';

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
	const differing = s.duplicates.reduce(
		(n, group) => n + group.paths.filter((p) => differsFromFirst(group, p)).length,
		0
	);
	const lines: { kind: SummaryKind; label: string }[] = [];
	if (copies > 0) {
		const versions = differing > 0 ? `, ${differing} with different metadata` : '';
		lines.push({
			kind: 'duplicates',
			label: `${count(copies, 'duplicate file', 'duplicate files')} (same picture as another file${versions})`
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
	if (s.orphans.length > 0) {
		lines.push({
			kind: 'orphans',
			label: `${count(s.orphans.length, 'orphan file', 'orphan files')} (no image or video is named after ${s.orphans.length === 1 ? 'it' : 'them'})`
		});
	}
	return lines;
}
