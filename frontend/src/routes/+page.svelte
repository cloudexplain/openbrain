<script lang="ts">
	import { onMount } from "svelte";
	import Sidebar from "$lib/components/Sidebar.svelte";
	import ChatMessage from "$lib/components/ChatMessage.svelte";
	import MessageInput from "$lib/components/MessageInput.svelte";
	import LoadingIndicator from "$lib/components/LoadingIndicator.svelte";
	import KnowledgeEditModal from "$lib/components/KnowledgeEditModal.svelte";
	import Notification from "$lib/components/Notification.svelte";
	import KnowledgeBase from "$lib/components/KnowledgeBase.svelte";
	import TagManager from "$lib/components/TagManager.svelte";
	import type { Message, ChatListItem, StreamResponse, DocumentReference } from "$lib/api";

	// Get data from server
	export let data;

	let messages: Message[] = [];
	let chats: ChatListItem[] = [];
	let currentChatId: string | null = null;
	let isLoading = false;
	let streamingMessage = "";
	let isSidebarMinimized = false;
	let showKnowledgeModal = false;
	let currentChatTitle = "";
	let viewMode: "chat" | "knowledge" | "tags" = "chat";
	
	// Track document references for each message
	let messageDocumentReferences: Map<string, DocumentReference[]> = new Map();
	
	// Drag and drop state
	let isDragOver = false;
	let uploadingFiles: Array<{name: string, progress: number, status: 'uploading' | 'success' | 'error'}> = [];

	// Notification system
	let notifications: Array<{
		id: number;
		message: string;
		type: "success" | "error" | "info";
	}> = [];
	let notificationId = 0;

	onMount(async () => {
		// Use server-provided data instead of making client-side API calls
		chats = data.chats || [];
		console.log("Loaded chats from server:", chats);
	});

	async function reloadChats() {
		try {
			const response = await fetch('/api/v1/chats');
			if (response.ok) {
				const loadedChats = await response.json();
				if (Array.isArray(loadedChats)) {
					chats = loadedChats;
				}
			}
		} catch (error) {
			console.error('Failed to reload chats:', error);
		}
	}

	async function reloadDocuments() {
		try {
			const response = await fetch('/api/v1/documents');
			if (response.ok) {
				const loadedDocuments = await response.json();
				if (Array.isArray(loadedDocuments)) {
					data.documents = loadedDocuments;
					showNotification('Knowledge base refreshed', 'info');
				}
			}
		} catch (error) {
			console.error('Failed to reload documents:', error);
		}
	}

	function showNotification(
		message: string,
		type: "success" | "error" | "info" = "info",
	) {
		const id = ++notificationId;
		notifications = [...notifications, { id, message, type }];
	}

	function removeNotification(id: number) {
		notifications = notifications.filter((n) => n.id !== id);
	}

	const generateUUID = () => {
		if (crypto.randomUUID) {
			return crypto.randomUUID();
		}
		// Fallback implementation
		return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
			/[xy]/g,
			function (c) {
				const r = (Math.random() * 16) | 0;
				const v = c == "x" ? r : (r & 0x3) | 0x8;
				return v.toString(16);
			},
		);
	};

	async function handleSendMessage(
		event: CustomEvent<{ content: string }>,
	) {
		console.log("BEfore calling random UUID");
		const userMessage: Message = {
			id: generateUUID(),
			content: event.detail.content,
			role: "user",
			timestamp: new Date(),
			chat_id: currentChatId || "",
		};

		messages = [...messages, userMessage];
		isLoading = true;
		streamingMessage = "";

		try {
			console.log("Sending message to backend");

			// Use proxy to call backend service (streaming needs direct connection)
			const response = await fetch("/api/v1/chat", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					message: event.detail.content,
					chat_id: currentChatId || null,
				}),
			});

			console.log(
				"Message response:",
				response.status,
				response.statusText,
			);

			if (!response.ok) {
				throw new Error(
					`Failed to send message: ${response.status} ${response.statusText}`,
				);
			}

			if (!response.body) {
				throw new Error("No response body received");
			}

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = "";

			let assistantMessage: Message | null = null;

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				// Decode the bytes to text and add to buffer
				buffer += decoder.decode(value, {
					stream: true,
				});

				// Process complete lines from the buffer
				const lines = buffer.split("\n");
				buffer = lines.pop() || ""; // Keep the incomplete line in the buffer

				for (const line of lines) {
					if (line.startsWith("data: ")) {
						try {
							const jsonStr =
								line.slice(6); // Remove 'data: '
							if (
								jsonStr.trim() ===
								""
							)
								continue; // Skip empty data lines

							const streamResponse: StreamResponse =
								JSON.parse(
									jsonStr,
								);
							console.log(
								"Parsed stream response:",
								streamResponse,
							);

							if (
								streamResponse.type ===
									"content" &&
								streamResponse.content
							) {
								streamingMessage +=
									streamResponse.content;
							} else if (
								streamResponse.type ===
								"done"
							) {
								// Create the final assistant message
								assistantMessage =
									{
										id:
											streamResponse.message_id ||
											generateUUID(),
										content: streamingMessage,
										role: "assistant",
										timestamp: new Date(),
										chat_id:
											streamResponse.chat_id ||
											currentChatId ||
											"",
									};

								// Store document references if available
								if (streamResponse.document_references && assistantMessage.id) {
									messageDocumentReferences.set(assistantMessage.id, streamResponse.document_references);
									// Force reactivity update
									messageDocumentReferences = messageDocumentReferences;
								}

								messages = [
									...messages,
									assistantMessage,
								];
								streamingMessage =
									"";

								// Update chat ID if this was a new chat
								if (
									streamResponse.chat_id &&
									!currentChatId
								) {
									currentChatId =
										streamResponse.chat_id;
								}
							}
						} catch (error) {
							console.error(
								"Error parsing stream response:",
								error,
							);
						}
					}
				}
			}

			// Reload chats to update sidebar
			await reloadChats();
			console.log("Message sending completed");
		} catch (error) {
			console.error("Failed to send message:", error);
			console.error("Error type:", error.constructor.name);
			console.error("Error message:", error.message);
			console.error("Full error object:", error);

			// Show user-friendly error message
			showNotification(
				`Failed to send message: ${error.message || "Network error"}`,
				"error",
			);
			streamingMessage = "";
		} finally {
			isLoading = false;
		}
	}

	async function handleNewChat() {
		// Switch to chat view if we're in knowledge base view
		if (viewMode === "knowledge") {
			viewMode = "chat";
		}

		try {
			// Create a new chat on the server
			const response = await fetch("/api/v1/chats", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					title: "New Chat",
				}),
			});

			if (!response.ok) {
				throw new Error(
					`Failed to create chat: ${response.status}`,
				);
			}

			const newChat = await response.json();
			console.log("Created new chat:", newChat);

			// Set the new chat as current
			currentChatId = newChat.id;
			currentChatTitle = newChat.title;
			messages = [];
			streamingMessage = "";

			// Add the new chat to the chats list at the beginning
			chats = [newChat, ...chats];
		} catch (error) {
			console.error("Failed to create new chat:", error);
			showNotification("Failed to create new chat", "error");

			// Fallback: just clear current state without server call
			currentChatId = null;
			messages = [];
			streamingMessage = "";
		}
	}

	async function handleSelectChat(event: CustomEvent<{ id: string }>) {
		console.log(
			"[handleSelectChat] Event triggered with ID:",
			event.detail.id,
		);

		// Switch to chat view if we're in knowledge base view
		if (viewMode === "knowledge") {
			viewMode = "chat";
		}

		currentChatId = event.detail.id;
		streamingMessage = "";

		try {
			console.log(
				"[handleSelectChat] Loading chat messages for:",
				event.detail.id,
			);

			// Use direct API call through proxy
			const response = await fetch(
				`/api/v1/chats/${event.detail.id}`,
			);

			console.log(
				"[handleSelectChat] Response status:",
				response.status,
			);

			if (!response.ok) {
				throw new Error(
					`Failed to load chat: ${response.status}`,
				);
			}

			// Direct JSON parsing - no SvelteKit serialization issues
			const chat = await response.json();
			console.log("[handleSelectChat] Raw chat data:", chat);
			messages = chat.messages || [];
			currentChatTitle = chat.title || "";
			console.log(
				"[handleSelectChat] Set messages:",
				messages.length,
				"messages",
			);
			console.log(
				"[handleSelectChat] Set title:",
				currentChatTitle,
			);
			console.log(
				"[handleSelectChat] Messages array:",
				messages,
			);

			// Force reactivity update
			messages = [...messages];
		} catch (error) {
			console.error("[handleSelectChat] Error:", error);
			showNotification(
				"Failed to load chat messages",
				"error",
			);
			messages = [];
		}
	}

	async function handleMessageDeleted(event: CustomEvent<{ messageId: string }>) {
		// Remove the message from the local messages array
		messages = messages.filter(msg => msg.id !== event.detail.messageId);
		
		// Also remove from document references if it exists
		messageDocumentReferences.delete(event.detail.messageId);
		
		// Force reactivity update
		messages = [...messages];
		
		showNotification("Message deleted successfully", "success");
	}

	async function handleDeleteChat(event: CustomEvent<{ id: string }>) {
		try {
			console.log("Deleting chat:", event.detail.id);

			const response = await fetch(
				`/api/v1/chats/${event.detail.id}`,
				{
					method: "DELETE",
				},
			);

			if (!response.ok) {
				throw new Error(
					`Failed to delete chat: ${response.status}`,
				);
			}

			// Remove from local state
			chats = chats.filter(
				(chat) => chat.id !== event.detail.id,
			);

			// Clear current chat if it was deleted
			if (currentChatId === event.detail.id) {
				await handleNewChat();
			}
		} catch (error) {
			console.error("Failed to delete chat:", error);
		}
	}

	function handleToggleMinimize() {
		isSidebarMinimized = !isSidebarMinimized;
	}

	async function handleSuggestedPrompt(prompt: string) {
		await handleSendMessage(
			new CustomEvent("send", {
				detail: { content: prompt },
			}),
		);
	}

	async function handleSaveToKnowledge() {
		if (!currentChatId) {
			showNotification("No chat selected to save", "error");
			return;
		}

		showKnowledgeModal = true;
	}

	async function handleSaveEditedKnowledge(
		event: CustomEvent<{
			title: string;
			content: any;
			mode: string;
		}>,
	) {
		if (!currentChatId) {
			return;
		}

		try {
			const { title, content, mode } = event.detail;

			const body: any = {
				title,
				save_mode:
					mode === "document"
						? "content"
						: "messages",
			};

			if (typeof content === "string") {
				body.content = content;
			} else {
				body.content = content;
			}

			const response = await fetch(
				`/api/v1/chats/${currentChatId}/save-to-knowledge`,
				{
					method: "POST",
					headers: {
						"Content-Type":
							"application/json",
					},
					body: JSON.stringify(body),
				},
			);

			if (!response.ok) {
				throw new Error(
					`Failed to save: ${response.status}`,
				);
			}

			const result = await response.json();

			showNotification(
				`Successfully saved "${title}" to knowledge base! Created ${result.chunks_created} chunks.`,
				"success",
			);
			showKnowledgeModal = false;
		} catch (error) {
			console.error(
				"Failed to save chat to knowledge:",
				error,
			);
			showNotification(
				"Failed to save chat to knowledge base",
				"error",
			);
		}
	}

	function handleCancelKnowledgeEdit() {
		showKnowledgeModal = false;
	}

	function toggleViewMode() {
		console.log("[toggleViewMode] Current viewMode:", viewMode);
		viewMode = viewMode === "chat" ? "knowledge" : "chat";
		console.log("[toggleViewMode] New viewMode:", viewMode);
	}

	function toggleTagsMode() {
		viewMode = viewMode === "tags" ? "chat" : "tags";
	}

	// Drag and drop handlers
	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		
		// Check if files are being dragged
		if (event.dataTransfer?.types.includes('Files')) {
			isDragOver = true;
		}
	}

	function handleDragLeave(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		
		// Only hide drag overlay if leaving the main container
		const rect = event.currentTarget.getBoundingClientRect();
		const x = event.clientX;
		const y = event.clientY;
		
		if (x < rect.left || x >= rect.right || y < rect.top || y >= rect.bottom) {
			isDragOver = false;
		}
	}

	function handleDrop(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		isDragOver = false;

		const files = event.dataTransfer?.files;
		if (files && files.length > 0) {
			handleFileUploads(Array.from(files));
		}
	}

	async function handleFileUploads(files: File[]) {
		// Filter for supported file types
		const allowedTypes = [
			'application/pdf',
			'text/plain', 
			'text/markdown',
			'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
		];

		const validFiles = files.filter(file => {
			if (!allowedTypes.includes(file.type)) {
				showNotification(`File type not supported: ${file.name}`, 'error');
				return false;
			}
			if (file.size > 50 * 1024 * 1024) { // 50MB limit
				showNotification(`File too large: ${file.name}`, 'error');
				return false;
			}
			return true;
		});

		if (validFiles.length === 0) return;

		// Initialize upload tracking
		uploadingFiles = validFiles.map(file => ({
			name: file.name,
			progress: 0,
			status: 'uploading' as const
		}));

		// Upload files using existing multi-file upload endpoint
		const formData = new FormData();
		validFiles.forEach(file => {
			formData.append('files', file);
		});

		try {
			const response = await fetch('/api/v1/documents/upload-multiple', {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				throw new Error(`Upload failed: ${response.status}`);
			}

			const result = await response.json();
			
			// Update upload status
			uploadingFiles = uploadingFiles.map(file => ({
				...file,
				progress: 100,
				status: 'success' as const
			}));

			showNotification(`Successfully uploaded ${result.uploads.length} files`, 'success');
			
			// Auto-reference uploaded documents in current message (Step 9)
			const successfulUploads = result.uploads.filter(upload => upload.status === 'processing');
			if (successfulUploads.length > 0) {
				handleAutoReferenceDocuments(successfulUploads);
				
				// Reload documents after a delay to allow background processing
				setTimeout(async () => {
					await reloadDocuments();
				}, 3000); // Wait 3 seconds for processing
			}
			
		} catch (error) {
			console.error('Upload failed:', error);
			uploadingFiles = uploadingFiles.map(file => ({
				...file,
				status: 'error' as const
			}));
			showNotification('Upload failed', 'error');
		}

		// Clear upload status after 3 seconds
		setTimeout(() => {
			uploadingFiles = [];
		}, 3000);
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
</script>

<div
	class="flex h-screen bg-gradient-to-br from-slate-50 to-blue-50/30 p-4 gap-4"
>
	<!-- Sidebar -->
	<div
		class="transition-all duration-300"
		class:w-80={!isSidebarMinimized}
		class:w-16={isSidebarMinimized}
	>
		<Sidebar
			bind:isMinimized={isSidebarMinimized}
			{chats}
			{currentChatId}
			on:newChat={handleNewChat}
			on:selectChat={handleSelectChat}
			on:deleteChat={handleDeleteChat}
			on:toggleMinimize={handleToggleMinimize}
			on:toggleKnowledgeBase={toggleViewMode}
			on:toggleTags={toggleTagsMode}
		/>
	</div>

	<!-- Main Content Area -->
	<div
		class="flex-1 {viewMode === 'knowledge'
			? 'flex'
			: 'flex flex-col'} bg-white rounded-2xl shadow-xl shadow-slate-200/60 border border-white/20 backdrop-blur-sm overflow-hidden relative"
		style="height: calc(100vh - 2rem);"
		on:dragover={handleDragOver}
		on:dragleave={handleDragLeave}
		on:drop={handleDrop}
	>
		{#if viewMode === "knowledge"}
			<!-- Knowledge Base View -->
			<KnowledgeBase
				documents={data.documents || []}
				on:close={() => (viewMode = "chat")}
				on:notification={(e) =>
					showNotification(
						e.detail.message,
						e.detail.type,
					)}
			/>
		{:else if viewMode === "tags"}
			<!-- Tag Management View -->
			<TagManager
				on:close={() => (viewMode = "chat")}
				on:notification={(e) =>
					showNotification(
						e.detail.message,
						e.detail.type,
					)}
			/>
		{:else}
			<!-- Chat View -->

			<!-- Chat Header (only show when there are messages) -->
			{#if currentChatId && messages.length > 0}
				<div
					class="flex items-center justify-between px-6 py-3 border-b border-gray-100 bg-gray-50/50"
				>
					<div class="text-sm text-gray-600">
						Current conversation ({messages.length}
						messages)
					</div>
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
			{/if}

			<!-- Chat Messages -->
			<div class="flex-1 overflow-y-auto">
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
								class="text-2xl font-semibold text-gray-900 mb-4"
							>
								Welcome to
								SecondBrain
							</h2>
							<p
								class="text-base text-gray-600 mb-8 leading-relaxed"
							>
								Your intelligent
								assistant that
								learns with you,
								curates your
								knowledge and
								helps you make
								sense of the
								world.
							</p>

							<p
								class="text-sm text-gray-500"
							>
								AI responses may
								contain errors.
								Please verify
								important
								information.
							</p>
						</div>
					</div>
				{:else}
					<div class="pb-32">
						{#each messages as message (message.id)}
							<ChatMessage
								{message}
								documentReferences={messageDocumentReferences.get(message.id) || []}
								on:messageDeleted={handleMessageDeleted}
							/>
						{/each}

						{#if isLoading}
							<LoadingIndicator
								type="typing"
							/>
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
		{/if}

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
</div>

<!-- Knowledge Edit Modal -->
{#if showKnowledgeModal}
	<KnowledgeEditModal
		{messages}
		chatTitle={currentChatTitle}
		chatId={currentChatId || ''}
		on:save={handleSaveEditedKnowledge}
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
