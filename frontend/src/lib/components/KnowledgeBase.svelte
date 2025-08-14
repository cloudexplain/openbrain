<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { marked } from 'marked';
	import type { Document, DocumentDetail } from '$lib/api';
	import PushNotification from './PushNotification.svelte';
	import { invalidateAll } from '$app/navigation';
	
	const dispatch = createEventDispatcher();
	
	export let documents: Document[] = [];
	let selectedDocument: DocumentDetail | null = null;
	let isLoading = false;
	let searchQuery = '';
	let documentLoading = false;
	let parsedContent = '';
	let showUploadModal = false;
	let uploadLoading = false;
	
	// Push notifications
	let pushNotifications: Array<{
		id: number;
		message: string;
		type: 'success' | 'error' | 'info' | 'processing';
		duration: number;
	}> = [];
	let notificationId = 0;
	
	// Configure marked options
	marked.setOptions({
		breaks: true, // Enable line breaks
		gfm: true, // Enable GitHub Flavored Markdown
	});
	
	onMount(async () => {
		// Documents are now loaded from +page.server.ts and passed as props
		sortDocuments();
	});
	
	function sortDocuments() {
		// Sort by created_at descending
		documents = documents.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
	}
	
	async function loadDocuments() {
		// Refresh documents from server
		await invalidateAll();
	}
	
	async function selectDocument(doc: Document) {
		documentLoading = true;
		try {
			const response = await fetch(`/api/v1/documents/${doc.id}`);
			
			if (!response.ok) {
				throw new Error(`Failed to load document: ${response.status}`);
			}
			
			selectedDocument = await response.json();
			// Parse markdown content
			if (selectedDocument) {
				parsedContent = marked.parse(selectedDocument.content) as string;
			}
		} catch (error) {
			console.error('Failed to load document:', error);
		} finally {
			documentLoading = false;
		}
	}
	
	function formatDate(dateString: string) {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
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
	
	$: filteredDocuments = documents.filter(doc =>
		doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
		doc.source_type.toLowerCase().includes(searchQuery.toLowerCase())
	);
	
	function showPushNotification(message: string, type: 'success' | 'error' | 'info' | 'processing' = 'info', duration: number = 3000) {
		const id = ++notificationId;
		pushNotifications = [...pushNotifications, { id, message, type, duration }];
		
		// Return ID so we can remove specific notifications
		return id;
	}
	
	function removePushNotification(id: number) {
		pushNotifications = pushNotifications.filter(n => n.id !== id);
	}
	
	async function handleFileUpload(event: Event) {
		const target = event.target as HTMLInputElement;
		const files = target.files;
		
		if (!files || files.length === 0) return;
		
		const file = files[0];
		
		// Validate file type
		const allowedTypes = ['application/pdf', 'text/plain', 'text/markdown', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
		if (!allowedTypes.includes(file.type)) {
			showPushNotification('Unsupported file type. Please upload PDF, TXT, MD, or DOCX files.', 'error');
			return;
		}
		
		// Validate file size (50MB max)
		const maxSize = 50 * 1024 * 1024; // 50MB
		if (file.size > maxSize) {
			showPushNotification('File too large. Maximum size is 50MB.', 'error');
			return;
		}
		
		uploadLoading = true;
		
		// Show processing notification
		const processingNotificationId = showPushNotification(`Uploading "${file.name}"...`, 'processing', 0); // Duration 0 = stays until removed
		
		try {
			// Use fetch directly to call our proxy endpoint
			const formData = new FormData();
			formData.append('file', file);
			
			const fetchResponse = await fetch('?/uploadDocument', {
				method: 'POST',
				body: formData
			});
			
			if (!fetchResponse.ok) {
				throw new Error(`Upload failed: ${fetchResponse.status} ${fetchResponse.statusText}`);
			}
			
			const response = await fetchResponse.json();
			
			// Remove processing notification
			removePushNotification(processingNotificationId);
			
			// Show success notification
			showPushNotification(`"${file.name}" uploaded! Processing in background...`, 'info', 2000);
			
			// Close modal
			showUploadModal = false;
			
			// Reset file input
			if (target) {
				target.value = '';
			}
			
			// Wait a bit then refresh document list to see if processing is complete
			setTimeout(async () => {
				await loadDocuments();
				showPushNotification(`"${file.name}" processing complete!`, 'success', 3000);
			}, 5000); // Check after 5 seconds
			
			// Continue checking periodically
			const checkInterval = setInterval(async () => {
				await loadDocuments();
			}, 3000);
			
			// Stop checking after 30 seconds
			setTimeout(() => clearInterval(checkInterval), 30000);
			
		} catch (error) {
			console.error('Failed to upload document:', error);
			removePushNotification(processingNotificationId);
			showPushNotification('Failed to upload document', 'error', 5000);
		} finally {
			uploadLoading = false;
		}
	}
</script>

<div class="flex h-full w-full bg-white rounded-xl shadow-lg overflow-hidden">
	<!-- Document List -->
	<div class="w-80 border-r border-gray-200 flex flex-col h-full">
		<!-- Fixed Header -->
		<div class="p-4 border-b border-gray-200 bg-white z-10 flex-shrink-0">
			<div class="flex items-center justify-between mb-3">
				<h2 class="text-lg font-semibold text-gray-800">Knowledge Base</h2>
				<button
					on:click={() => dispatch('close')}
					class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
					title="Back to Chat"
				>
					<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>
			
			<!-- Upload Button -->
			<button
				on:click={() => showUploadModal = true}
				class="w-full mb-3 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white rounded-lg transition-all duration-200 text-sm font-medium shadow-md hover:shadow-lg"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
				</svg>
				Upload Document
			</button>
			
			<input
				type="text"
				placeholder="Search documents..."
				bind:value={searchQuery}
				class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
			/>
		</div>
		
		<!-- Scrollable Content -->
		<div class="flex-1 overflow-y-auto custom-scrollbar min-h-0">
			{#if isLoading}
				<div class="flex items-center justify-center h-64 text-gray-500">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
				</div>
			{:else if filteredDocuments.length === 0}
				<div class="text-center py-12 px-4 text-gray-500">
					<div class="text-4xl mb-3">📚</div>
					<div class="text-sm font-medium">No documents found</div>
					<div class="text-xs mt-1">Save chats to build your knowledge base</div>
				</div>
			{:else}
				{#each filteredDocuments as doc}
					<button
						on:click={() => selectDocument(doc)}
						class="w-full px-4 py-3 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 {selectedDocument?.id === doc.id ? 'bg-blue-50' : ''}"
					>
						<div class="flex items-start gap-3">
							<div class="text-xl mt-0.5">
								{getSourceIcon(doc.source_type)}
							</div>
							<div class="flex-1 min-w-0">
								<div class="font-medium text-sm text-gray-900 truncate">
									{doc.title}
								</div>
								<div class="flex items-center gap-2 mt-1 text-xs text-gray-500">
									<span class="capitalize">{doc.source_type}</span>
									<span>•</span>
									<span>{doc.chunk_count} chunks</span>
								</div>
								<div class="text-xs text-gray-400 mt-1">
									{formatDate(doc.created_at)}
								</div>
							</div>
							{#if selectedDocument?.id === doc.id}
								<div class="w-1 h-12 bg-blue-500 rounded-full self-center"></div>
							{/if}
						</div>
					</button>
				{/each}
			{/if}
		</div>
		
		<!-- Fixed Footer -->
		<div class="p-3 border-t border-gray-200 text-center text-xs text-gray-500 bg-white flex-shrink-0">
			{filteredDocuments.length} document{filteredDocuments.length !== 1 ? 's' : ''} in knowledge base
		</div>
	</div>
	
	<!-- Document Viewer -->
	<div class="flex-1 flex flex-col h-full">
		{#if documentLoading}
			<div class="flex-1 flex items-center justify-center">
				<div class="text-center">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
					<div class="text-sm text-gray-500">Loading document...</div>
				</div>
			</div>
		{:else if selectedDocument}
			<div class="flex flex-col h-full">
				<!-- Document Header -->
				<div class="px-6 py-4 border-b border-gray-200 flex-shrink-0">
					<div class="flex items-start justify-between">
						<div>
							<h3 class="text-xl font-semibold text-gray-900">
								{selectedDocument.title}
							</h3>
							<div class="flex items-center gap-3 mt-2 text-sm text-gray-500">
								<span class="flex items-center gap-1">
									{getSourceIcon(selectedDocument.source_type)}
									<span class="capitalize">{selectedDocument.source_type}</span>
								</span>
								<span>•</span>
								<span>{selectedDocument.chunk_count} chunks</span>
								<span>•</span>
								<span>{formatDate(selectedDocument.created_at)}</span>
							</div>
						</div>
						<button
							on:click={() => selectedDocument = null}
							class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
							title="Close document"
						>
							<svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
							</svg>
						</button>
					</div>
				</div>
				
				<!-- Document Content -->
				<div class="flex-1 overflow-y-auto px-6 py-4 bg-white custom-scrollbar min-h-0">
					<div class="markdown-content prose prose-sm max-w-none 
						prose-headings:text-gray-900 
						prose-p:text-gray-700 
						prose-strong:text-gray-900 
						prose-code:text-pink-600 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
						prose-pre:bg-gray-900 prose-pre:text-gray-100
						prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:text-gray-700
						prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
						prose-li:text-gray-700
						prose-hr:border-gray-300">
						{@html parsedContent}
					</div>
				</div>
				
				<!-- Document Actions -->
				<div class="px-6 py-3 border-t border-gray-200 flex items-center justify-between flex-shrink-0">
					<div class="text-xs text-gray-500">
						Document ID: {selectedDocument.id.slice(0, 8)}...
					</div>
					<div class="flex gap-2">
						<button
							class="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
							title="Copy content"
							on:click={() => {
								navigator.clipboard.writeText(selectedDocument?.content || '');
							}}
						>
							Copy Content
						</button>
					</div>
				</div>
			</div>
		{:else}
			<div class="flex-1 flex items-center justify-center text-gray-400">
				<div class="text-center">
					<div class="text-6xl mb-4">📖</div>
					<div class="text-lg font-medium">Select a document to view</div>
					<div class="text-sm mt-2">Choose from your knowledge base on the left</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Upload Modal -->
{#if showUploadModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
			<div class="p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-800">Upload Document</h3>
					<button
						on:click={() => showUploadModal = false}
						class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
					>
						<svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
				
				<div class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
					<input
						type="file"
						id="fileUpload"
						accept=".pdf,.txt,.md,.docx"
						on:change={handleFileUpload}
						class="hidden"
						disabled={uploadLoading}
					/>
					
					{#if uploadLoading}
						<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
						<p class="text-sm text-gray-600">Uploading document...</p>
					{:else}
						<svg class="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
						</svg>
						<p class="text-sm text-gray-600 mb-2">Choose a file to upload</p>
						<p class="text-xs text-gray-500 mb-4">Supports PDF, TXT, MD, and DOCX files (max 50MB)</p>
						<label
							for="fileUpload"
							class="inline-flex items-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer transition-colors"
						>
							Select File
						</label>
					{/if}
				</div>
				
				<div class="flex justify-end gap-2 mt-6">
					<button
						on:click={() => showUploadModal = false}
						class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
						disabled={uploadLoading}
					>
						Cancel
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Push Notifications -->
{#each pushNotifications as notification (notification.id)}
	<PushNotification
		message={notification.message}
		type={notification.type}
		duration={notification.duration}
		onClose={() => removePushNotification(notification.id)}
	/>
{/each}

<style>
	/* Custom scrollbar styling */
	:global(.custom-scrollbar) {
		scrollbar-width: thin;
		scrollbar-color: #cbd5e1 #f1f5f9;
	}
	
	:global(.custom-scrollbar::-webkit-scrollbar) {
		width: 8px;
		height: 8px;
	}
	
	:global(.custom-scrollbar::-webkit-scrollbar-track) {
		background: #f1f5f9;
		border-radius: 4px;
	}
	
	:global(.custom-scrollbar::-webkit-scrollbar-thumb) {
		background: #cbd5e1;
		border-radius: 4px;
	}
	
	:global(.custom-scrollbar::-webkit-scrollbar-thumb:hover) {
		background: #94a3b8;
	}
	
	:global(.markdown-content pre) {
		background-color: #1a1a1a;
		color: #e0e0e0;
		padding: 1rem;
		border-radius: 0.5rem;
		overflow-x: auto;
	}
	
	:global(.markdown-content code) {
		font-family: 'Monaco', 'Courier New', monospace;
	}
	
	:global(.markdown-content pre code) {
		background-color: transparent;
		color: inherit;
		padding: 0;
	}
	
	:global(.markdown-content h1),
	:global(.markdown-content h2),
	:global(.markdown-content h3) {
		font-weight: 600;
		margin-top: 1.5rem;
		margin-bottom: 0.75rem;
	}
	
	:global(.markdown-content p) {
		line-height: 1.7;
		margin-bottom: 1rem;
	}
	
	:global(.markdown-content ul),
	:global(.markdown-content ol) {
		margin-left: 1.5rem;
		margin-bottom: 1rem;
	}
	
	:global(.markdown-content li) {
		margin-bottom: 0.5rem;
	}
	
	:global(.markdown-content blockquote) {
		padding: 0.75rem 1rem;
		margin: 1rem 0;
		border-left: 4px solid #3b82f6;
		background-color: #eff6ff;
	}
</style>