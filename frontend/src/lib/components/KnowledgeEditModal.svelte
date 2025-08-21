<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Message } from '$lib/api';
	
	export let messages: Message[] = [];
	export let chatTitle: string = '';
	export let chatId: string = '';
	
	const dispatch = createEventDispatcher();
	
	interface EditableMessage {
		id: string;
		content: string;
		role: 'user' | 'assistant';
		originalContent: string;
		isEditing: boolean;
	}
	
	let editableMessages: EditableMessage[] = messages.map(msg => ({
		...msg,
		originalContent: msg.content,
		isEditing: false
	}));
	
	let documentTitle = chatTitle;
	let documentContent = '';
	let editMode: 'messages' | 'document' = 'messages';
	let hoveredMessageIndex: number | null = null;
	let isGeneratingSummary = false;
	
	function focusAndSelect(node: HTMLDivElement) {
		node.focus();
		const range = document.createRange();
		range.selectNodeContents(node);
		const selection = window.getSelection();
		selection?.removeAllRanges();
		selection?.addRange(range);
		
		return {
			destroy() {}
		};
	}
	
	function deleteMessage(index: number) {
		editableMessages = editableMessages.filter((_, i) => i !== index);
		updateDocumentContent();
	}
	
	function startEditingMessage(index: number) {
		editableMessages[index].isEditing = true;
		editableMessages = editableMessages;
	}
	
	function finishEditingMessage(index: number) {
		editableMessages[index].isEditing = false;
		editableMessages = editableMessages;
		updateDocumentContent();
	}
	
	function handleEditableKeydown(event: KeyboardEvent, index: number) {
		if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			event.preventDefault();
			finishEditingMessage(index);
		} else if (event.key === 'Escape') {
			event.preventDefault();
			const target = event.currentTarget as HTMLDivElement;
			target.textContent = editableMessages[index].originalContent;
			editableMessages[index].content = editableMessages[index].originalContent;
			finishEditingMessage(index);
		}
	}
	
	function handleEditableInput(event: Event, index: number) {
		const target = event.currentTarget as HTMLDivElement;
		editableMessages[index].content = target.textContent || '';
	}
	
	function updateMessageContent(index: number, newContent: string) {
		editableMessages[index].content = newContent;
		updateDocumentContent();
	}
	
	function updateDocumentContent() {
		documentContent = editableMessages.map(msg => {
			const roleLabel = msg.role === 'user' ? 'Question' : 'Answer';
			return `${roleLabel}:\n${msg.content}`;
		}).join('\n\n---\n\n');
	}
	
	function switchToDocumentMode() {
		updateDocumentContent();
		editMode = 'document';
	}
	
	function switchToMessagesMode() {
		editMode = 'messages';
	}
	
	function handleSave() {
		const finalContent = editMode === 'document' 
			? documentContent 
			: editableMessages.map(msg => ({
				role: msg.role,
				content: msg.content
			}));
		
		dispatch('save', {
			title: documentTitle,
			content: finalContent,
			mode: editMode
		});
	}
	
	function handleCancel() {
		dispatch('cancel');
	}
	
	async function generateSummary() {
		if (isGeneratingSummary || !messages.length) return;
		
		isGeneratingSummary = true;
		
		try {
			// Use the passed chatId
			
			const response = await fetch(`/api/v1/chats/${chatId}/summarize`, {
				method: 'POST'
			});
			
			if (!response.ok) {
				throw new Error(`Failed to generate summary: ${response.status}`);
			}
			
			const result = await response.json();
			
			// Update the document title with the generated summary
			documentTitle = result.summary;
			
		} catch (error) {
			console.error('Error generating summary:', error);
			// You could show a notification here
		} finally {
			isGeneratingSummary = false;
		}
	}
	
	// Initialize document content
	updateDocumentContent();
</script>

