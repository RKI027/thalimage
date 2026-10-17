<script lang="ts">
	import { copyPath, readOnlySources } from '$lib/imageCopies';
	import type { ImageCopy } from '$lib/types';
	import ConfirmDialog from './ConfirmDialog.svelte';

	/**
	 * Confirms deleting images from disk: lists every copy with its sidecars,
	 * or, when a copy is in a source that is not writable, those sources and
	 * no way to go ahead. `message` reports what went wrong last time.
	 */
	let {
		images,
		copies,
		message,
		onconfirm,
		oncancel
	}: {
		images: number;
		copies: ImageCopy[];
		message: string;
		onconfirm: () => void;
		oncancel: () => void;
	} = $props();

	const readOnly = $derived(readOnlySources(copies));
	const one = $derived(images === 1);
</script>

<ConfirmDialog
	open
	title={one ? 'Delete this image from disk?' : `Delete ${images} images from disk?`}
	confirmLabel="Delete {copies.length} {copies.length === 1 ? 'file' : 'files'} permanently"
	danger
	canConfirm={copies.length > 0 && readOnly.length === 0}
	{onconfirm}
	{oncancel}
>
	{#if message}
		<p class="confirm-message">{message}</p>
	{/if}
	{#if readOnly.length > 0}
		<p>
			Some copies are in sources Thalimage may not change. To delete {one ? 'the image' : 'these images'},
			mark {readOnly.length === 1 ? 'this source' : 'these sources'} writable in Settings first:
		</p>
		<ul class="file-list">
			{#each readOnly as folder (folder)}
				<li>{folder}</li>
			{/each}
		</ul>
	{:else if copies.length > 0}
		<p>
			Every copy below will be removed from the disk, with its sidecars. This cannot be undone.
			{#if one}
				The image leaves the gallery; its tags, scores, votes and collections are kept, and come
				back if the same file is scanned again.
			{:else}
				The images leave the gallery; their tags, scores, votes and collections are kept, and come
				back if the same files are scanned again.
			{/if}
		</p>
	{/if}
	<ul class="file-list">
		{#each copies as copy (copyPath(copy))}
			<li>
				{copyPath(copy)}
				{#each copy.sidecars as sidecar (sidecar)}
					<div class="file-note">+ {copyPath({ ...copy, relative_path: sidecar })}</div>
				{/each}
			</li>
		{/each}
	</ul>
</ConfirmDialog>

<style>
	.confirm-message {
		color: #f88;
	}

	.file-note {
		color: #888;
	}

	.file-list {
		margin: 8px 0;
		padding-left: 18px;
		font-family: monospace;
		font-size: 0.8rem;
	}
</style>
