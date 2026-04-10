<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getImage, listImages } from '$lib/api';
	import type { ImageDetail, ImageSummary } from '$lib/types';
	import ImageViewer from '$lib/components/ImageViewer.svelte';
	import MetadataPanel from '$lib/components/MetadataPanel.svelte';

	let image: ImageDetail | null = $state(null);
	let neighbors: ImageSummary[] = $state([]);
	let currentIndex = $state(-1);
	let error: string | null = $state(null);

	async function load(hash: string) {
		error = null;
		try {
			image = await getImage(hash);
			if (neighbors.length === 0) {
				await loadNeighbors();
			} else {
				updateIndex();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load image';
			image = null;
		}
	}

	async function loadNeighbors() {
		const pg = await listImages({ limit: 1000 });
		neighbors = pg.items;
		updateIndex();
	}

	function updateIndex() {
		if (!image) return;
		currentIndex = neighbors.findIndex((n) => n.content_hash === image!.content_hash);
	}

	function navigate(delta: number) {
		const newIndex = currentIndex + delta;
		if (newIndex >= 0 && newIndex < neighbors.length) {
			goto(`/image/${neighbors[newIndex].content_hash}`);
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowLeft') {
			e.preventDefault();
			navigate(-1);
		} else if (e.key === 'ArrowRight') {
			e.preventDefault();
			navigate(1);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			goto('/');
		}
	}

	$effect(() => {
		const hash = $page.params.hash;
		if (hash) {
			load(hash);
		}
	});

</script>

<svelte:window onkeydown={onKeydown} />

{#if error}
	<div class="error">{error}</div>
{:else if image}
	<div class="image-page">
		<div class="top-bar">
			<a href="/">← Back</a>
			<span class="filename">{image.filename}</span>
			<div class="nav-buttons">
				<button disabled={currentIndex <= 0} onclick={() => navigate(-1)}>← Prev</button>
				<span class="position">
					{#if currentIndex >= 0}
						{currentIndex + 1} / {neighbors.length}
					{/if}
				</span>
				<button
					disabled={currentIndex < 0 || currentIndex >= neighbors.length - 1}
					onclick={() => navigate(1)}
				>
					Next →
				</button>
			</div>
		</div>
		<div class="body">
			<ImageViewer
				hash={image.content_hash}
				filename={image.filename}
				width={image.width}
				height={image.height}
			/>
			<MetadataPanel {image} />
		</div>
	</div>
{:else}
	<div class="loading">Loading…</div>
{/if}

<style>
	.image-page {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.top-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 16px;
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	.filename {
		color: #ccc;
		font-size: 0.9rem;
	}

	.nav-buttons {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.nav-buttons button {
		padding: 4px 12px;
		border: 1px solid #444;
		border-radius: 4px;
		background: #2a2a2a;
		color: #ccc;
		cursor: pointer;
	}

	.nav-buttons button:hover:not(:disabled) {
		background: #3a3a3a;
	}

	.nav-buttons button:disabled {
		opacity: 0.4;
		cursor: default;
	}

	.position {
		color: #888;
		font-size: 0.85rem;
		min-width: 60px;
		text-align: center;
	}

	.body {
		flex: 1;
		display: flex;
		min-height: 0;
	}

	.error {
		padding: 32px;
		text-align: center;
		color: #f66;
	}

	.loading {
		padding: 32px;
		text-align: center;
		color: #888;
	}
</style>
