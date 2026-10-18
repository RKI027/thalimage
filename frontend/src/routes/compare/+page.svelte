<script lang="ts">
	import { page } from '$app/stores';
	import { loadCompared, type ComparedImage, type CompareMode } from '$lib/comparison';
	import { isTextEntry } from '$lib/keys';
	import ComparisonView from '$lib/components/views/ComparisonView.svelte';

	// Two images compared, keyed by the query: `reference` and `current`.
	let reference: ComparedImage | null = $state(null);
	let current: ComparedImage | null = $state(null);
	let mode: CompareMode = $state('side');
	let error: string | null = $state(null);

	$effect(() => {
		const params = $page.url.searchParams;
		const keys = [params.get('reference'), params.get('current')];
		if (!keys[0] || !keys[1]) {
			error = 'Two images are needed to compare';
			return;
		}
		error = null;
		Promise.all(keys.map((k) => loadCompared(k as string)))
			.then(([r, c]) => {
				reference = r;
				current = c;
			})
			.catch((e) => (error = e instanceof Error ? e.message : 'Failed to load the images'));
	});

	function swap() {
		[reference, current] = [current, reference];
	}

	function back() {
		if (history.length > 1) history.back();
		else location.assign('/');
	}

	function onKeydown(e: KeyboardEvent) {
		if (isTextEntry(e.target)) return;
		if (e.key === 'x') swap();
		else if (e.key === 'Escape') {
			e.preventDefault();
			back();
		}
	}
</script>

<svelte:head><title>Compare — Thalimage</title></svelte:head>
<svelte:window onkeydown={onKeydown} />

<div class="compare-page">
	<div class="top-bar">
		<a
			href="/"
			onclick={(e) => {
				e.preventDefault();
				back();
			}}>← Back</a
		>
		<button class="control" onclick={swap} disabled={!reference} title="Make the current image the reference (X)">
			Swap
		</button>
	</div>
	{#if error}
		<div class="status">{error}</div>
	{:else if reference && current}
		<ComparisonView {reference} {current} bind:mode />
	{:else}
		<div class="status">Loading…</div>
	{/if}
</div>

<style>
	.compare-page {
		display: flex;
		flex-direction: column;
		height: 100%;
		gap: 8px;
	}

	.top-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: calc(8px + env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) 8px
			max(16px, env(safe-area-inset-left));
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	.status {
		padding: 24px;
		color: #888;
	}
</style>
