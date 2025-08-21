<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	
	const dispatch = createEventDispatcher();
	
	export let documentId: string | null = null;
	export let selectedTags: Tag[] = [];
	export let mode: 'display' | 'edit' = 'display';
	
	interface Tag {
		id: string;
		name: string;
		color: string;
		description?: string;
	}
	
	let allTags: Tag[] = [];
	let isLoading = false;
	let showDropdown = false;
	let searchQuery = '';
	
	onMount(async () => {
		await loadAllTags();
		if (documentId) {
			await loadDocumentTags();
		}
	});
	
	async function loadAllTags() {
		try {
			const response = await fetch('/api/v1/tags');
			if (!response.ok) throw new Error('Failed to load tags');
			
			const data = await response.json();
			allTags = data.tags;
		} catch (error) {
			console.error('Failed to load tags:', error);
		}
	}
	
	async function loadDocumentTags() {
		if (!documentId) return;
		
		isLoading = true;
		try {
			const response = await fetch(`/api/v1/documents/${documentId}/tags`);
			if (!response.ok) throw new Error('Failed to load document tags');
			
			const data = await response.json();
			selectedTags = data.tags;
		} catch (error) {
			console.error('Failed to load document tags:', error);
		} finally {
			isLoading = false;
		}
	}
	
	async function addTag(tag: Tag) {
		if (!documentId) return;
		
		// Check if tag is already selected
		if (selectedTags.some(t => t.id === tag.id)) {
			return;
		}
		
		try {
			const response = await fetch(`/api/v1/documents/${documentId}/tags`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					tag_ids: [...selectedTags.map(t => t.id), tag.id]
				})
			});
			
			if (!response.ok) throw new Error('Failed to add tag');
			
			const data = await response.json();
			selectedTags = data.tags;
			showDropdown = false;
			searchQuery = '';
			
			dispatch('change', { tags: selectedTags });
		} catch (error) {
			console.error('Failed to add tag:', error);
			dispatch('error', { message: 'Failed to add tag' });
		}
	}
	
	async function removeTag(tag: Tag) {
		if (!documentId || mode !== 'edit') return;
		
		try {
			const response = await fetch(`/api/v1/documents/${documentId}/tags/${tag.id}`, {
				method: 'DELETE'
			});
			
			if (!response.ok) throw new Error('Failed to remove tag');
			
			selectedTags = selectedTags.filter(t => t.id !== tag.id);
			dispatch('change', { tags: selectedTags });
		} catch (error) {
			console.error('Failed to remove tag:', error);
			dispatch('error', { message: 'Failed to remove tag' });
		}
	}
	
	$: availableTags = allTags.filter(tag => 
		!selectedTags.some(t => t.id === tag.id) &&
		(searchQuery === '' || tag.name.toLowerCase().includes(searchQuery.toLowerCase()))
	);
	
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.tag-selector-dropdown')) {
			showDropdown = false;
		}
	}
</script>

<svelte:window on:click={handleClickOutside} />

<div class="tag-selector">
	<!-- Selected Tags -->
	<div class="flex flex-wrap gap-2 mb-2">
		{#each selectedTags as tag}
			<div
				class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm"
				style="background-color: {tag.color}20; color: {tag.color}; border: 1px solid {tag.color}40"
			>
				<span>{tag.name}</span>
				{#if mode === 'edit'}
					<button
						on:click={() => removeTag(tag)}
						class="ml-1 hover:opacity-70 transition-opacity"
					>
						<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
						</svg>
					</button>
				{/if}
			</div>
		{/each}
		
		{#if selectedTags.length === 0 && mode === 'display'}
			<span class="text-sm text-gray-500">No tags</span>
		{/if}
	</div>
	
	<!-- Add Tag Button (Edit Mode) -->
	{#if mode === 'edit' && documentId}
		<div class="relative tag-selector-dropdown">
			<button
				on:click|stopPropagation={() => showDropdown = !showDropdown}
				class="inline-flex items-center gap-2 px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
				Add Tag
			</button>
			
			{#if showDropdown}
				<div class="absolute z-10 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200">
					<div class="p-2 border-b border-gray-200">
						<input
							type="text"
							bind:value={searchQuery}
							placeholder="Search tags..."
							class="w-full px-3 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							on:click|stopPropagation
						/>
					</div>
					
					<div class="max-h-48 overflow-y-auto">
						{#if availableTags.length === 0}
							<div class="p-3 text-sm text-gray-500 text-center">
								{searchQuery ? 'No matching tags' : 'All tags are already added'}
							</div>
						{:else}
							{#each availableTags as tag}
								<button
									on:click|stopPropagation={() => addTag(tag)}
									class="w-full text-left px-3 py-2 hover:bg-gray-50 transition-colors flex items-center gap-2"
								>
									<div
										class="w-4 h-4 rounded-full"
										style="background-color: {tag.color}"
									></div>
									<span class="text-sm">{tag.name}</span>
								</button>
							{/each}
						{/if}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.tag-selector-dropdown {
		position: relative;
	}
</style>