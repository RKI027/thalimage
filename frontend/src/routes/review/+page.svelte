<script lang="ts">
	import { get } from 'svelte/store';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { archiveImages, deleteImages, getNeighbors, mergeImages, thumbUrl } from '$lib/api';
	import { backDestination, browsingContext, contextListing, groupsNearDuplicates } from '$lib/browsingContext';
	import { loadCompared, type CompareMode } from '$lib/comparison';
	import { isTextEntry } from '$lib/keys';
	import { nextGroup, ReviewSession, type ReviewAction } from '$lib/review.svelte';
	import { settingsStore } from '$lib/stores';
	import type { ImageDeletion } from '$lib/types';
	import ComparisonView from '$lib/components/views/ComparisonView.svelte';
	import TagEditor from '$lib/components/TagEditor.svelte';

	// The images reviewed, by key in the query (`images`, comma-separated);
	// `next` when opened from a near-duplicate listing, to go on to the next
	// group from there.
	let session: ReviewSession | null = $state(null);
	let mode: CompareMode = $state('side');
	let error: string | null = $state(null);
	let following: string[] = $state([]);
	// Where leaving goes once the flags are applied or discarded; null while
	// reviewing.
	let leaving: 'back' | 'next' | null = $state(null);
	let busy = $state(false);
	let dialog: HTMLDialogElement | undefined = $state();

	const LETTERS: Record<ReviewAction, string> = { archive: 'A', merge: 'G', delete: 'D' };
	const KEYS: Record<string, ReviewAction> = { a: 'archive', g: 'merge', d: 'delete' };

	$effect(() => {
		const params = $page.url.searchParams;
		const keys = (params.get('images') ?? '').split(',').filter(Boolean);
		const fromListing = params.has('next');
		session = null;
		following = [];
		leaving = null;
		if (keys.length < 2) {
			error = 'A review needs two images or more.';
			return;
		}
		error = null;
		Promise.all(keys.map(loadCompared))
			.then((images) => (session = new ReviewSession(images)))
			.catch((e) => (error = e instanceof Error ? e.message : 'Failed to load the images'));
		if (fromListing) findNextGroup(keys).then((next) => (following = next));
	});

	$effect(() => {
		if (!dialog) return;
		if (leaving && !dialog.open) dialog.showModal();
		if (!leaving && dialog.open) dialog.close();
	});

	async function findNextGroup(reviewed: string[]): Promise<string[]> {
		const ctx = get(browsingContext);
		if (!ctx || !groupsNearDuplicates(ctx)) return [];
		try {
			await settingsStore.loaded;
			const around = await getNeighbors(reviewed[reviewed.length - 1], {
				...contextListing(ctx, get(settingsStore).show_nsfw),
				window: 50
			});
			return nextGroup(around.after, reviewed);
		} catch {
			return [];
		}
	}

	function nameOf(key: string): string {
		return session?.images.find((i) => i.detail.content_hash === key)?.detail.filename ?? key;
	}

	function filesOf(key: string): string[] {
		const image = session?.images.find((i) => i.detail.content_hash === key);
		return (image?.copies ?? []).map((c) => `${c.source_path.replace(/\/$/, '')}/${c.relative_path}`);
	}

	const hasNext = $derived(following.length >= 2);

	function go(where: 'back' | 'next') {
		leaving = null;
		if (where === 'next' && hasNext) goto(`/review?images=${following.join(',')}&next`);
		else goto(backDestination(get(browsingContext)));
	}

	/** Leave for `where`, asking first what to do with the flags. */
	function leave(where: 'back' | 'next') {
		if (session && session.flagged > 0) leaving = where;
		else go(where);
	}

	function failures(result: ImageDeletion): string[] {
		return result.failed.map((f) => `${f.relative_path}: ${f.error}`);
	}

	async function apply() {
		if (!session || session.problem || !leaving) return;
		const plan = session.plan;
		busy = true;
		error = null;
		const failed: string[] = [];
		try {
			if (plan.merge.length) failed.push(...failures(await mergeImages(plan.reference, plan.merge)));
			if (plan.archive.length) await archiveImages(plan.archive, true);
			if (plan.delete.length) failed.push(...failures(await deleteImages(plan.delete)));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Applying the flags failed';
			busy = false;
			return;
		}
		busy = false;
		if (failed.length) {
			error = `Some files could not be removed: ${failed.join('; ')}`;
			return;
		}
		go(leaving);
	}

	function onKeydown(e: KeyboardEvent) {
		if (!session || leaving || isTextEntry(e.target)) return;
		const action = KEYS[e.key.toLowerCase()];
		if (e.key === 'ArrowRight') session.next();
		else if (e.key === 'ArrowLeft') session.previous();
		else if (e.key === 'f') session.makeReference();
		else if (e.key === 'u') session.undo();
		else if (action) session.flag(action, e.shiftKey ? 'reference' : 'current');
		else if (e.key === 'n' && hasNext) leave('next');
		else if (e.key === 'Escape') leave('back');
		else return;
		e.preventDefault();
	}
