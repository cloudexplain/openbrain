<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from "svelte";
	
	import { goto } from "$app/navigation";
	
	
	import ChatMessage from "$lib/components/ChatMessage.svelte";
	import MessageInput from "$lib/components/MessageInput.svelte";
	import LoadingIndicator from "$lib/components/LoadingIndicator.svelte";
	import KnowledgeEditModal from "$lib/components/KnowledgeEditModal.svelte";
	import Notification from "$lib/components/Notification.svelte";
	import type { Message, ChatListItem, StreamResponse, DocumentReference } from "$lib/api";
	import { deepResearchDepth, depthConfigs } from "$lib/stores/deepResearch";

	// Get chat ID from route params
	let chatId = $derived($page.params.id);

	let messages = $state<Message[]>([]);
	let currentChatTitle = $state("");
	let isLoading = $state(false);
	let streamingMessage = $state("");
	let showKnowledgeModal = $state(false);
	
	// Track document references for each message
	let messageDocumentReferences = $state(new Map<string, DocumentReference[]>());
	
	// Track message count for auto-title updates
	let messageCountSinceLastTitleUpdate = $state(0);
	let totalMessageCount = $state(0);
	let lastUserPromptForRename = $state(0);
	
	// Drag and drop state
	let isDragOver = $state(false);
	let uploadingFiles = $state<Array<{name: string, progress: number, status: 'uploading' | 'success' | 'error'}>>([]);

	// Notification system
	let notifications = $state<Array<{
		id: number;
		message: string;
		type: "success" | "error" | "info";
	}>>([]);
	let notificationId = $state(0);

	onMount(async () => {
		if (chatId) {
			await loadChatMessages();
		}
		
		// Cleanup polling interval on component destroy
		return () => {
			if (pollingInterval) {
				clearInterval(pollingInterval);
				pollingInterval = null;
			}
		};
	});

	// Watch for route changes
	$effect(() => {
		if (chatId) {
			loadChatMessages();
		}
	});

	// DEBUG: Reactive logging to diagnose the issue
	$effect(() => {
		console.log("🔍 [DEBUG] Reactive state update:");
		console.log("  - messages.length:", messages.length);
		console.log("  - isLoading:", isLoading);
		console.log("  - streamingMessage:", streamingMessage);
		console.log("  - Show welcome condition:", messages.length === 0 && !isLoading && !streamingMessage);
		console.log("  - Messages array:", messages);
	});

	// Polling for deep research completion
	let pollingInterval = $state(null);

	$effect(() => {
		// Check if any message has deep research status "running"
		const hasRunningResearch = messages.some(msg => 
			msg.role === "assistant" && 
			(msg.content === "Deep research in progress..." || msg.content?.includes("Deep research in progress"))
		);

		if (hasRunningResearch && !pollingInterval) {
			// Start polling every 3 seconds
			pollingInterval = setInterval(async () => {
				await loadChatMessages();
			}, 3000);
			console.log("Started polling for deep research completion");
		} else if (!hasRunningResearch && pollingInterval) {
			// Stop polling when no running research
			clearInterval(pollingInterval);
			pollingInterval = null;
			console.log("Stopped polling - no running research");
		}
	});

	async function loadChatMessages() {
		try {
			isLoading = true;
			console.log("Loading chat messages for:", chatId);

			// Load chat with messages
			const response = await fetch(`/api/v1/chats/${chatId}`);

			console.log("Response status:", response.status);

			if (!response.ok) {
				throw new Error(`Failed to load messages: ${response.status}`);
			}

			const chat = await response.json();
			console.log("Raw chat data:", chat);

			// Set messages and title with explicit reactivity
			const loadedMessages = Array.isArray(chat.messages) ? chat.messages : [];
			// Sort messages chronologically (oldest first)
			const sortedMessages = loadedMessages.sort((a, b) => 
				new Date(a.created_at || a.timestamp).getTime() - new Date(b.created_at || b.timestamp).getTime()
			);
			messages = [...sortedMessages]; // Force new array reference for reactivity
			currentChatTitle = chat.title || `Chat ${chatId}`;

			console.log("Set messages:", messages.length, "messages");
			console.log("Set title:", currentChatTitle);
			
			// Force UI update
			console.log("🔄 Messages variable updated, should trigger reactive update");

			// Clear any streaming message
			streamingMessage = "";
			
			// Scroll to bottom after messages load
			setTimeout(() => {
				scrollToBottom();
			}, 100);
		} catch (error) {
			console.error("Error loading chat:", error);
			showNotification("Failed to load chat messages", "error");
		} finally {
			isLoading = false;
		}
	}


	async function handleSendMessage(event: CustomEvent<{ content: string; useDeepResearch: boolean }>) {
		const { content, useDeepResearch } = event.detail;
		const trimmedContent = content.trim();
		if (!trimmedContent || isLoading) return;

		// Create user message
		const userMessage: Message = {
			id: Date.now().toString(),
			content: trimmedContent,
			role: "user",
			timestamp: new Date().toISOString(),
			chatId: chatId,
		};

		messages = [...messages, userMessage];
		isLoading = true;
		streamingMessage = "";

		try {
			// Get the current depth configuration
			const currentDepthConfig = depthConfigs.find(c => c.level === $deepResearchDepth) || depthConfigs[0];
			
			const response = await fetch("/api/v1/chat", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({ 
					message: trimmedContent,
					chat_id: chatId,
					use_rag: !useDeepResearch, // Disable RAG when using deep research
					rag_limit: 5,
					rag_threshold: 0.7,
					use_deep_research: useDeepResearch,
					max_concurrent_research_units: useDeepResearch ? currentDepthConfig.maxConcurrentResearchUnits : 1,
					max_researcher_iterations: useDeepResearch ? currentDepthConfig.maxResearcherIterations : 1,
					max_react_tool_calls: useDeepResearch ? currentDepthConfig.maxReactToolCalls : 1,
					max_structured_output_retries: useDeepResearch ? currentDepthConfig.maxStructuredOutputRetries : 1
				}),
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			if (useDeepResearch) {
				// For deep research, no streaming needed - just reload messages
				// The backend creates the message immediately and starts processing
				// Our polling effect will detect the "running" message and start polling
				await loadChatMessages();
				scrollToBottom();
			} else {
				// Handle regular streaming for non-deep research
				const reader = response.body?.getReader();
				const decoder = new TextDecoder();
				let assistantMessage: Message | null = null;

				if (reader) {
					let buffer = "";
					while (true) {
						const { done, value } = await reader.read();
						if (done) break;

						buffer += decoder.decode(value, { stream: true });
						const lines = buffer.split("\n");
						buffer = lines.pop() || "";

						for (const line of lines) {
							if (line.startsWith("data: ")) {
								try {
									const data: StreamResponse = JSON.parse(line.slice(6));

									if (data.type === "content") {
										// First content chunk - create assistant message if it doesn't exist
										if (!assistantMessage) {
											assistantMessage = {
												id: Date.now().toString(), // Temporary ID until we get the real one
												content: "",
												role: "assistant",
												timestamp: new Date().toISOString(),
												chatId: chatId,
											};
											messages = [...messages, assistantMessage];
										}
										
										// Append content to streaming message and assistant message
										streamingMessage += data.content;
										assistantMessage.content += data.content;
										messages = [...messages];
									} else if (data.type === "done") {
										// Message is complete
										if (assistantMessage && data.message_id) {
											// Update with real message ID
											assistantMessage.id = data.message_id;
										}

										if (data.document_references && assistantMessage) {
											messageDocumentReferences.set(assistantMessage.id, data.document_references);
										}

										// Debug citation mapping
										if (data.citation_mapping) {
											console.log('📖 Citation mapping received:', data.citation_mapping);
										}

										streamingMessage = "";
										assistantMessage = null; // Reset for next message
									}
								} catch (e) {
									console.warn("Failed to parse streaming response:", line);
								}
							}
						}
					}
				}
			}

			// Update counters for auto-rename
			messageCountSinceLastTitleUpdate += 2; // User + assistant message
			totalMessageCount += 2;
			lastUserPromptForRename++;

			// Auto-rename chat after certain conditions
			if (shouldRenameChat()) {
				await handleAutoRenameChat();
			}
			
			// Reload messages to ensure we have the latest state from the server
			await loadChatMessages();
			scrollToBottom();

		} catch (error) {
			console.error("Error sending message:", error);
			showNotification("Failed to send message. Please try again.", "error");
		} finally {
			isLoading = false;
			streamingMessage = "";
		}
	}

	function shouldRenameChat(): boolean {
		return (
			currentChatTitle === "New Chat" &&
			totalMessageCount >= 4 &&
			lastUserPromptForRename >= 2
		);
	}

	async function handleAutoRenameChat() {
		if (!chatId) return;

		try {
			const response = await fetch(`/api/v1/chats/${chatId}/auto-title`, {
				method: "POST",
			});

			if (response.ok) {
				const data = await response.json();
				currentChatTitle = data.title;
				messageCountSinceLastTitleUpdate = 0;
				lastUserPromptForRename = 0;
			}
		} catch (error) {
			console.error("Failed to auto-rename chat:", error);
		}
	}

	async function handleSaveToKnowledge() {
		if (!chatId) return;
		showKnowledgeModal = true;
	}

	async function handleSaveEditedKnowledge(event: CustomEvent) {
		const { title, content, mode } = event.detail;
		
		try {
			// Prepare the request body based on the mode
			let requestBody: any = {
				title: title
			};
			
			if (mode === 'document') {
				// If in document mode, send the content as a single string
				requestBody.content = content;
			} else {
				// If in messages mode, send the edited messages array
				requestBody.messages = content;
			}
			
			const response = await fetch(`/api/v1/chats/${chatId}/save-to-knowledge`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(requestBody)
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}

			const result = await response.json();
			showKnowledgeModal = false;
			showNotification(`Saved "${title}" to knowledge base`, "success");
		} catch (error) {
			console.error("Error saving to knowledge:", error);
			showNotification("Failed to save to knowledge base", "error");
		}
	}

	async function handleOverwriteChat(event: CustomEvent) {
		const { messages: editedMessages, title } = event.detail;
		
		try {
			// Update the chat with edited messages
			const response = await fetch(`/api/v1/chats/${chatId}`, {
				method: "PUT",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					title: title,
					messages: editedMessages
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}

			// Update local state with edited messages
			messages = editedMessages.map((msg: any, index: number) => ({
				...msg,
				id: msg.id || `edited-${index}`,
				timestamp: msg.timestamp || new Date().toISOString(),
				chatId: chatId
			}));
			
			currentChatTitle = title;
			showKnowledgeModal = false;
			showNotification("Chat updated successfully", "success");
		} catch (error) {
			console.error("Error updating chat:", error);
			showNotification("Failed to update chat", "error");
		}
	}
	
	function handleCancelKnowledgeEdit() {
		showKnowledgeModal = false;
	}

	function handleMessageDeleted(event: CustomEvent<{ messageId: string }>) {
		console.log('📨 handleMessageDeleted called with event:', event.detail);
		const { messageId } = event.detail;
		
		console.log('📨 Removing message from UI, messageId:', messageId);
		console.log('📨 Messages before deletion:', messages.length);
		
		// Remove the message from the local messages array
		messages = messages.filter(msg => msg.id !== messageId);
		
		console.log('📨 Messages after deletion:', messages.length);
		
		// Also remove any document references for this message
		messageDocumentReferences.delete(messageId);
		
		console.log('📨 Showing success notification');
		showNotification("Message deleted successfully", "success");
	}

	function handleViewDocument(event: CustomEvent<{ documentId: string; chunks?: any[]; pages?: number[] }>) {
		const { documentId, chunks, pages } = event.detail;
		
		// Build the URL with optional highlight parameters
		let url = `/knowledge/${documentId}`;
		const params = new URLSearchParams();
		
		// Add messageId to track that this came from a chat
		params.set('messageId', chatId);
		
		if (chunks && chunks.length > 0) {
			// Extract chunk IDs
			const chunkIds = chunks.map(chunk => chunk.id || chunk.chunk_id).filter(Boolean);
			if (chunkIds.length > 0) {
				params.set('chunks', chunkIds.join(','));
			}
		}
		
		if (pages && pages.length > 0) {
			params.set('pages', pages.join(','));
		}
		
		if (params.toString()) {
			url += `?${params.toString()}`;
		}
		
		// Navigate to the document with highlights
		goto(url);
	}

	async function handleSuggestedPrompt(prompt: string) {
		await handleSendMessage(
			new CustomEvent("send", {
				detail: { content: prompt, useDeepResearch: false },
			}),
		);
	}

	// Drag and drop handlers
	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		isDragOver = true;
	}

	function handleDragLeave(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		
		// Only set isDragOver to false if we're leaving the main container
		if (!event.currentTarget?.contains(event.relatedTarget as Node)) {
			isDragOver = false;
		}
	}

	async function handleDrop(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		isDragOver = false;

		const files = Array.from(event.dataTransfer?.files || []);
		if (files.length === 0) return;

		// Filter for supported file types
		const supportedTypes = ['.pdf', '.txt', '.md', '.docx'];
		const supportedFiles = files.filter(file => 
			supportedTypes.some(type => file.name.toLowerCase().endsWith(type))
		);

		if (supportedFiles.length === 0) {
			showNotification("Please drop supported files (PDF, TXT, MD, DOCX)", "error");
			return;
		}

		// Process each file
		for (const file of supportedFiles) {
			await uploadFile(file);
		}
	}

	async function uploadFile(file: File) {
		const fileProgress = {
			name: file.name,
			progress: 0,
			status: 'uploading' as const
		};
		
		uploadingFiles = [...uploadingFiles, fileProgress];

		try {
			const formData = new FormData();
			formData.append('file', file);
			// const response = await fetch("?/uploadDocument", {
			// 	method: "POST",
			// 	headers: authService.getAuthHeaders(),
			// 	body: formData,
			// });

			const response = await fetch('/api/v1/documents/upload', {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				throw new Error(`Upload failed: ${response.status}`);
			}

			const result = await response.json();
			
			// Update file status
			uploadingFiles = uploadingFiles.map(f => 
				f.name === file.name 
					? { ...f, status: 'success', progress: 100 }
					: f
			);

			// Auto-reference the uploaded document
			handleAutoReferenceDocuments([result]);

			// Remove from progress after a delay
			setTimeout(() => {
				uploadingFiles = uploadingFiles.filter(f => f.name !== file.name);
			}, 3000);

		} catch (error) {
			console.error('Upload error:', error);
			
			// Update file status to error
			uploadingFiles = uploadingFiles.map(f => 
				f.name === file.name 
					? { ...f, status: 'error' }
					: f
			);

			showNotification(`Failed to upload ${file.name}`, "error");

			// Remove from progress after a delay
			setTimeout(() => {
				uploadingFiles = uploadingFiles.filter(f => f.name !== file.name);
			}, 5000);
		}
	}

	function handleAutoReferenceDocuments(uploads: any[]) {
		// Dispatch an event to MessageInput to auto-reference the uploaded documents
		const documentReferences = uploads.map(upload => ({
			title: upload.title || upload.filename,
			filename: upload.filename
		}));
		
		// Use a custom event to communicate with MessageInput
		const event = new CustomEvent('auto-reference-documents', {
			detail: { documents: documentReferences }
		});
		
		window.dispatchEvent(event);
	}

	function showNotification(
		message: string,
		type: "success" | "error" | "info" = "info",
	) {
		const id = notificationId++;
		notifications = [...notifications, { id, message, type }];
	}

	function removeNotification(id: number) {
		notifications = notifications.filter((n) => n.id !== id);
	}

	function scrollToBottom() {
		// Scroll to the bottom of the chat messages container
		const chatContainer = document.querySelector('.chat-messages-container');
		if (chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		} else {
			// Fallback: scroll the entire page to bottom
			window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
		}
	}
</script>

<!-- Chat Content -->
<div
	class="flex flex-col h-full bg-white overflow-hidden relative"
	on:dragover={handleDragOver}
	on:dragleave={handleDragLeave}
	on:drop={handleDrop}
>
	<!-- Chat Header (only show when there are messages) -->
	{#if chatId && messages.length > 0}
		<div
			class="flex items-center justify-between px-6 py-3 border-b border-gray-100 bg-gray-50/50"
		>
			<div class="text-sm text-gray-600">
				<span class="font-medium">{currentChatTitle}</span>
				<span class="mx-2">•</span>
				<span>{messages.length} message{messages.length !== 1 ? 's' : ''}</span>
			</div>
			<div class="flex items-center gap-2">
				<button
					on:click={handleSaveToKnowledge}
					class="flex items-center gap-2 px-3 py-1.5 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors duration-200"
					title="Save this conversation to knowledge base for future reference"
				>
					<svg
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12"
						/>
					</svg>
					Save to Knowledge
				</button>
			</div>
		</div>
	{/if}

	<!-- Chat Messages -->
	<div class="flex-1 overflow-y-auto chat-messages-container">
		{#if messages.length === 0 && !isLoading && !streamingMessage}
			<div
				class="flex items-center justify-center h-full p-8"
			>
				<div
					class="text-center max-w-2xl"
				>
					<div
						class="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-blue-500/25"
					>
						<svg
							class="w-8 h-8 text-white"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
							/>
						</svg>
					</div>
					<h2
						class="text-2xl font-bold text-gray-900 mb-3"
					>
						Welcome to SecondBrain
					</h2>
					<p
						class="text-gray-600 mb-6 leading-relaxed"
					>
						Your intelligent assistant that learns with you, curates your knowledge and helps you make sense of the world.
					</p>

				</div>
			</div>
		{:else}
			<div class="p-6">
				{#each messages as message}
					<ChatMessage
						{message}
						documentReferences={messageDocumentReferences.get(message.id) || []}
						on:viewDocument={handleViewDocument}
						on:messageDeleted={handleMessageDeleted}
					/>
				{/each}
				
				{#if isLoading}
					<LoadingIndicator />
				{/if}
				
				{#if streamingMessage}
					<ChatMessage
						message={{
							id: "streaming",
							content: streamingMessage,
							role: "assistant",
							timestamp: new Date(),
						}}
						documentReferences={[]}
						on:messageDeleted={handleMessageDeleted}
					/>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Message Input -->
	<MessageInput
		disabled={isLoading || streamingMessage !== ""}
		on:send={handleSendMessage}
	/>

	<!-- Drag Overlay -->
	{#if isDragOver}
		<div class="absolute inset-0 bg-blue-500/10 backdrop-blur-sm flex items-center justify-center z-50">
			<div class="bg-white/95 backdrop-blur-sm rounded-2xl border-2 border-dashed border-blue-400 p-12 text-center shadow-2xl">
				<div class="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center mx-auto mb-6">
					<svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
					</svg>
				</div>
				<h3 class="text-xl font-semibold text-gray-900 mb-2">Drop files to upload</h3>
				<p class="text-gray-600 mb-4">Supported formats: PDF, TXT, MD, DOCX</p>
				<p class="text-sm text-gray-500">Files will be added to your knowledge base and automatically referenced</p>
			</div>
		</div>
	{/if}

	<!-- Upload Progress -->
	{#if uploadingFiles.length > 0}
		<div class="absolute top-4 right-4 z-40 max-w-sm">
			{#each uploadingFiles as file}
				<div class="mb-2 bg-white rounded-lg shadow-lg border border-gray-200 p-3">
					<div class="flex items-center gap-2 mb-2">
						{#if file.status === 'uploading'}
							<svg class="w-4 h-4 text-blue-500 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
							</svg>
						{:else if file.status === 'success'}
							<svg class="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
							</svg>
						{:else}
							<svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
							</svg>
						{/if}
						<span class="text-sm font-medium text-gray-900 truncate">{file.name}</span>
					</div>
					{#if file.status === 'uploading'}
						<div class="w-full bg-gray-200 rounded-full h-1.5">
							<div class="bg-blue-500 h-1.5 rounded-full transition-all duration-300" style="width: {file.progress}%"></div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Knowledge Edit Modal -->
{#if showKnowledgeModal}
	<KnowledgeEditModal
		{messages}
		chatTitle={currentChatTitle}
		chatId={chatId || ''}
		on:save={handleSaveEditedKnowledge}
		on:overwrite={handleOverwriteChat}
		on:cancel={handleCancelKnowledgeEdit}
	/>
{/if}

<!-- Notifications -->
{#each notifications as notification (notification.id)}
	<Notification
		message={notification.message}
		type={notification.type}
		onClose={() => removeNotification(notification.id)}
	/>
{/each}
