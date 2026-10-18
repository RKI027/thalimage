import { describe, expect, it } from 'vitest';
import type { ComparedImage } from './comparison';
import { groupAround, nextGroup, pickReference, ReviewSession } from './review.svelte';
import type { ImageSummary } from './types';

function image(name: string, width = 100, height = 100, file_size = 1000): ComparedImage {
	return {
		detail: { content_hash: name, filename: `${name}.png`, width, height, file_size },
		copies: [],
		tags: []
	} as unknown as ComparedImage;
}

const keys = (images: ComparedImage[]) => images.map((i) => i.detail.content_hash);

describe('pickReference', () => {
	it('takes the most pixels, then the largest file, then the first', () => {
		expect(pickReference([image('a'), image('b', 200, 100), image('c', 100, 200)])).toBe(1);
		expect(pickReference([image('a'), image('b', 100, 100, 2000)])).toBe(1);
		expect(pickReference([image('a'), image('b')])).toBe(0);
	});
});

describe('ReviewSession', () => {
	const group = () => [image('a'), image('b', 200, 200), image('c'), image('d')];

	it('starts on the reference and the first other image', () => {
		const s = new ReviewSession(group());

		expect(s.reference.detail.content_hash).toBe('b');
		expect(s.current.detail.content_hash).toBe('a');
		expect(keys(s.others)).toEqual(['a', 'c', 'd']);
	});

	it('steps through the other images, round', () => {
		const s = new ReviewSession(group());

		s.next();
		s.next();
		expect(s.current.detail.content_hash).toBe('d');
		s.next();
		expect(s.current.detail.content_hash).toBe('a');
		s.previous();
		expect(s.current.detail.content_hash).toBe('d');
	});

	it('shows any other image as the current one, never the reference', () => {
		const s = new ReviewSession(group());

		s.show('d');
		expect(s.current.detail.content_hash).toBe('d');
		s.show('b');
		expect(s.current.detail.content_hash).toBe('d');
	});

	it('makes the current image the reference, the reference becoming current', () => {
		const s = new ReviewSession(group());
		s.next();

		s.makeReference();

		expect(s.reference.detail.content_hash).toBe('c');
		expect(s.current.detail.content_hash).toBe('b');
	});

	it('flags the current image, the same flag again clearing it', () => {
		const s = new ReviewSession(group());

		s.flag('delete');
		expect(s.flagOf('a')).toBe('delete');
		s.flag('archive');
		expect(s.flagOf('a')).toBe('archive');
		s.flag('archive');
		expect(s.flagOf('a')).toBeUndefined();
	});

	it('flags the reference to archive or delete, never to merge', () => {
		const s = new ReviewSession(group());

		s.flag('archive', 'reference');
		expect(s.flagOf('b')).toBe('archive');
		expect(s.flag('merge', 'reference')).toBe(false);
		expect(s.flagOf('b')).toBe('archive');
	});

	it('drops a merge flag on an image made the reference', () => {
		const s = new ReviewSession(group());
		s.flag('merge');

		s.makeReference();

		expect(s.flagOf('a')).toBeUndefined();
	});

	it('undoes the flags one by one', () => {
		const s = new ReviewSession(group());
		s.flag('delete');
		s.next();
		s.flag('merge');
		s.flag('archive');

		s.undo();
		expect(s.flagOf('c')).toBe('merge');
		s.undo();
		s.undo();
		expect(s.flagOf('c')).toBeUndefined();
		expect(s.flagOf('a')).toBeUndefined();
	});

	it('plans the flags by action, in group order', () => {
		const s = new ReviewSession(group());
		s.next();
		s.flag('merge');
		s.previous();
		s.flag('merge');
		s.next();
		s.next();
		s.flag('delete');

		expect(s.plan).toEqual({ reference: 'b', merge: ['a', 'c'], archive: [], delete: ['d'] });
		expect(s.problem).toBeNull();
	});

	it('will not delete the reference while images merge into it', () => {
		const s = new ReviewSession(group());
		s.flag('merge');
		s.flag('delete', 'reference');

		expect(s.problem).toMatch(/reference/);
	});
});

describe('nextGroup', () => {
	const listed = (content_hash: string, duplicate_group: number) =>
		({ content_hash, duplicate_group }) as unknown as ImageSummary;

	it('takes the images of the group listed after this one', () => {
		const after = [listed('c', 1), listed('d', 2), listed('e', 2), listed('f', 3)];

		expect(nextGroup(after, ['a', 'b', 'c'])).toEqual(['d', 'e']);
	});

	it('is empty past the last group', () => {
		expect(nextGroup([listed('c', 1)], ['a', 'b', 'c'])).toEqual([]);
	});
});

describe('groupAround', () => {
	const listed = (content_hash: string, duplicate_group?: number | null) =>
		({ content_hash, duplicate_group }) as unknown as ImageSummary;

	it('takes the images of the group the image shown is in, in listing order', () => {
		const window = [listed('a', 0), listed('b', 1), listed('c', 1), listed('d', 1), listed('e', 2)];

		expect(groupAround(window, 2)).toEqual(['b', 'c', 'd']);
	});

	it('is empty for an image in no group', () => {
		expect(groupAround([listed('a', 0), listed('b', null)], 1)).toEqual([]);
		expect(groupAround([listed('a')], 0)).toEqual([]);
	});
});
