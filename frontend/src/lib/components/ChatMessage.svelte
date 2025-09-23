<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import DocumentReferences from './DocumentReferences.svelte';
	import MathRenderer from './MathRenderer.svelte';
	import type { DocumentReference } from '$lib/api';
	import { goto } from '$app/navigation';

	let { message, documentReferences = [] } = $props<{
		message: {
			id: string;
			content: string;
			role: 'user' | 'assistant';
			timestamp: Date;
		};
		documentReferences?: DocumentReference[];
	}>();

	// Debug: Log document references
	$effect(() => {
		if (documentReferences.length > 0) {
			console.log('📄 ChatMessage: Received document references for message', message.id, ':', documentReferences);
		}
	});

	const dispatch = createEventDispatcher();
	let showDeleteModal = $state(false);
	
	// Debug: Log when showDeleteModal changes
	$effect(() => {
		console.log('🗑️ showDeleteModal changed to:', showDeleteModal);
	});
	
	// Check localStorage for "don't ask again" preference
	function getSkipDeleteConfirmation(): boolean {
		if (typeof window !== 'undefined') {
			return localStorage.getItem('skipDeleteConfirmation') === 'true';
		}
		return false;
	}
	
	function setSkipDeleteConfirmation(skip: boolean) {
		if (typeof window !== 'undefined') {
			localStorage.setItem('skipDeleteConfirmation', skip.toString());
		}
	}

	function copyToClipboard() {
		navigator.clipboard.writeText(message.content).catch(err => {
			console.error('Failed to copy text: ', err);
		});
	}

	async function deleteMessage() {
		console.log('🗑️ Delete message called for:', message.id);
		try {
			console.log('🗑️ Making DELETE request to:', `/api/v1/messages/${message.id}`);
			const response = await fetch(`/api/v1/messages/${message.id}`, {
				method: 'DELETE',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			console.log('🗑️ Delete response status:', response.status);
			if (!response.ok) {
				const errorText = await response.text();
				console.error('🗑️ Delete failed, response body:', errorText);
				throw new Error(`Failed to delete message: ${response.status} - ${errorText}`);
			}

			console.log('🗑️ Delete successful, dispatching messageDeleted event');
			// Dispatch event to parent to remove message from UI
			dispatch('messageDeleted', { messageId: message.id });
			showDeleteModal = false;
		} catch (error) {
			console.error('🗑️ Error deleting message:', error);
			// You could add a notification here
		}
	}

	function confirmDelete() {
		console.log('🗑️ Confirm delete clicked for message:', message.id);
		// Check if user has opted to skip confirmation
		const skipConfirmation = getSkipDeleteConfirmation();
		console.log('🗑️ Skip confirmation setting:', skipConfirmation);
		if (skipConfirmation) {
			console.log('🗑️ Skip confirmation is enabled, deleting immediately');
			deleteMessage();
		} else {
			console.log('🗑️ Showing delete confirmation modal');
			showDeleteModal = true;
			console.log('🗑️ showDeleteModal is now:', showDeleteModal);
		}
	}
	
	function deleteWithoutAsking() {
		setSkipDeleteConfirmation(true);
		deleteMessage();
	}

	function handleViewDocument(event: CustomEvent<{id: string}>) {
		const documentId = event.detail.id;
		console.log('📄 ChatMessage: handleViewDocument called with documentId:', documentId);
		
		// Find the document reference to get chunk details
		const docRef = documentReferences.find(ref => ref.id === documentId);
		console.log('📄 ChatMessage: Found document reference:', docRef);
		
		// Build URL with highlighting parameters
		let url = `/knowledge/${documentId}`;
		const params = new URLSearchParams();
		
		// Add message ID for context
		params.set('messageId', message.id);
		
		// Add specific chunk info if available
		if (docRef?.chunks_used) {
			const chunkIds = docRef.chunks_used.map(chunk => chunk.chunk_id).join(',');
			const pages = [...new Set(docRef.chunks_used
				.map(chunk => chunk.page_number)
				.filter(Boolean)
				.sort((a, b) => a - b)
			)].join(',');
			
			console.log('📄 ChatMessage: Extracted chunk IDs:', chunkIds);
			console.log('📄 ChatMessage: Extracted pages:', pages);
			
			if (chunkIds) params.set('chunks', chunkIds);
			if (pages) params.set('pages', pages);
		}
		
		if (params.toString()) {
			url += '?' + params.toString();
		}
		
		console.log('📄 ChatMessage: Navigating to URL:', url);
		
		// Navigate to the knowledge page using SvelteKit navigation
		goto(url);
	}
</script>

<div class="group px-6 py-8 transition-colors duration-200 hover:bg-gray-50/30">
	<div class="max-w-3xl mx-auto">
		<div class="flex gap-6">
			<!-- Avatar -->
			<div class="flex-shrink-0 mt-1">
				{#if message.role === 'user'}
					<div class="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center shadow-sm">
						<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
						</svg>
					</div>
				{:else}
					<div class="w-7 h-7 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center shadow-sm">
						<svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
						</svg>
					</div>
				{/if}
			</div>
			
			<!-- Message Content -->
			<div class="flex-1 min-w-0">
				<!-- Role Label -->
				<div class="flex items-center gap-2 mb-3">
					<span class="text-sm font-medium text-gray-900">
						{message.role === 'user' ? 'You' : 'Assistant'}
					</span>
				</div>
				
				<!-- Message Text -->
				<div class="prose prose-sm prose-gray max-w-none text-gray-800 leading-relaxed 
							prose-headings:text-gray-900 prose-headings:font-semibold
							prose-a:text-blue-600 hover:prose-a:text-blue-800 prose-a:no-underline hover:prose-a:underline
							prose-code:text-gray-900 prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-medium
							prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200 prose-pre:rounded-lg prose-pre:p-4 prose-pre:overflow-x-auto
							prose-blockquote:border-l-blue-500 prose-blockquote:bg-blue-50/50 prose-blockquote:p-4 prose-blockquote:rounded-r-lg
							prose-ul:list-disc prose-ol:list-decimal prose-li:my-1
							prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-th:p-2 prose-th:bg-gray-50 prose-td:border prose-td:border-gray-300 prose-td:p-2
							citation-links">
					<!-- All messages now use standard markdown rendering -->
					<MathRenderer content={message.content} />
				</div>
				
				<!-- Document References (for assistant messages) -->
				{#if message.role === 'assistant' && documentReferences && documentReferences.length > 0}
					<DocumentReferences 
						references={documentReferences} 
						on:viewDocument={handleViewDocument}
					/>
				{/if}
				
				<!-- Action Buttons -->
				<div class="flex items-center gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
					{#if message.role === 'assistant'}
						<button on:click={copyToClipboard} class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors duration-150">
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
							</svg>
							Copy
						</button>
					{/if}
					<button on:click={() => {console.log('🗑️ Delete button clicked'); confirmDelete();}} class="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors duration-150">
						<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
						</svg>
						Delete
					</button>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- Delete Confirmation Modal -->
{#if showDeleteModal}
	{console.log('🗑️ MODAL IS RENDERING! showDeleteModal =', showDeleteModal)}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click|self={() => {console.log('🗑️ Modal backdrop clicked'); showDeleteModal = false;}}>
		<div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
			<div class="p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-800">
						Delete Message
					</h3>
					<button
						on:click={() => showDeleteModal = false}
						class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
					>
						<svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>

				<div class="mb-6">
					<div class="flex items-center gap-3 mb-3">
						<div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
							<svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
							</svg>
						</div>
						<div>
							<p class="text-sm text-gray-600">
								Are you sure you want to delete this {message.role === 'user' ? 'message' : 'response'}?
							</p>
						</div>
					</div>
					<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
						<p class="text-sm text-yellow-800">
							<strong>Warning:</strong> This action cannot be undone. The message will be permanently removed from the chat history.
						</p>
					</div>
				</div>

				<div class="flex items-center justify-between">
					<button
						on:click={deleteWithoutAsking}
						class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 underline transition-colors"
					>
						Don't ask again
					</button>
					<div class="flex gap-3">
						<button
							on:click={() => showDeleteModal = false}
							class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
						>
							Cancel
						</button>
						<button
							on:click={() => {console.log('🗑️ Modal delete button clicked'); deleteMessage();}}
							class="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium"
						>
							Delete Message
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Enhanced styling for citation links */
	:global(.citation-links a[href*="/knowledge/"][href*="chunks="]) {
		background: rgba(37, 99, 235, 0.1);
		padding: 1px 3px;
		border-radius: 2px;
		font-weight: 500;
		border: 1px solid rgba(37, 99, 235, 0.2);
		transition: all 0.2s ease;
		text-decoration: none;
	}
	
	:global(.citation-links a[href*="/knowledge/"][href*="chunks="]:hover) {
		background: rgba(37, 99, 235, 0.2);
		border-color: rgba(37, 99, 235, 0.4);
		text-decoration: underline;
	}
</style>
