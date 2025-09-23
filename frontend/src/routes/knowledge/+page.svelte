<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	
	let documents: any[] = [];
	let loading = true;
	let error: string | null = null;
	let searchQuery = '';
	
	onMount(async () => {
		await loadDocuments();
	});
	
	async function loadDocuments() {
		try {
			loading = true;
			error = null;
			
			console.log('Loading documents from /api/v1/documents...');
			const response = await fetch('/api/v1/documents');
			
			console.log('Response status:', response.status);
			console.log('Response headers:', response.headers);
			
			if (!response.ok) {
				const errorText = await response.text();
				console.error('API error response:', errorText);
				throw new Error(`Failed to load documents: ${response.status} ${errorText}`);
			}
			
			const data = await response.json();
			console.log('API response data:', data);
			
			// Check if data has documents property or is direct array
			if (Array.isArray(data)) {
				documents = data;
			} else if (data.documents) {
				documents = data.documents;
			} else {
				documents = [];
			}
			console.log('Loaded documents:', documents.length);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load documents';
			console.error('Error loading documents:', err);
		} finally {
			loading = false;
		}
	}
	
	function handleDocumentClick(documentId: string) {
		goto(`/knowledge/${documentId}`);
	}
	
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
	
	function formatDate(dateString: string) {
		return new Date(dateString).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
	
	let filteredDocuments = $derived(documents.filter(doc =>
		doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
		doc.filename?.toLowerCase().includes(searchQuery.toLowerCase())
	));
</script>

<div class="min-h-screen bg-gray-50">
	<!-- Header -->
	<div class="bg-white shadow-sm border-b">
		<div class="px-4 sm:px-6 lg:px-8 py-6">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-2xl font-bold text-gray-900">Knowledge Base</h1>
					<p class="text-sm text-gray-500 mt-1">
						{documents.length} document{documents.length !== 1 ? 's' : ''} in your knowledge base
					</p>
				</div>
				
				<!-- Upload button could go here -->
				<button
					class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
					on:click={() => goto('/')}
				>
					<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
					</svg>
					Upload Document
				</button>
			</div>
			
			<!-- Search bar -->
			<div class="mt-4">
				<div class="relative">
					<svg class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
					</svg>
					<input
						type="text"
						placeholder="Search documents..."
						bind:value={searchQuery}
						class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					>
				</div>
			</div>
		</div>
	</div>
	
	<!-- Content -->
	<div class="px-4 sm:px-6 lg:px-8 py-6">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="flex items-center space-x-2 text-gray-500">
					<svg class="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<span>Loading documents...</span>
				</div>
			</div>
		{:else if error}
			<div class="bg-red-50 border border-red-200 rounded-lg p-4">
				<div class="flex">
					<svg class="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
					</svg>
					<div>
						<h3 class="text-sm font-medium text-red-800">Error loading documents</h3>
						<p class="text-sm text-red-700 mt-1">{error}</p>
						<button 
							on:click={loadDocuments}
							class="mt-2 text-sm text-red-600 hover:text-red-800 underline"
						>
							Try again
						</button>
					</div>
				</div>
			</div>
		{:else if filteredDocuments.length === 0}
			<div class="text-center py-12">
				{#if documents.length === 0}
					<!-- No documents at all -->
					<div class="text-gray-500">
						<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
						</svg>
						<h3 class="mt-2 text-sm font-medium text-gray-900">No documents</h3>
						<p class="mt-1 text-sm text-gray-500">Get started by uploading your first document</p>
						<div class="mt-6">
							<button
								type="button"
								on:click={() => goto('/')}
								class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
							>
								<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
								</svg>
								Upload Document
							</button>
						</div>
					</div>
				{:else}
					<!-- No search results -->
					<div class="text-gray-500">
						<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
						</svg>
						<h3 class="mt-2 text-sm font-medium text-gray-900">No documents found</h3>
						<p class="mt-1 text-sm text-gray-500">Try adjusting your search query</p>
					</div>
				{/if}
			</div>
		{:else}
			<!-- Document grid -->
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
				{#each filteredDocuments as document}
					<div 
						class="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer group"
						on:click={() => handleDocumentClick(document.id)}
						role="button"
						tabindex="0"
						on:keydown={(e) => e.key === 'Enter' && handleDocumentClick(document.id)}
					>
						<!-- Document icon and type -->
						<div class="flex items-center justify-between mb-3">
							<div class="flex items-center">
								<span class="text-2xl mr-2">{getSourceIcon(document.source_type)}</span>
								<span class="text-xs text-gray-500 capitalize">{document.source_type}</span>
							</div>
							<div class="opacity-0 group-hover:opacity-100 transition-opacity">
								<svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
								</svg>
							</div>
						</div>
						
						<!-- Document title -->
						<h3 class="font-medium text-gray-900 text-sm mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
							{document.title}
						</h3>
						
						<!-- File info -->
						{#if document.filename}
							<p class="text-xs text-gray-500 mb-2 truncate">
								{document.filename}
							</p>
						{/if}
						
						<!-- Metadata -->
						<div class="text-xs text-gray-400 space-y-1">
							<div class="flex items-center justify-between">
								<span>Created</span>
								<span>{formatDate(document.created_at)}</span>
							</div>
							{#if document.metadata?.total_pages}
								<div class="flex items-center justify-between">
									<span>Pages</span>
									<span>{document.metadata.total_pages}</span>
								</div>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>