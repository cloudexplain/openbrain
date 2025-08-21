<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { DocumentReference } from '$lib/api';
	
	const dispatch = createEventDispatcher();
	
	export let references: DocumentReference[] = [];
	
	let isExpanded = false;
	
	function getSourceIcon(sourceType: string) {
		switch (sourceType) {
			case 'chat':
				return '💬';
			case 'file':
				return '📄';
			case 'url':
				return '🌐';
			default:
				return '📋';
		}
	}
	
	function formatSimilarity(similarity: number): string {
		return `${(similarity * 100).toFixed(1)}%`;
	}
	
	function handleViewDocument(docId: string) {
		dispatch('viewDocument', { id: docId });
	}
</script>

{#if references && references.length > 0}
	<div class="mt-3 border-t border-gray-200 pt-3">
		<button
			on:click={() => isExpanded = !isExpanded}
			class="flex items-center justify-between w-full text-left p-2 hover:bg-gray-50 rounded-lg transition-colors"
		>
			<div class="flex items-center gap-2 text-sm text-gray-600">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
				<span>Referenced {references.length} document{references.length !== 1 ? 's' : ''}</span>
			</div>
			<svg 
				class="w-4 h-4 text-gray-400 transition-transform {isExpanded ? 'rotate-180' : ''}" 
				fill="none" 
				stroke="currentColor" 
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>
		
		{#if isExpanded}
			<div class="mt-2 space-y-2">
				{#each references as ref}
					<div class="bg-gray-50 rounded-lg p-3 border border-gray-200">
						<div class="flex items-start justify-between gap-2">
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1">
									<span class="text-lg">{getSourceIcon(ref.source_type)}</span>
									<h4 class="font-medium text-gray-900 text-sm truncate" title={ref.title}>
										{ref.title}
									</h4>
								</div>
								
								<div class="flex items-center gap-4 text-xs text-gray-500">
									<span class="capitalize">{ref.source_type}</span>
									<span>{ref.chunk_count} chunk{ref.chunk_count !== 1 ? 's' : ''} used</span>
									<span>Max: {formatSimilarity(ref.max_similarity)}</span>
									<span>Avg: {formatSimilarity(ref.avg_similarity)}</span>
								</div>
								
								{#if ref.tags && ref.tags.length > 0}
									<div class="flex flex-wrap gap-1 mt-2">
										{#each ref.tags.slice(0, 3) as tag}
											<span 
												class="inline-flex items-center px-2 py-0.5 text-xs rounded-full"
												style="background-color: {tag.color}20; color: {tag.color}; border: 1px solid {tag.color}40"
											>
												{tag.name}
											</span>
										{/each}
										{#if ref.tags.length > 3}
											<span class="text-xs text-gray-400 px-1">
												+{ref.tags.length - 3} more
											</span>
										{/if}
									</div>
								{/if}
							</div>
							
							<button
								on:click={() => handleViewDocument(ref.id)}
								class="flex-shrink-0 p-1 hover:bg-gray-200 rounded transition-colors"
								title="View document"
							>
								<svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
								</svg>
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	.rotate-180 {
		transform: rotate(180deg);
	}
</style>