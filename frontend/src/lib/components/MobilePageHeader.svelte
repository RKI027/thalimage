<script lang="ts">
	import { mobileStore } from '$lib/mobileStore.svelte';

	let {
		leftType = 'hamburger',
		backHref = '/',
		title = '',
		onMenuOpen
	}: {
		leftType?: 'hamburger' | 'back';
		backHref?: string;
		title?: string;
		onMenuOpen?: () => void;
	} = $props();
</script>

<div class="mobile-header">
	{#if leftType === 'hamburger'}
		<button class="header-btn" onclick={mobileStore.open} aria-label="Open menu">☰</button>
	{:else}
		<a class="header-btn back-btn" href={backHref} aria-label="Go back">←</a>
	{/if}

	<h1 class="header-title">{title}</h1>

	{#if onMenuOpen}
		<button class="header-btn" onclick={onMenuOpen} aria-label="More options">⋮</button>
	{:else}
		<div class="header-btn-placeholder"></div>
	{/if}
</div>

<style>
	.mobile-header {
		display: flex;
		align-items: center;
		height: 48px;
		padding: env(safe-area-inset-top) max(4px, env(safe-area-inset-right)) 0
			max(4px, env(safe-area-inset-left));
		background: #1a1a1a;
		border-bottom: 1px solid #333;
		flex-shrink: 0;
	}

	.header-title {
		flex: 1;
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: #eee;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		padding: 0 8px;
	}

	.header-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 44px;
		min-height: 44px;
		background: none;
		border: none;
		color: #eee;
		font-size: 1.2rem;
		cursor: pointer;
		text-decoration: none;
		flex-shrink: 0;
	}

	.header-btn:hover {
		color: #fff;
		text-decoration: none;
	}

	.back-btn {
		font-size: 1.4rem;
	}

	.header-btn-placeholder {
		min-width: 44px;
		flex-shrink: 0;
	}
</style>
