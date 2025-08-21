<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	
	const dispatch = createEventDispatcher();
	
	export let show = false;
	export let position = { x: 0, y: 0 };
	export let query = '';
	
	interface Document {
		id: string;
		title: string;
		source_type: string;
		file_type?: string;
		filename?: string;
		created_at?: string;
		chunk_count: number;
	}
	
	let documents: Document[] = [];
	let isLoading = false;
	let selectedIndex = 0;
	let container: HTMLDivElement;
	let adjustedPosition = { ...position };
	let dropdownHeight = 0;
	let searchTimeout: NodeJS.Timeout | null = null;

	// Search documents when query changes or component shows (with debounce)
	$: if (show) {
		// Clear existing timeout
		if (searchTimeout) {
			clearTimeout(searchTimeout);
		}
		
		// Debounce search requests
		searchTimeout = setTimeout(() => {
			searchDocuments(query);
			selectedIndex = 0; // Reset selection when query changes
		}, 150); // 150ms debounce
	}
	
	$: if (!show) {
		selectedIndex = 0;
		// Clear any pending search timeout
		if (searchTimeout) {
			clearTimeout(searchTimeout);
			searchTimeout = null;
		}
	}

	// Recalculate position when show state, position, or container changes
	$: if (show && position && typeof window !== 'undefined') {
		// Use setTimeout to ensure DOM is rendered
		setTimeout(() => {
			calculatePosition();
		}, 10);
	}
	
	// Also recalculate when documents load (which changes dropdown height)
	$: if (show && documents && typeof window !== 'undefined') {
		setTimeout(() => calculatePosition(), 20);
	}

	function calculatePosition() {
		if (typeof window === 'undefined') return;
		
		const viewportHeight = window.innerHeight;
		// Estimate dropdown height - either actual height or reasonable default
		const estimatedHeight = Math.min(300, dropdownHeight || 250); // Slightly taller than tags for metadata
		
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
	
	async function searchDocuments(currentQuery: string) {
		isLoading = true;
		try {
			console.log('Searching documents with query:', currentQuery);
			
			// Try new search endpoint first
			let response = await fetch(`/api/v1/documents/search?query=${encodeURIComponent(currentQuery || '')}&limit=10`);
			console.log('Search endpoint response status:', response.status);
			
			if (response.ok) {
				const data = await response.json();
				console.log('Search response data:', data);
				documents = data.documents || [];
			} else {
				console.warn('Search endpoint failed, falling back to old approach');
				// Fallback to old approach
				response = await fetch('/api/v1/documents');
				if (response.ok) {
					const allDocuments = await response.json();
					console.log('Fallback: loaded', allDocuments.length, 'documents');
					
					// Filter documents based on query
					if (currentQuery && currentQuery.trim()) {
						documents = allDocuments.filter((doc) => 
							doc.title.toLowerCase().includes(currentQuery.toLowerCase())
						);
					} else {
						documents = allDocuments;
					}
					
					// Limit results to 10 and sort by creation date
					documents = documents
						.slice(0, 10)
						.sort((a, b) => new Date(b.created_at || '').getTime() - new Date(a.created_at || '').getTime());
				}
			}
		} catch (error) {
			console.error('Failed to search documents:', error);
			documents = [];
		} finally {
			isLoading = false;
		}
	}
	
	function selectDocument(document: Document) {
		dispatch('select', { document });
	}
	
	function selectCurrentDocument() {
		if (documents.length > 0 && selectedIndex >= 0 && selectedIndex < documents.length) {
			selectDocument(documents[selectedIndex]);
		}
	}
	
	function handleKeydown(event: KeyboardEvent) {
		if (!show || documents.length === 0) return;
		
		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				selectedIndex = Math.min(selectedIndex + 1, documents.length - 1);
				scrollToSelected();
				break;
			case 'ArrowUp':
				event.preventDefault();
				selectedIndex = Math.max(selectedIndex - 1, 0);
				scrollToSelected();
				break;
			case 'Enter':
				event.preventDefault();
				selectCurrentDocument();
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
	
	function getFileIcon(document: Document) {
		if (document.file_type === 'application/pdf') return '📄';
		if (document.file_type === 'text/plain') return '📝';
		if (document.file_type === 'text/markdown') return '📋';
		if (document.source_type === 'chat') return '💬';
		return '📁';
	}
	
	function formatDate(dateString?: string) {
		if (!dateString) return '';
		const date = new Date(dateString);
		return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
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
		class="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-2 min-w-72 max-h-72 overflow-y-auto document-autocomplete"
		style="left: {adjustedPosition.x}px; top: {adjustedPosition.y}px;"
		bind:clientHeight={dropdownHeight}
	>
		{#if isLoading}
			<div class="px-4 py-3 text-sm text-gray-500 flex items-center">
				<svg class="w-4 h-4 mr-2 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
				</svg>
				Searching documents...
			</div>
		{:else if documents.length === 0}
			<div class="px-4 py-3 text-sm text-gray-500">
				{query.length > 0 ? 'No documents found' : 'No documents available'}
			</div>
		{:else}
			{#each documents as document, index}
				<button
					data-index={index}
					on:click={() => selectDocument(document)}
					class="w-full px-4 py-3 text-left transition-colors hover:bg-gray-50 {
						index === selectedIndex 
							? 'bg-blue-50 border-l-2 border-blue-500' 
							: ''
					}"
				>
					<div class="flex items-start gap-3">
						<div class="text-lg mt-0.5 flex-shrink-0">
							{getFileIcon(document)}
						</div>
						<div class="flex-1 min-w-0">
							<div class="font-medium text-gray-900 text-sm truncate">
								{document.title}
							</div>
							<div class="flex items-center gap-2 mt-1 text-xs text-gray-500">
								{#if document.source_type === 'chat'}
									<span class="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">Chat</span>
								{:else if document.filename}
									<span class="bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">{document.filename}</span>
								{/if}
								
								{#if document.chunk_count}
									<span>{document.chunk_count} chunks</span>
								{/if}
								
								{#if document.created_at}
									<span>•</span>
									<span>{formatDate(document.created_at)}</span>
								{/if}
							</div>
						</div>
					</div>
				</button>
			{/each}
			{#if documents.length > 0}
				<div class="px-4 py-2 text-xs text-gray-400 border-t border-gray-100 mt-1">
					Use ↑↓ to navigate, Enter to select, Esc to close
				</div>
			{/if}
		{/if}
	</div>
{/if}