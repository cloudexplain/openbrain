<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	
	const dispatch = createEventDispatcher();
	
	export let show = false;
	export let position = { x: 0, y: 0 };
	export let query = '';
	
	let tags: Array<{id: string, name: string, color: string}> = [];
	let isLoading = false;
	let selectedIndex = 0;
	let container: HTMLDivElement;
	let adjustedPosition = { ...position };
	let dropdownHeight = 0;

	$: if (show && query.length >= 0) {
		loadTags();
		selectedIndex = 0; // Reset selection when query changes
	}
	
	$: if (!show) {
		selectedIndex = 0;
	}

	// Recalculate position when show state, position, or container changes
	$: if (show && position && typeof window !== 'undefined') {
		// Use setTimeout to ensure DOM is rendered
		setTimeout(() => {
			calculatePosition();
		}, 10);
	}
	
	// Also recalculate when tags load (which changes dropdown height)
	$: if (show && tags && typeof window !== 'undefined') {
		setTimeout(() => calculatePosition(), 20);
	}

	function calculatePosition() {
		if (typeof window === 'undefined') return;
		
		const viewportHeight = window.innerHeight;
		// Estimate dropdown height - either actual height or reasonable default
		const estimatedHeight = Math.min(256, dropdownHeight || 200); // max-h-64 = 256px, or current height
		
		// Check if there's enough space below
		const spaceBelow = viewportHeight - position.y;
		const spaceAbove = position.y;
		
		let newY = position.y;
		
		// If not enough space below but enough space above, show above
		if (spaceBelow < estimatedHeight && spaceAbove >= estimatedHeight) {
			newY = position.y - estimatedHeight;
		}
		
		// Ensure dropdown doesn't go above viewport
		if (newY < 0) {
			newY = 10; // Small margin from top
		}
		
		// Ensure dropdown doesn't go below viewport
		if (newY + estimatedHeight > viewportHeight) {
			newY = viewportHeight - estimatedHeight - 10; // Small margin from bottom
		}
		
		adjustedPosition = { x: position.x, y: newY };
	}
	
	async function loadTags() {
		isLoading = true;
		try {
			const response = await fetch(`/api/v1/tags?search=${encodeURIComponent(query)}&limit=10`);
			if (response.ok) {
				const data = await response.json();
				tags = data.tags;
			}
		} catch (error) {
			console.error('Failed to load tags:', error);
		} finally {
			isLoading = false;
		}
	}
	
	function selectTag(tag: {name: string, color: string}) {
		dispatch('select', { tag });
	}
	
	function selectCurrentTag() {
		if (tags.length > 0 && selectedIndex >= 0 && selectedIndex < tags.length) {
			selectTag(tags[selectedIndex]);
		}
	}
	
	function handleKeydown(event: KeyboardEvent) {
		if (!show || tags.length === 0) return;
		
		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				selectedIndex = Math.min(selectedIndex + 1, tags.length - 1);
				scrollToSelected();
				break;
			case 'ArrowUp':
				event.preventDefault();
				selectedIndex = Math.max(selectedIndex - 1, 0);
				scrollToSelected();
				break;
			case 'Enter':
				event.preventDefault();
				selectCurrentTag();
				break;
			case 'Escape':
				event.preventDefault();
				dispatch('close');
				break;
		}
	}
	
	function scrollToSelected() {
		if (container) {
			const selectedElement = container.querySelector(`[data-index="${selectedIndex}"]`) as HTMLElement;
			if (selectedElement) {
				selectedElement.scrollIntoView({ block: 'nearest' });
			}
		}
	}
	
	onMount(() => {
		const handleGlobalKeydown = (event: KeyboardEvent) => {
			if (show) {
				handleKeydown(event);
			}
		};
		
		document.addEventListener('keydown', handleGlobalKeydown);
		
		return () => {
			document.removeEventListener('keydown', handleGlobalKeydown);
		};
	});
</script>

{#if show}
	<div
		bind:this={container}
		class="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-2 min-w-48 max-h-64 overflow-y-auto tag-autocomplete"
		style="left: {adjustedPosition.x}px; top: {adjustedPosition.y}px;"
		bind:clientHeight={dropdownHeight}
	>
		{#if isLoading}
			<div class="px-4 py-2 text-sm text-gray-500">Searching tags...</div>
		{:else if tags.length === 0}
			<div class="px-4 py-2 text-sm text-gray-500">
				{query.length > 0 ? 'No tags found' : 'Start typing to search tags...'}
			</div>
		{:else}
			{#each tags as tag, index}
				<button
					data-index={index}
					on:click={() => selectTag(tag)}
					class="w-full px-4 py-2 text-left transition-colors flex items-center gap-2 {
						index === selectedIndex 
							? 'bg-orange-50 text-orange-900' 
							: 'hover:bg-gray-50 text-gray-900'
					}"
				>
					<div
						class="w-3 h-3 rounded-full"
						style="background-color: {tag.color}"
					></div>
					<span class="text-sm">#{tag.name}</span>
				</button>
			{/each}
			{#if tags.length > 0}
				<div class="px-4 py-1 text-xs text-gray-400 border-t border-gray-100 mt-1">
					Use ↑↓ to navigate, Enter to select, Esc to close
				</div>
			{/if}
		{/if}
	</div>
{/if}