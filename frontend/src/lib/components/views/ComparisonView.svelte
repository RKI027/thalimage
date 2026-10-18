<script lang="ts">
	import { previewUrl } from '$lib/api';
	import {
		comparisonRows,
		nextMode,
		type ComparedImage,
		type CompareMode,
		type OverlayKind
	} from '$lib/comparison';
	import { isTextEntry } from '$lib/keys';
	import { isVideoFilename } from '$lib/media';
	import ImagePanel from './ImagePanel.svelte';

	/**
	 * A reference image and the current one, side by side, one at a time or
	 * overlaid, over their metadata lined up. Answers M (next view), T (the
	 * other image, when toggling), O (blend or wipe) and a held Space (the
	 * reference alone).
	 */
	let {
		reference,
		current,
		mode = $bindable('side')
	}: {
		reference: ComparedImage;
		current: ComparedImage;
		mode?: CompareMode;
	} = $props();

	let overlayKind: OverlayKind = $state('blend');
	// How much of the current image shows (blend), or where the divider
	// stands (wipe), in percent.
	let amount = $state(50);
	let showingCurrent = $state(true);
	let holdingReference = $state(false);

	const canOverlay = $derived(
		!isVideoFilename(reference.detail.filename) && !isVideoFilename(current.detail.filename)
	);
	const rows = $derived(comparisonRows(reference, current));
	const single = $derived(holdingReference || !showingCurrent ? reference : current);

	$effect(() => {
		if (mode === 'overlay' && !canOverlay) mode = 'side';
	});

	function onKeydown(e: KeyboardEvent) {
		if (isTextEntry(e.target)) return;
		if (e.key === 'm') {
			mode = nextMode(mode, canOverlay);
		} else if (e.key === 't' && mode === 'toggle') {
			showingCurrent = !showingCurrent;
		} else if (e.key === 'o' && mode === 'overlay') {
			overlayKind = overlayKind === 'blend' ? 'wipe' : 'blend';
		} else if (e.key === ' ' && mode !== 'side') {
			e.preventDefault();
			holdingReference = true;
		}
	}

	function onKeyup(e: KeyboardEvent) {
		if (e.key === ' ') holdingReference = false;
	}
</script>

<svelte:window onkeydown={onKeydown} onkeyup={onKeyup} onblur={() => (holdingReference = false)} />

