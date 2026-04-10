<script lang="ts">
	import type { ImageDetail } from '$lib/types';

	let { image, open = true }: { image: ImageDetail; open?: boolean } = $props();

	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function tryParseJSON(s: string | null): Record<string, unknown> | null {
		if (!s) return null;
		try {
			return JSON.parse(s);
		} catch {
			return null;
		}
	}
</script>

<aside class="panel" class:collapsed={!open}>
	<button class="toggle" onclick={() => (open = !open)}>
		{open ? '▶' : '◀'} Metadata
	</button>

	{#if open}
		<div class="content">
			<section>
				<h3>File</h3>
				<dl>
					<dt>Name</dt><dd>{image.filename}</dd>
					<dt>Size</dt><dd>{formatSize(image.file_size)}</dd>
					<dt>Format</dt><dd>{image.format}</dd>
					<dt>Dimensions</dt><dd>{image.width} × {image.height}</dd>
					<dt>Aspect</dt><dd>{image.aspect_ratio.toFixed(2)}</dd>
					<dt>Modified</dt><dd>{new Date(image.file_modified).toLocaleString()}</dd>
					{#if image.file_created}
						<dt>Created</dt><dd>{new Date(image.file_created).toLocaleString()}</dd>
					{/if}
				</dl>
			</section>

			{#if image.ai_tool || image.prompt}
				<section>
					<h3>AI Parameters</h3>
					<dl>
						{#if image.ai_tool}
							<dt>Tool</dt><dd>{image.ai_tool}</dd>
						{/if}
						{#if image.prompt}
							<dt>Prompt</dt><dd class="wrap">{image.prompt}</dd>
						{/if}
						{#if image.negative_prompt}
							<dt>Negative</dt><dd class="wrap">{image.negative_prompt}</dd>
						{/if}
						{#if image.raw_params}
							<dt>Params</dt><dd class="wrap mono">{image.raw_params}</dd>
						{/if}
					</dl>
				</section>
			{/if}

			{#if image.png_text}
				{@const parsed = tryParseJSON(image.png_text)}
				{#if parsed}
					<section>
						<h3>PNG Text</h3>
						<dl>
							{#each Object.entries(parsed) as [key, val]}
								<dt>{key}</dt><dd class="wrap">{val}</dd>
							{/each}
						</dl>
					</section>
				{/if}
			{/if}
		</div>
	{/if}
</aside>

<style>
	.panel {
		width: 320px;
		background: #1a1a1a;
		border-left: 1px solid #333;
		overflow-y: auto;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
	}

	.panel.collapsed {
		width: auto;
	}

	.toggle {
		background: #2a2a2a;
		border: none;
		color: #ccc;
		padding: 8px 12px;
		cursor: pointer;
		text-align: left;
		border-bottom: 1px solid #333;
	}

	.toggle:hover {
		background: #3a3a3a;
	}

	.content {
		padding: 12px;
		overflow-y: auto;
	}

	section {
		margin-bottom: 16px;
	}

	h3 {
		margin: 0 0 8px;
		font-size: 0.85rem;
		color: #6ea8fe;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	dl {
		margin: 0;
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 4px 12px;
		font-size: 0.85rem;
	}

	dt {
		color: #888;
		white-space: nowrap;
	}

	dd {
		margin: 0;
		color: #ccc;
		word-break: break-word;
	}

	.wrap {
		white-space: pre-wrap;
		max-height: 200px;
		overflow-y: auto;
	}

	.mono {
		font-family: monospace;
		font-size: 0.8rem;
	}
</style>
