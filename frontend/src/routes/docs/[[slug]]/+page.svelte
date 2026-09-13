<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import { listDocs, getDoc } from '$lib/api';
	import type { DocSummary } from '$lib/types';
	import MobilePageHeader from '$lib/components/MobilePageHeader.svelte';

	let pages: DocSummary[] = $state([]);
	let html = $state('');
	let title = $state('Documentation');
	let error: string | null = $state(null);

	const slug = $derived($page.params.slug ?? '');

	onMount(async () => {
		try {
			pages = await listDocs();
		} catch {
			error = 'Could not load the documentation index.';
		}
	});

	// The bare /docs URL opens the first page rather than an empty shell.
	const current = $derived(slug || pages[0]?.slug || '');

	$effect(() => {
		const wanted = current;
		if (!wanted) return;
		let stale = false;
		getDoc(wanted)
			.then((doc) => {
				if (stale) return;
				title = doc.title;
				html = marked.parse(doc.markdown, { async: false }) as string;
				error = null;
			})
			.catch(() => {
				if (!stale) error = 'That documentation page does not exist.';
			});
		return () => {
			stale = true;
		};
	});
</script>

<svelte:head><title>{title} — Thalimage</title></svelte:head>

<MobilePageHeader leftType="back" backHref="/" title="Documentation" />

<div class="docs">
	<nav class="toc">
		<h2>Documentation</h2>
		<ul>
			{#each pages as p}
				<li>
					<a href="/docs/{p.slug}" class:active={p.slug === current}>{p.title}</a>
				</li>
			{/each}
		</ul>
	</nav>

	<article class="content">
		{#if error}
			<p class="error">{error}</p>
		{:else}
			<!-- Pages ship with the server; the Markdown is ours, not user input. -->
			{@html html}
		{/if}
	</article>
</div>

<style>
	.docs {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		overscroll-behavior-y: contain;
		display: flex;
		gap: 32px;
		padding: 24px;
		align-items: flex-start;
	}

	.toc {
		flex-shrink: 0;
		width: 200px;
		position: sticky;
		top: 24px;
	}

	.toc h2 {
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #888;
		margin: 0 0 12px;
	}

	.toc ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.toc a {
		display: block;
		padding: 8px 12px;
		color: #ccc;
		text-decoration: none;
		border-radius: 4px;
		border-left: 2px solid transparent;
		min-height: 44px;
		box-sizing: border-box;
	}

	.toc a:hover {
		background: #2a2a2a;
	}

	.toc a.active {
		color: #fff;
		background: #2a2a2a;
		border-left-color: #4a9eff;
	}

	.content {
		flex: 1;
		min-width: 0;
		max-width: 70ch;
		color: #ddd;
		line-height: 1.65;
	}

	.error {
		color: #ff6b6b;
	}

	.content :global(h1) {
		font-size: 1.75rem;
		margin: 0 0 24px;
		color: #fff;
	}

	.content :global(h2) {
		font-size: 1.2rem;
		margin: 32px 0 12px;
		color: #fff;
		border-bottom: 1px solid #333;
		padding-bottom: 6px;
	}

	.content :global(p) {
		margin: 0 0 16px;
	}

	.content :global(strong) {
		color: #fff;
	}

	.content :global(code) {
		background: #2a2a2a;
		padding: 2px 5px;
		border-radius: 3px;
		font-size: 0.9em;
	}

	.content :global(table) {
		border-collapse: collapse;
		width: 100%;
		margin: 0 0 20px;
	}

	.content :global(th),
	.content :global(td) {
		border: 1px solid #333;
		padding: 8px 12px;
		text-align: left;
	}

	.content :global(th) {
		background: #222;
		color: #fff;
	}

	.content :global(li) {
		margin-bottom: 8px;
	}

	@media (max-width: 768px) {
		.docs {
			flex-direction: column;
			padding: 12px calc(12px + env(safe-area-inset-right)) calc(24px + env(safe-area-inset-bottom))
				calc(12px + env(safe-area-inset-left));
			gap: 16px;
		}

		.toc {
			position: static;
			width: 100%;
		}

		.toc ul {
			display: flex;
			flex-wrap: wrap;
			gap: 4px;
		}
	}
</style>
