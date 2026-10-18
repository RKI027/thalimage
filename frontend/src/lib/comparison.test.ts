import { describe, expect, it } from 'vitest';
import { comparisonRows, nextMode, wipeAt, type ComparedImage } from './comparison';
import type { ImageDetail } from './types';

function compared(detail: Partial<ImageDetail> = {}, extra: Partial<ComparedImage> = {}): ComparedImage {
	return {
		detail: {
			content_hash: 'a'.repeat(64),
			filename: 'a.png',
			source_id: 1,
			relative_path: 'a.png',
			width: 1024,
			height: 1536,
			aspect_ratio: 1024 / 1536,
			format: 'PNG',
			thumb_generated: true,
			archived: false,
			nsfw: false,
			file_size: 2 * 1024 * 1024,
			file_modified: '2026-01-02T03:04:05',
			file_created: null,
			ai_tool: null,
			prompt: null,
			negative_prompt: null,
			raw_params: null,
			exif_data: null,
			png_text: null,
			original_name: null,
			folder_tags: [],
			other_versions: 0,
			possible_edit: null,
			...detail
		},
		copies: [
			{ source_id: 1, source_path: '/pics', relative_path: 'a.png', writable: false, sidecars: [] }
		],
		tags: [],
		...extra
	};
}

function row(rows: ReturnType<typeof comparisonRows>, label: string) {
	const found = rows.find((r) => r.label === label);
	if (!found) throw new Error(`no ${label} row`);
	return found;
}

describe('comparisonRows', () => {
	it('lines up the two images, flagging what differs', () => {
		const rows = comparisonRows(compared(), compared({ width: 512, height: 768, format: 'WEBP' }));

		expect(row(rows, 'Dimensions')).toEqual({
			label: 'Dimensions',
			reference: '1024 × 1536',
			current: '512 × 768',
			differs: true
		});
		expect(row(rows, 'Format').differs).toBe(true);
		expect(row(rows, 'File size').differs).toBe(false);
	});

	it('tells sizes apart by their bytes, not their rounded text', () => {
		const rows = comparisonRows(compared({ file_size: 2_097_152 }), compared({ file_size: 2_097_200 }));

		expect(row(rows, 'File size').differs).toBe(true);
	});

	it('shows a missing creation date as a dash', () => {
		const rows = comparisonRows(compared(), compared({ file_created: '2026-01-01T00:00:00' }));

		expect(row(rows, 'Created').reference).toBe('—');
		expect(row(rows, 'Created').differs).toBe(true);
	});

	it('lists every file of each image, in its source', () => {
		const current = compared(
			{},
			{
				copies: [
					{ source_id: 1, source_path: '/pics', relative_path: 'b.png', writable: false, sidecars: [] },
					{ source_id: 2, source_path: '/more', relative_path: 'x/b.png', writable: true, sidecars: [] }
				]
			}
		);

		const files = row(comparisonRows(compared(), current), 'Files');

		expect(files.reference).toBe('/pics/a.png');
		expect(files.current).toBe('/pics/b.png\n/more/x/b.png');
	});

	it('compares tags whatever their order, folder tags included', () => {
		const tag = (id: number, name: string) => ({ id, name, created_at: '' });
		const rows = comparisonRows(
			compared({ folder_tags: ['folder:pics'] }, { tags: [tag(1, 'b'), tag(2, 'a')] }),
			compared({ folder_tags: ['folder:pics'] }, { tags: [tag(2, 'a'), tag(1, 'b')] })
		);

		expect(row(rows, 'Tags')).toMatchObject({ reference: 'a, b, folder:pics', differs: false });
	});
});

describe('nextMode', () => {
	it('cycles side by side, toggle, overlay', () => {
		expect(nextMode('side')).toBe('toggle');
		expect(nextMode('toggle')).toBe('overlay');
		expect(nextMode('overlay')).toBe('side');
	});

	it('skips the overlay when the two cannot be overlaid', () => {
		expect(nextMode('toggle', false)).toBe('side');
	});
});

describe('wipeAt', () => {
	it('places the divider where the pointer is, in percent of the picture', () => {
		expect(wipeAt(150, { left: 100, width: 200 })).toBe(25);
	});

	it('keeps it on the picture when the pointer leaves it', () => {
		expect(wipeAt(50, { left: 100, width: 200 })).toBe(0);
		expect(wipeAt(400, { left: 100, width: 200 })).toBe(100);
	});
});