<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
	<div class="bg-white rounded-xl max-w-6xl w-full max-h-[90vh] flex flex-col shadow-2xl">
		<div class="px-6 py-4 border-b border-gray-200">
			<h2 class="text-2xl font-semibold text-gray-800">Edit Knowledge Document</h2>
			<p class="text-sm text-gray-600 mt-1">
				Review and edit messages before saving to your knowledge base
			</p>
		</div>
		
		<div class="px-6 py-3 border-b border-gray-200">
			<label class="block text-sm font-medium text-gray-700 mb-2">
				Document Title
			</label>
			<div class="flex gap-2">
				<input
					type="text"
					bind:value={documentTitle}
					class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
					placeholder="Enter a descriptive title for this knowledge document"
				/>
				<button
					on:click={generateSummary}
					disabled={isGeneratingSummary}
					class="px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-gray-300 text-white rounded-lg transition-colors font-medium text-sm whitespace-nowrap"
					title="Generate an AI summary as the title"
				>
					{#if isGeneratingSummary}
						<svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
						</svg>
					{:else}
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
						</svg>
					{/if}
					Auto-Summarize
				</button>
			</div>
		</div>
		
		<div class="px-6 py-3 border-b border-gray-200 flex gap-2">
			<button
				on:click={switchToMessagesMode}
				class="px-4 py-2 rounded-lg font-medium transition-colors {editMode === 'messages' 
					? 'bg-blue-500 text-white' 
					: 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
			>
				Edit Messages
			</button>
			<button
				on:click={switchToDocumentMode}
				class="px-4 py-2 rounded-lg font-medium transition-colors {editMode === 'document' 
					? 'bg-blue-500 text-white' 
					: 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
			>
				Edit as Document
			</button>
			
			{#if editMode === 'messages'}
				<div class="ml-auto text-sm text-gray-600 flex items-center">
					<span class="mr-4">{editableMessages.length} messages</span>
					<span class="text-xs text-gray-500">Double-click to edit • Hover to delete</span>
				</div>
			{/if}
		</div>
		
		<div class="flex-1 overflow-y-auto px-6 py-4">
			{#if editMode === 'messages'}
				<div class="space-y-4 max-w-4xl mx-auto">
					{#each editableMessages as msg, index}
						<div 
							class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}"
							on:mouseenter={() => hoveredMessageIndex = index}
							on:mouseleave={() => hoveredMessageIndex = null}
						>
							<div class="relative max-w-[80%] group">
								<!-- Message bubble -->
								<div 
									class="px-4 py-3 rounded-2xl cursor-pointer transition-all duration-200 {msg.role === 'user' 
										? 'bg-blue-500 text-white ml-4' 
										: 'bg-gray-100 text-gray-900 mr-4'} 
									{msg.isEditing ? 'ring-2 ring-blue-300' : 'hover:shadow-md'}"
									on:dblclick={() => startEditingMessage(index)}
								>
									{#if msg.isEditing}
										<div>
											<div
												contenteditable="true"
												on:blur={() => finishEditingMessage(index)}
												on:input={(e) => handleEditableInput(e, index)}
												on:keydown={(e) => handleEditableKeydown(e, index)}
												class="whitespace-pre-wrap focus:outline-none"
												role="textbox"
												aria-multiline="true"
												use:focusAndSelect
											>
												{msg.content}
											</div>
											<div class="text-xs opacity-75 mt-2">
												Press Ctrl+Enter to save, Esc to cancel
											</div>
										</div>
									{:else}
										<div class="whitespace-pre-wrap">
											{msg.content}
										</div>
									{/if}
								</div>
								
								<!-- Delete button -->
								{#if hoveredMessageIndex === index && !msg.isEditing}
									<button
										on:click={() => deleteMessage(index)}
										class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors shadow-lg"
										title="Delete message"
									>
										<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
										</svg>
									</button>
								{/if}
								
								<!-- Role indicator -->
								<div class="text-xs text-gray-500 mt-1 {msg.role === 'user' ? 'text-right' : 'text-left'}">
									{msg.role === 'user' ? 'You' : 'Assistant'}
									{#if msg.content !== msg.originalContent}
										<span class="ml-1 px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded">
											edited
										</span>
									{/if}
								</div>
							</div>
						</div>
					{/each}
					
					{#if editableMessages.length === 0}
						<div class="text-center py-12 text-gray-500">
							<div class="text-6xl mb-4">💬</div>
							<div class="text-lg">No messages to save</div>
							<div class="text-sm">Add some content to save to your knowledge base</div>
						</div>
					{/if}
				</div>
			{:else}
				<div class="h-full">
					<label class="block text-sm font-medium text-gray-700 mb-2">
						Document Content
					</label>
					<textarea
						bind:value={documentContent}
						class="w-full h-[calc(100%-2rem)] px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
						placeholder="Edit the document content here..."
					/>
				</div>
			{/if}
		</div>
		
		<div class="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
			<div class="text-sm text-gray-600">
				{#if editMode === 'messages'}
					{editableMessages.length} messages ready to save
				{:else}
					Editing as single document
				{/if}
			</div>
			<div class="flex gap-3">
				<button
					on:click={handleCancel}
					class="px-5 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
				>
					Cancel
				</button>
				<button
					on:click={handleSave}
					class="px-5 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
				>
					Save to Knowledge Base
				</button>
			</div>
		</div>
	</div>
</div>