<div class="comparison">
	<div class="controls">
		<div class="modes" role="group" aria-label="View">
			<button class="control" class:active={mode === 'side'} onclick={() => (mode = 'side')}>Side by side</button>
			<button class="control" class:active={mode === 'toggle'} onclick={() => (mode = 'toggle')}>Toggle</button>
			<button
				class="control"
				class:active={mode === 'overlay'}
				disabled={!canOverlay}
				title={canOverlay ? '' : 'Videos cannot be overlaid'}
				onclick={() => (mode = 'overlay')}
			>
				Overlay
			</button>
		</div>
		{#if mode === 'toggle'}
			<button class="control" onclick={() => (showingCurrent = !showingCurrent)} title="Show the other image (T)">
				Showing {single === reference ? 'reference' : 'current'}
			</button>
		{:else if mode === 'overlay'}
			<div class="modes" role="group" aria-label="Overlay" title="Blend or wipe (O)">
				<button class="control" class:active={overlayKind === 'blend'} onclick={() => (overlayKind = 'blend')}>
					Blend
				</button>
				<button class="control" class:active={overlayKind === 'wipe'} onclick={() => (overlayKind = 'wipe')}>
					Wipe
				</button>
			</div>
			<input
				class="amount"
				type="range"
				min="0"
				max="100"
				bind:value={amount}
				aria-label={overlayKind === 'blend' ? 'Current image opacity' : 'Divider position'}
			/>
		{/if}
		<span class="hint">M view{mode !== 'side' ? ' · hold Space: reference' : ''}</span>
	</div>

	<div class="pictures">
		{#if mode === 'side'}
			<figure>
				<ImagePanel hash={reference.detail.content_hash} filename={reference.detail.filename} />
				<figcaption>Reference</figcaption>
			</figure>
			<div class="divider"></div>
			<figure>
				<ImagePanel hash={current.detail.content_hash} filename={current.detail.filename} />
				<figcaption>Current</figcaption>
			</figure>
		{:else if mode === 'toggle'}
			<figure>
				<ImagePanel hash={single.detail.content_hash} filename={single.detail.filename} />
				<figcaption>{single === reference ? 'Reference' : 'Current'}</figcaption>
			</figure>
		{:else}
			<figure class="overlay">
				<div class="frame" style="--ratio: {reference.detail.width / reference.detail.height}">
					<img src={previewUrl(reference.detail.content_hash)} alt={reference.detail.filename} />
					{#if !holdingReference}
						<img
							class="top"
							src={previewUrl(current.detail.content_hash)}
							alt={current.detail.filename}
							style={overlayKind === 'blend' ? `opacity: ${amount / 100}` : `clip-path: inset(0 0 0 ${amount}%)`}
						/>
						{#if overlayKind === 'wipe'}
							<div class="wipe-line" style="left: {amount}%"></div>
						{/if}
					{/if}
				</div>
				<figcaption>
					{holdingReference ? 'Reference' : overlayKind === 'blend' ? `Current at ${amount}%` : 'Reference | Current'}
				</figcaption>
			</figure>
		{/if}
	</div>

	<div class="metadata">
	<table>
		<thead>
			<tr><th></th><th>Reference</th><th>Current</th></tr>
		</thead>
		<tbody>
			{#each rows as row (row.label)}
				<tr class:differs={row.differs}>
					<th scope="row">{row.label}</th>
					<td>{row.reference}</td>
					<td>{row.current}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	</div>
</div>

<style>
	.comparison {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
		gap: 8px;
	}

	.controls {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		padding: 0 8px;
	}

	.modes {
		display: flex;
		gap: 4px;
	}

	.control.active {
		border-color: #6ea8fe;
		color: #fff;
	}

	.amount {
		width: 160px;
	}

	.hint {
		margin-left: auto;
		color: #777;
		font-size: 0.75rem;
	}

	.pictures {
		flex: 1;
		display: flex;
		min-height: 0;
	}

	figure {
		position: relative;
		flex: 1;
		display: flex;
		min-width: 0;
		min-height: 0;
		margin: 0;
	}

	figcaption {
		position: absolute;
		top: 8px;
		left: 8px;
		padding: 2px 6px;
		border-radius: 3px;
		background: rgba(0, 0, 0, 0.6);
		color: #ccc;
		font-size: 0.75rem;
		pointer-events: none;
	}

	.divider {
		width: 2px;
		background: #333;
		flex-shrink: 0;
	}

	.overlay {
		align-items: center;
		justify-content: center;
		background: #000;
		container-type: size;
	}

	/* The reference's shape, as large as the pane allows: the blend and the
	   wipe are measured on the picture, not on the bars around it. */
	.frame {
		position: relative;
		width: min(100cqw, 100cqh * var(--ratio));
		aspect-ratio: var(--ratio);
	}

	/* Both pictures fitted to the same frame, the current one on top. */
	.overlay img {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: contain;
	}

	.wipe-line {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 2px;
		margin-left: -1px;
		background: #c9a35b;
		pointer-events: none;
	}

	.metadata {
		flex-shrink: 0;
		max-height: 30vh;
		overflow-y: auto;
		padding: 0 8px 8px;
	}

	/* Fixed columns that wrap, so a long path cannot push the current
	   image's column off a narrow screen. */
	.metadata table {
		width: 100%;
		table-layout: fixed;
		border-collapse: collapse;
		font-size: 0.8rem;
	}

	.metadata th:first-child {
		width: 6.5em;
	}

	.metadata th,
	.metadata td {
		padding: 2px 12px 2px 0;
		text-align: left;
		vertical-align: top;
		white-space: pre-line;
		overflow-wrap: anywhere;
		color: #aaa;
	}

	.metadata thead th {
		color: #777;
		font-weight: normal;
	}

	.metadata tr.differs td {
		color: #c9a35b;
	}

	@media (max-width: 768px) {
		.pictures {
			flex-direction: column;
		}

		.divider {
			width: 100%;
			height: 2px;
		}

		.hint {
			display: none;
		}
	}
</style>