</script>

<svelte:head><title>Review — Thalimage</title></svelte:head>
<svelte:window onkeydown={onKeydown} />

<div class="review-page">
	<div class="top-bar">
		<a
			href="/"
			onclick={(e) => {
				e.preventDefault();
				leave('back');
			}}>← Back</a
		>
		{#if session}
			<span class="summary">
				{session.images.length} images · {session.flagged} flagged
				<span class="hint">←/→ · F reference · A G D flag (Shift: reference) · U undo{hasNext ? ' · N next group' : ''}</span>
			</span>
		{/if}
		<div class="leave">
			{#if hasNext}
				<button class="control" onclick={() => leave('next')} title="Go on to the next near-duplicate group (N)">
					Next group
				</button>
			{/if}
			<button class="control control-primary" onclick={() => leave('back')} disabled={!session}>Done</button>
		</div>
	</div>

	{#if error && !leaving}
		<div class="status error">{error}</div>
	{/if}

	{#if session}
		<div class="strip">
			{#each session.images as image (image.detail.content_hash)}
				{@const key = image.detail.content_hash}
				{@const flag = session.flagOf(key)}
				<button
					class="thumb"
					class:reference={key === session.reference.detail.content_hash}
					class:current={key === session.current.detail.content_hash}
					class:flagged={!!flag}
					title={image.detail.filename}
					onclick={() => session?.show(key)}
				>
					<img src={thumbUrl(key)} alt={image.detail.filename} />
					{#if key === session.reference.detail.content_hash}
						<span class="badge ref">R</span>
					{/if}
					{#if flag}
						<span class="badge {flag}">{LETTERS[flag]}</span>
					{/if}
				</button>
			{/each}
		</div>

		<div class="flags">
			{#each ['archive', 'merge', 'delete'] as const as action (action)}
				<button
					class="control"
					class:active={session.flagOf(session.current.detail.content_hash) === action}
					onclick={() => session?.flag(action)}
					title="Flag the current image ({LETTERS[action]})"
				>
					{action === 'merge' ? 'Merge into reference' : action === 'archive' ? 'Archive' : 'Delete'}
				</button>
			{/each}
			<button class="control" onclick={() => session?.makeReference()} title="Make the current image the reference (F)">
				Make reference
			</button>
		</div>

		<ComparisonView reference={session.reference} current={session.current} bind:mode />

		<div class="tags">
			<span class="label">Current image's tags</span>
			<TagEditor
				hash={session.current.detail.content_hash}
				folderTags={session.current.detail.folder_tags}
				onchange={(tags) => {
					if (session) session.current.tags = tags;
				}}
			/>
		</div>
	{:else if !error}
		<div class="status">Loading…</div>
	{/if}
</div>

<dialog bind:this={dialog} oncancel={(e) => (e.preventDefault(), (leaving = null))} aria-labelledby="review-title">
	{#if session}
		{@const plan = session.plan}
		<h3 id="review-title">Apply {session.flagged} {session.flagged === 1 ? 'flag' : 'flags'}?</h3>
		<div class="body">
			{#if plan.merge.length}
				<p>Merge into <strong>{nameOf(plan.reference)}</strong>, deleting these files:</p>
				<ul>
					{#each plan.merge.flatMap(filesOf) as file (file)}<li>{file}</li>{/each}
				</ul>
			{/if}
			{#if plan.archive.length}
				<p>Archive:</p>
				<ul>
					{#each plan.archive as key (key)}<li>{nameOf(key)}</li>{/each}
				</ul>
			{/if}
			{#if plan.delete.length}
				<p>Delete from disk, every copy:</p>
				<ul>
					{#each plan.delete.flatMap(filesOf) as file (file)}<li>{file}</li>{/each}
				</ul>
			{/if}
			{#if plan.merge.length || plan.delete.length}
				<p class="warning">Deleting and merging remove files from disk; this cannot be undone.</p>
			{/if}
			{#if session.problem}
				<p class="warning">{session.problem}</p>
			{/if}
			{#if error}
				<p class="warning">{error}</p>
			{/if}
		</div>
		<div class="actions">
			<!-- svelte-ignore a11y_autofocus -->
			<button class="control" autofocus onclick={() => (leaving = null)} disabled={busy}>Keep reviewing</button>
			<button class="control" onclick={() => leaving && go(leaving)} disabled={busy}>
				Discard flags{leaving === 'next' ? ' and go on' : ''}
			</button>
			<button class="control control-danger" onclick={apply} disabled={busy || !!session.problem}>
				Apply{leaving === 'next' ? ' and go on' : ''}
			</button>
		</div>
	{/if}
</dialog>

<style>
	.review-page {
		display: flex;
		flex-direction: column;
		height: 100%;
		gap: 8px;
	}

	.top-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: calc(8px + env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) 8px
			max(16px, env(safe-area-inset-left));
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	.leave {
		display: flex;
		gap: 8px;
	}

	.summary {
		color: #888;
		font-size: 0.85rem;
	}

	.hint {
		margin-left: 12px;
		color: #666;
		font-size: 0.75rem;
	}

	.strip {
		display: flex;
		gap: 6px;
		padding: 0 8px;
		overflow-x: auto;
		flex-shrink: 0;
	}

	.thumb {
		position: relative;
		flex-shrink: 0;
		width: 64px;
		height: 64px;
		padding: 0;
		border: 2px solid transparent;
		border-radius: 4px;
		background: #1a1a1a;
		cursor: pointer;
	}

	.thumb img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		border-radius: 2px;
	}

	.thumb.current {
		border-color: #6ea8fe;
	}

	.thumb.reference {
		border-color: #c9a35b;
	}

	.thumb.flagged img {
		opacity: 0.5;
	}

	.badge {
		position: absolute;
		bottom: 2px;
		right: 2px;
		padding: 0 4px;
		border-radius: 3px;
		font-size: 0.7rem;
		font-weight: 600;
		color: #fff;
	}

	.badge.ref {
		left: 2px;
		right: auto;
		background: #8a6d2e;
	}

	.badge.archive {
		background: #3a5a8a;
	}

	.badge.merge {
		background: #2e6b4a;
	}

	.badge.delete {
		background: #8a2e2e;
	}

	.flags {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		padding: 0 8px;
	}

	.flags .control.active {
		border-color: #6ea8fe;
		color: #fff;
	}

	.tags {
		flex-shrink: 0;
		padding: 0 8px 8px;
		max-width: 480px;
	}

	.label {
		display: block;
		margin-bottom: 4px;
		color: #777;
		font-size: 0.75rem;
	}

	.status {
		padding: 24px;
		color: #888;
	}

	.error,
	.warning {
		color: #f6a84b;
	}

	dialog {
		max-width: min(640px, calc(100vw - 32px));
		padding: 20px;
		border: 1px solid #444;
		border-radius: 6px;
		background: #1e1e1e;
		color: #ddd;
	}

	dialog::backdrop {
		background: rgba(0, 0, 0, 0.6);
	}

	dialog h3 {
		margin: 0 0 12px;
	}

	.body {
		font-size: 0.9rem;
		max-height: 50vh;
		overflow-y: auto;
		overflow-wrap: anywhere;
	}

	.body ul {
		margin: 4px 0 12px;
		padding-left: 20px;
		color: #aaa;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: 8px;
		margin-top: 16px;
	}

	@media (max-width: 768px) {
		.hint {
			display: none;
		}
	}
</style>
