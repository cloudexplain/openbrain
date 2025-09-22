<script lang="ts">
	import { onMount, createEventDispatcher } from "svelte";
	import { marked } from "marked";
	import type {
		Document,
		DocumentDetail,
		DocumentWithChunks,
		DocumentChunk,
	} from "$lib/api";
	import PushNotification from "./PushNotification.svelte";
	import TagSelector from "./TagSelector.svelte";
	import TipTapEditor from "./TipTapEditor.svelte";
	import { invalidateAll } from "$app/navigation";
	import { authService } from "$lib/stores/auth";

	const dispatch = createEventDispatcher();

	// Auto-resize textarea action
	function autoResize(node: HTMLTextAreaElement) {
		function resize() {
			node.style.height = "auto";
			// Set min height to 100px, but expand as needed
			const scrollHeight = node.scrollHeight;
			node.style.height = Math.max(100, scrollHeight) + "px";
		}

		// Initial resize
		resize();

		// Resize on input
		node.addEventListener("input", resize);

		return {
			destroy() {
				node.removeEventListener("input", resize);
			},
		};
	}

	export let documents: Document[] = [];
	export let highlightChunks: string[] = [];
	export let highlightPages: number[] = [];
	let selectedDocument: DocumentDetail | null = null;
	let selectedDocumentChunks: DocumentWithChunks | null = null;

	// Chunk data for highlighting
	let chunkData: any[] = [];
	let highlightedContent = "";
	let isLoading = false;
	let searchQuery = "";
	let documentLoading = false;
	let parsedContent = "";
	let showUploadModal = false;
	let uploadLoading = false;
	let uploadedFiles: File[] = [];
	let isDragging = false;
	let uploadProgress: {
		[key: string]: { progress: number; status: string };
	} = {};
	let isEditMode = false;
	let editedChunks: DocumentChunk[] = [];
	let editedTitle = "";
	let editedContent = ""; // Single unified content for editing
	let hasChanges = false;
	let displayMode: "formatted" | "raw" = "formatted"; // Display mode toggle

	// Cache for loaded documents to avoid re-fetching
	let documentCache: Map<string, DocumentDetail> = new Map();
	let showDeleteModal = false;
	let documentToDelete: DocumentDetail | null = null;

	// PDF viewer state
	let viewMode: "raw" | "pdf" = "raw";
	let isPdfDocument = false;

	// Placeholder for uploading files
	let uploadingFiles: { name: string; id: number }[] = [];
	let nextUploadId = 0;

	// Reactive logic to remove placeholders when documents are loaded
	$: {
		if (uploadingFiles.length > 0 && documents.length > 0) {
			const documentTitles = new Set(documents.map((d) => d.title));
			const stillUploading = uploadingFiles.filter((file) => {
				// Check against original name and name without extension
				const baseName = file.name.includes(".")
					? file.name.substring(0, file.name.lastIndexOf("."))
					: file.name;
				return !documentTitles.has(file.name) && !documentTitles.has(baseName);
			});

			if (stillUploading.length < uploadingFiles.length) {
				uploadingFiles = stillUploading;
			}
		}
	}

	// Push notifications
	let pushNotifications: Array<{
		id: number;
		message: string;
		type: "success" | "error" | "info" | "processing";
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
		documents = documents.sort(
			(a, b) =>
				new Date(b.created_at).getTime() -
				new Date(a.created_at).getTime(),
		);
	}

	async function loadDocuments() {
		// Clear document cache when refreshing list
		documentCache.clear();
		// Refresh documents from server
		await invalidateAll();
	}

	async function selectDocument(doc: Document) {
		// Reset PDF state
		isPdfDocument = false;

		// Check cache first
		if (documentCache.has(doc.id)) {
			selectedDocument = documentCache.get(doc.id) || null;
			if (selectedDocument) {
				parsedContent = marked.parse(
					selectedDocument.content,
				) as string;
				// Check if it's a PDF document and set view mode accordingly
				isPdfDocument =
					selectedDocument.file_type ===
					"application/pdf";
				viewMode = isPdfDocument ? "pdf" : "raw";

				// Load chunk data for highlighting if needed
				await loadChunkDataForHighlighting();
			}
			return;
		}

		documentLoading = true;
		try {
			const response = await fetch(
				`/api/v1/documents/${doc.id}`,
			);

			if (!response.ok) {
				throw new Error(
					`Failed to load document: ${response.status}`,
				);
			}

			selectedDocument = await response.json();

			// Cache the document for future use
			if (selectedDocument) {
				documentCache.set(doc.id, selectedDocument);
				parsedContent = marked.parse(
					selectedDocument.content,
				) as string;
				// Check if it's a PDF document and set view mode accordingly
				isPdfDocument =
					selectedDocument.file_type ===
					"application/pdf";
				viewMode = isPdfDocument ? "pdf" : "raw";

				// Load chunk data for highlighting if needed
				await loadChunkDataForHighlighting();
			}
		} catch (error) {
			console.error("Failed to load document:", error);
			showPushNotification(
				"Failed to load document",
				"error",
			);
		} finally {
			documentLoading = false;
		}
	}

	function formatDate(dateString: string) {
		const date = new Date(dateString);
		return date.toLocaleDateString("en-US", {
			month: "short",
			day: "numeric",
			year: "numeric",
			hour: "2-digit",
			minute: "2-digit",
		});
	}

	function getSourceIcon(sourceType: string) {
		switch (sourceType) {
			case "chat":
				return "💬";
			case "file":
				return "📄";
			case "url":
				return "🌐";
			default:
				return "📋";
		}
	}

	$: filteredDocuments = documents.filter(
		(doc) =>
			doc.title
				.toLowerCase()
				.includes(searchQuery.toLowerCase()) ||
			doc.source_type
				.toLowerCase()
				.includes(searchQuery.toLowerCase()),
	);

	function showPushNotification(
		message: string,
		type: "success" | "error" | "info" | "processing" = "info",
		duration: number = 3000,
	) {
		const id = ++notificationId;
		pushNotifications = [
			...pushNotifications,
			{ id, message, type, duration },
		];

		// Return ID so we can remove specific notifications
		return id;
	}

	function removePushNotification(id: number) {
		pushNotifications = pushNotifications.filter(
			(n) => n.id !== id,
		);
	}

	async function enterEditMode() {
		if (!selectedDocument) return;

		isEditMode = true;
		documentLoading = true;

		try {
			// Use direct API call through proxy (same pattern as chat loading)
			const response = await fetch(
				`/api/v1/documents/${selectedDocument.id}/chunks`,
			);

			if (!response.ok) {
				throw new Error(
					`Failed to load chunks: ${response.status}`,
				);
			}

			// Direct JSON parsing - no SvelteKit serialization issues
			selectedDocumentChunks = await response.json();
			console.log(
				"Document chunks loaded:",
				selectedDocumentChunks,
			);

			editedChunks = JSON.parse(
				JSON.stringify(selectedDocumentChunks.chunks),
			); // Deep clone
			editedTitle = selectedDocumentChunks.title;

			// Combine all chunks into single content for unified editing
			editedContent = editedChunks
				.map((chunk) => chunk.content)
				.join("\n\n");

			hasChanges = false;
		} catch (error) {
			console.error("Failed to load document chunks:", error);
			showPushNotification(
				"Failed to load document for editing",
				"error",
			);
			isEditMode = false;
		} finally {
			documentLoading = false;
		}
	}

	function exitEditMode() {
		isEditMode = false;
		selectedDocumentChunks = null;
		editedChunks = [];
		editedTitle = "";
		editedContent = "";
		hasChanges = false;
	}

	function closeDocument() {
		selectedDocument = null;
		viewMode = "raw";
		isPdfDocument = false;
		chunkData = [];
		highlightedContent = "";
	}

	async function loadChunkDataForHighlighting() {
		if (!selectedDocument || !highlightChunks.length) {
			highlightedContent = selectedDocument?.content || "";
			return;
		}

		try {
			const chunkUrl = `/api/v1/documents/${selectedDocument.id}/chunks?chunk_ids=${highlightChunks.join(",")}`;
			console.log(
				"Loading chunk data for highlighting:",
				chunkUrl,
			);

			const response = await fetch(chunkUrl, {
				headers: {
					Authorization: `Bearer ${localStorage.getItem("access_token")}`,
					"Content-Type": "application/json",
				},
			});

			if (response.ok) {
				const data = await response.json();
				chunkData = data.chunks || [];
				console.log("Loaded chunk data:", chunkData);

				// Apply highlights to raw content
				if (selectedDocument.content) {
					highlightedContent = highlightTextInRaw(
						selectedDocument.content,
						chunkData,
					);
				}
			} else {
				console.error(
					"Failed to load chunk data:",
					response.status,
				);
				highlightedContent =
					selectedDocument?.content || "";
			}
		} catch (err) {
			console.error("Error loading chunk data:", err);
			highlightedContent = selectedDocument?.content || "";
		}
	}

	function highlightTextInRaw(content: string, chunks: any[]): string {
		if (!chunks.length) return content;

		let highlightedText = content;

		// Sort chunks by content length (longest first) to avoid partial matches
		const sortedChunks = [...chunks].sort((a, b) => {
			const aText = a.content || a.chunk_text || a.text || "";
			const bText = b.content || b.chunk_text || b.text || "";
			return bText.length - aText.length;
		});

		sortedChunks.forEach((chunk, index) => {
			const chunkText =
				chunk.content ||
				chunk.chunk_text ||
				chunk.text ||
				"";
			if (!chunkText.trim()) return;

			// Use fuzzy matching - look for the chunk text (allowing for minor variations)
			const normalizedChunkText = chunkText
				.toLowerCase()
				.trim();
			const normalizedContent = highlightedText.toLowerCase();

			// Find the chunk text in the content
			const chunkIndex =
				normalizedContent.indexOf(normalizedChunkText);

			if (chunkIndex !== -1) {
				// Get the actual text from the original content (preserving case)
				const actualText = highlightedText.substring(
					chunkIndex,
					chunkIndex + chunkText.length,
				);

				// Replace with highlighted version
				const highlightedChunk = `<mark class="chunk-highlight" data-chunk-id="${chunk.id}" data-chunk-index="${index}">${actualText}</mark>`;

				highlightedText =
					highlightedText.substring(
						0,
						chunkIndex,
					) +
					highlightedChunk +
					highlightedText.substring(
						chunkIndex + chunkText.length,
					);
			}
		});

		return highlightedText;
	}

	function handleContentEdit(html: string, markdown: string) {
		if (editedContent !== markdown) {
			editedContent = markdown;
			hasChanges = true;
		}
	}

	function handleTitleEdit(newTitle: string) {
		if (editedTitle !== newTitle) {
			editedTitle = newTitle;
			hasChanges = true;
		}
	}

	async function saveChanges() {
		if (!selectedDocument || !hasChanges) return;

		const savingNotificationId = showPushNotification(
			"Saving changes...",
			"processing",
			0,
		);

		try {
			// Split the unified content back into chunks
			// We'll use a simple strategy: split by double newlines or by max chunk size
			const chunkSize = 1500; // Approximate chunk size in characters
			const paragraphs = editedContent.split("\n\n");
			const newChunks = [];
			let currentChunk = "";

			for (const paragraph of paragraphs) {
				if (
					(currentChunk + "\n\n" + paragraph)
						.length > chunkSize &&
					currentChunk.length > 0
				) {
					// Save current chunk and start new one
					newChunks.push({
						content: currentChunk.trim(),
						id: editedChunks[
							newChunks.length
						]?.id, // Keep existing ID if available
					});
					currentChunk = paragraph;
				} else {
					// Add to current chunk
					currentChunk = currentChunk
						? currentChunk +
							"\n\n" +
							paragraph
						: paragraph;
				}
			}

			// Don't forget the last chunk
			if (currentChunk.trim()) {
				newChunks.push({
					content: currentChunk.trim(),
					id: editedChunks[newChunks.length]?.id,
				});
			}

			// Use direct API call through proxy (same pattern as chat operations)
			const response = await fetch(
				`/api/v1/documents/${selectedDocument.id}/chunks`,
				{
					method: "PUT",
					headers: {
						"Content-Type":
							"application/json",
					},
					body: JSON.stringify({
						title: editedTitle,
						chunks: newChunks, // Send all chunks (full replacement)
					}),
				},
			);

			if (!response.ok) {
				throw new Error(
					`Failed to save: ${response.status}`,
				);
			}

			const result = await response.json();
			console.log("Update result:", result);

			removePushNotification(savingNotificationId);
			showPushNotification(
				"Document updated successfully!",
				"success",
			);

			// Clear cache for this document since it was updated
			if (selectedDocument) {
				documentCache.delete(selectedDocument.id);
			}

			// Reload the document to show updated content
			await selectDocument(selectedDocument);
			exitEditMode();

			// Refresh document list to update title if changed
			await loadDocuments();
		} catch (error) {
			console.error("Failed to save changes:", error);
			removePushNotification(savingNotificationId);
			showPushNotification("Failed to save changes", "error");
		}
	}

	async function handleFileUpload(event: Event) {
		const target = event.target as HTMLInputElement;
		const files = target.files;

		if (!files || files.length === 0) return;

		// Convert FileList to Array and process
		const fileArray = Array.from(files);
		await processFiles(fileArray);

		// Reset file input
		if (target) {
			target.value = "";
		}
	}

	async function processFiles(files: File[]) {
		if (files.length === 0) return;

		// Validate files
		const allowedTypes = [
			"application/pdf",
			"text/plain",
			"text/markdown",
			"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
		];
		const maxSize = 50 * 1024 * 1024; // 50MB

		const validFiles: File[] = [];
		for (const file of files) {
			if (!allowedTypes.includes(file.type)) {
				showPushNotification(
					`"${file.name}" - Unsupported file type. Supported: PDF, TXT, MD, DOCX`,
					"error",
				);
				continue;
			}
			if (file.size > maxSize) {
				showPushNotification(
					`"${file.name}" - File too large. Maximum size is 50MB.`,
					"error",
				);
				continue;
			}
			validFiles.push(file);
		}

		if (validFiles.length === 0) return;

		// Add to uploading files list for placeholder UI
		const newUploads = validFiles.map((file) => ({
			name: file.name,
			id: nextUploadId++,
		}));
		uploadingFiles = [...uploadingFiles, ...newUploads];

		uploadLoading = true;
		uploadedFiles = validFiles;

		// Show processing notification
		const processingNotificationId = showPushNotification(
			`Uploading ${validFiles.length} file${validFiles.length > 1 ? "s" : ""}...`,
			"processing",
			0,
		); // Duration 0 = stays until removed

		try {
			// Process files in parallel if multiple or use single upload for one file
			if (validFiles.length === 1) {
				// Single file upload
				const formData = new FormData();
				formData.append("file", validFiles[0]);

				const fetchResponse = await fetch(
					"/api/v1/documents/upload",
					{
						method: "POST",
						headers: authService.getAuthHeaders(),
						body: formData,
					},
				);

				if (!fetchResponse.ok) {
					throw new Error(
						`Upload failed: ${fetchResponse.status} ${fetchResponse.statusText}`,
					);
				}

				const response = await fetchResponse.json();
				showPushNotification(
					`"${validFiles[0].name}" uploaded! Processing in background...`,
					"success",
					3000,
				);
			} else {
				// Multiple file upload - upload sequentially to show progress
				let successCount = 0;
				let failCount = 0;

				for (let i = 0; i < validFiles.length; i++) {
					const file = validFiles[i];
					uploadProgress[file.name] = {
						progress:
							(i /
								validFiles.length) *
							100,
						status: "uploading",
					};

					try {
						const formData = new FormData();
						formData.append("file", file);

						const fetchResponse =
							await fetch(
								"/api/v1/documents/upload",
								{
									method: "POST",
									headers: authService.getAuthHeaders(),
									body: formData,
								},
							);

						if (!fetchResponse.ok) {
							throw new Error(
								`Upload failed for ${file.name}`,
							);
						}

						uploadProgress[file.name] = {
							progress: 100,
							status: "completed",
						};
						successCount++;
					} catch (error) {
						uploadProgress[file.name] = {
							progress: 100,
							status: "failed",
						};
						failCount++;
						console.error(
							`Failed to upload ${file.name}:`,
							error,
						);
					}
				}

				if (successCount > 0) {
					showPushNotification(
						`Successfully uploaded ${successCount} file${successCount > 1 ? "s" : ""}${failCount > 0 ? `, ${failCount} failed` : ""}`,
						"success",
						3000,
					);
				} else {
					showPushNotification(
						`Failed to upload files`,
						"error",
						3000,
					);
				}
			}

			// Remove processing notification
			removePushNotification(processingNotificationId);

			// Close modal
			showUploadModal = false;
			uploadedFiles = [];
			uploadProgress = {};

			// Wait a bit then refresh document list to see if processing is complete
			setTimeout(async () => {
				await loadDocuments();
				showPushNotification(
					`"${file.name}" processing complete!`,
					"success",
					3000,
				);
			}, 5000); // Check after 5 seconds

			// Continue checking periodically
			const checkInterval = setInterval(async () => {
				await loadDocuments();
			}, 3000);

			// Stop checking after 30 seconds
			setTimeout(() => clearInterval(checkInterval), 30000);
		} catch (error) {
			console.error("Failed to upload documents:", error);
			removePushNotification(processingNotificationId);
			showPushNotification(
				"Failed to upload documents",
				"error",
				5000,
			);
		} finally {
			uploadLoading = false;
			uploadedFiles = [];
			uploadProgress = {};
		}
	}

	function handleDragOver(event: DragEvent) {
		event.preventDefault();
		isDragging = true;
	}

	function handleDragLeave(event: DragEvent) {
		event.preventDefault();
		isDragging = false;
	}

	async function handleDrop(event: DragEvent) {
		event.preventDefault();
		isDragging = false;

		const files = event.dataTransfer?.files;
		if (!files || files.length === 0) return;

		// Convert FileList to Array and process
		const fileArray = Array.from(files);
		await processFiles(fileArray);
	}

	function confirmDeleteDocument(doc: DocumentDetail) {
		documentToDelete = doc;
		showDeleteModal = true;
	}

	async function deleteDocument() {
		if (!documentToDelete) return;

		const deletingNotificationId = showPushNotification(
			`Deleting "${documentToDelete.title}"...`,
			"processing",
			0,
		);

		try {
			const response = await fetch(
				`/api/v1/documents/${documentToDelete.id}`,
				{
					method: "DELETE",
				},
			);

			if (!response.ok) {
				throw new Error(
					`Delete failed: ${response.status} ${response.statusText}`,
				);
			}

			removePushNotification(deletingNotificationId);
			showPushNotification(
				`"${documentToDelete.title}" deleted successfully`,
				"success",
				3000,
			);

			// Clear from cache if it exists
			documentCache.delete(documentToDelete.id);

			// Clear selected document if it was the one being deleted
			if (selectedDocument?.id === documentToDelete.id) {
				closeDocument();
			}

			// Close delete modal
			showDeleteModal = false;
			documentToDelete = null;

			// Refresh document list
			await loadDocuments();
		} catch (error) {
			console.error("Failed to delete document:", error);
			removePushNotification(deletingNotificationId);
			showPushNotification(
				"Failed to delete document",
				"error",
				5000,
			);
		}
	}
</script>

<div class="flex h-full w-full bg-white rounded-xl shadow-lg overflow-hidden">
	<!-- Document List -->
	<div class="w-80 border-r border-gray-200 flex flex-col h-full">
		<!-- Fixed Header -->
		<div
			class="p-4 border-b border-gray-200 bg-white z-10 flex-shrink-0"
		>
			<div class="flex items-center justify-between mb-3">
				<h2 class="text-lg font-semibold text-gray-800">
					Knowledge Base
				</h2>
				<button
					on:click={() => dispatch("close")}
					class="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
					title="Back to Chat"
				>
					<svg
						class="w-5 h-5 text-gray-600"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						></path>
					</svg>
				</button>
			</div>

			<!-- Upload Button -->
			<button
				on:click={() => (showUploadModal = true)}
				class="w-full mb-3 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white rounded-lg transition-all duration-200 text-sm font-medium shadow-md hover:shadow-lg"
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
						d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
					/>
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
				<div
					class="flex items-center justify-center h-64 text-gray-500"
				>
					<div
						class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"
					></div>
				</div>
			{:else if filteredDocuments.length === 0 && uploadingFiles.length === 0}
				<div class="text-center py-12 px-4 text-gray-500">
					<div class="text-4xl mb-3">📚</div>
					<div class="text-sm font-medium">
						No documents found
					</div>
					<div class="text-xs mt-1">
						Save chats to build your
						knowledge base
					</div>
				</div>
			{:else}
				{#each uploadingFiles as file}
					<div
						class="w-full px-4 py-3 text-left border-b border-gray-100 opacity-60 pointer-events-none"
					>
						<div class="flex items-start gap-3">
							<div class="text-xl mt-0.5">
								📄
							</div>
							<div class="flex-1 min-w-0">
								<div
									class="font-medium text-sm text-gray-900 truncate"
								>
									{file.name}
								</div>
								<div
									class="flex items-center gap-2 mt-1 text-xs text-gray-500"
								>
									<div
										class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500"
									></div>
									<span>Uploading...</span>
								</div>
							</div>
						</div>
					</div>
				{/each}
				{#each filteredDocuments as doc}
					<button
						on:click={() =>
							selectDocument(doc)}
						class="w-full px-4 py-3 hover:bg-gray-50 transition-colors text-left border-b border-gray-100 {selectedDocument?.id ===
						doc.id
							? 'bg-blue-50'
							: ''}"
					>
						<div
							class="flex items-start gap-3"
						>
							<div
								class="text-xl mt-0.5"
							>
								{getSourceIcon(
									doc.source_type,
								)}
							</div>
							<div
								class="flex-1 min-w-0"
							>
								<div
									class="font-medium text-sm text-gray-900 truncate"
								>
									{doc.title}
								</div>
								<div
									class="flex items-center gap-2 mt-1 text-xs text-gray-500"
								>
									<span
										class="capitalize"
										>{doc.source_type}</span
									>
									<span
										>•</span
									>
									<span
										>{doc.chunk_count}
										chunks</span
									>
								</div>
								<div
									class="text-xs text-gray-400 mt-1"
								>
									{formatDate(
										doc.created_at,
									)}
								</div>
							</div>
							{#if selectedDocument?.id === doc.id}
								<div
									class="w-1 h-12 bg-blue-500 rounded-full self-center"
								></div>
							{/if}
						</div>
					</button>
				{/each}
			{/if}
		</div>

		<!-- Fixed Footer -->
		<div
			class="p-3 border-t border-gray-200 text-center text-xs text-gray-500 bg-white flex-shrink-0"
		>
			{filteredDocuments.length} document{filteredDocuments.length !==
			1
				? "s"
				: ""} in knowledge base
		</div>
	</div>

	<!-- Document Viewer -->
	<div class="flex-1 flex flex-col h-full">
		{#if documentLoading}
			<div class="flex-1 flex items-center justify-center">
				<div class="text-center">
					<div
						class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"
					></div>
					<div class="text-sm text-gray-500">
						Loading document...
					</div>
				</div>
			</div>
		{:else if selectedDocument}
			<div class="flex flex-col h-full">
				<!-- Document Header -->
				<div
					class="px-6 py-4 border-b border-gray-200 flex-shrink-0"
				>
					<div
						class="flex items-start justify-between"
					>
						<div class="flex-1">
							{#if isEditMode}
								<input
									type="text"
									bind:value={
										editedTitle
									}
									on:input={(
										e,
									) =>
										handleTitleEdit(
											e
												.currentTarget
												.value,
										)}
									class="text-xl font-semibold text-gray-900 bg-transparent border-b-2 border-blue-500 focus:outline-none w-full"
								/>
							{:else}
								<h3
									class="text-xl font-semibold text-gray-900"
								>
									{selectedDocument.title}
								</h3>
							{/if}
							<div
								class="flex items-center gap-3 mt-2 text-sm text-gray-500"
							>
								<span
									class="flex items-center gap-1"
								>
									{getSourceIcon(
										selectedDocument.source_type,
									)}
									<span
										class="capitalize"
										>{selectedDocument.source_type}</span
									>
								</span>
								<span>•</span>
								<span
									>{selectedDocument.chunk_count}
									chunks</span
								>
								<span>•</span>
								<span
									>{formatDate(
										selectedDocument.created_at,
									)}</span
								>
							</div>
						</div>
						<div
							class="flex items-center gap-2"
						>
							{#if !isEditMode}
								<button
									on:click={enterEditMode}
									class="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors font-medium shadow-sm"
									title="Edit document"
								>
									Edit
								</button>
								<button
									on:click={() =>
										confirmDeleteDocument(
											selectedDocument,
										)}
									class="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium shadow-sm"
									title="Delete document"
								>
									Delete
								</button>
							{/if}
							<button
								on:click={() => {
									if (
										isEditMode
									) {
										exitEditMode();
									} else {
										closeDocument();
									}
								}}
								class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
								title={isEditMode
									? "Cancel editing"
									: "Close document"}
							>
								<svg
									class="w-5 h-5 text-gray-500"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M6 18L18 6M6 6l12 12"
									></path>
								</svg>
							</button>
						</div>
					</div>

					<!-- View Toggle -->
					{#if !isEditMode}
						<div
							class="mt-3 flex items-center gap-3"
						>
							<span
								class="text-sm text-gray-600"
								>View:</span
							>
							<div
								class="flex items-center gap-2 bg-gray-100 rounded-lg p-1"
							>
								{#if isPdfDocument}
									<button
										on:click={() =>
											(viewMode =
												"raw")}
										class="px-3 py-1 text-sm rounded-md transition-colors {viewMode ===
										'raw'
											? 'bg-white text-blue-600 shadow-sm'
											: 'text-gray-600 hover:text-gray-800'}"
									>
										Raw
									</button>
									<button
										on:click={() =>
											(viewMode =
												"pdf")}
										class="px-3 py-1 text-sm rounded-md transition-colors {viewMode ===
										'pdf'
											? 'bg-white text-blue-600 shadow-sm'
											: 'text-gray-600 hover:text-gray-800'}"
									>
										PDF
									</button>
								{:else}
									<button
										on:click={() =>
											(displayMode =
												"formatted")}
										class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
										'formatted'
											? 'bg-white text-blue-600 shadow-sm'
											: 'text-gray-600 hover:text-gray-800'}"
									>
										Formatted
									</button>
									<button
										on:click={() =>
											(displayMode =
												"raw")}
										class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
										'raw'
											? 'bg-white text-blue-600 shadow-sm'
											: 'text-gray-600 hover:text-gray-800'}"
									>
										Raw
										Markdown
									</button>
								{/if}
							</div>
						</div>
					{/if}

					<!-- Tags Section -->
					<div class="mt-3">
						<TagSelector
							documentId={selectedDocument.id}
							mode="edit"
							on:error={(e) =>
								showPushNotification(
									e.detail
										.message,
									"error",
								)}
							on:createTag={(e) => {
								// Dispatch event to parent to switch to tag management
								dispatch(
									"switchToTags",
									{
										tagName: e
											.detail
											.name,
									},
								);
							}}
						/>
					</div>
				</div>

				<!-- Document Content -->
				<div
					class="flex-1 overflow-y-auto bg-white custom-scrollbar min-h-0 relative {viewMode ===
					'pdf'
						? 'p-0'
						: 'px-6 py-4'}"
				>
					{#if isEditMode}
						<!-- Display mode toggle for edit mode -->
						<div
							class="mb-4 flex items-center gap-3 sticky top-0 bg-white pb-2 border-b border-gray-200 z-10"
						>
							<span
								class="text-sm text-gray-600"
								>View:</span
							>
							<div
								class="flex items-center gap-2 bg-gray-100 rounded-lg p-1"
							>
								<button
									on:click={() =>
										(displayMode =
											"formatted")}
									class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
									'formatted'
										? 'bg-white text-blue-600 shadow-sm'
										: 'text-gray-600 hover:text-gray-800'}"
								>
									Formatted
								</button>
								<button
									on:click={() =>
										(displayMode =
											"raw")}
									class="px-3 py-1 text-sm rounded-md transition-colors {displayMode ===
									'raw'
										? 'bg-white text-blue-600 shadow-sm'
										: 'text-gray-600 hover:text-gray-800'}"
								>
									Raw
								</button>
							</div>
							<span
								class="text-xs text-gray-500 ml-auto"
							>
								{editedContent.length}
								characters
							</span>
						</div>

						{#if displayMode === "formatted"}
							<!-- TipTap Editor (without instructional text) -->
							<div class="space-y-3">
								<TipTapEditor
									content={editedContent}
									onChange={handleContentEdit}
									placeholder="Start writing your document..."
									height="500px"
									editable={true}
								/>
							</div>
						{:else}
							<!-- Raw markdown view -->
							<div class="space-y-3">
								<div
									class="text-xs text-gray-500"
								>
									Edit raw
									markdown
									syntax.
									Use
									**bold**,
									*italic*,
									#
									headings,
									etc.
								</div>
								<textarea
									value={editedContent}
									on:input={(
										e,
									) =>
										handleContentEdit(
											"",
											e
												.currentTarget
												.value,
										)}
									class="w-full p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
									placeholder="Enter markdown content..."
									style="height: 500px;"
								/>
							</div>
						{/if}
					{:else if !isEditMode}
						{#if viewMode === "pdf" && isPdfDocument && selectedDocument}
							<!-- PDF Viewer -->
							<iframe
								src={`/api/v1/documents/${selectedDocument.id}/pdf`}
								class="absolute inset-0 w-full h-full border-0"
								title="PDF Viewer"
							/>
						{:else if displayMode === "raw"}
							<!-- Raw markdown display (read-only) with highlighting -->
							{#if highlightChunks.length > 0}
								<pre
									class="w-full p-4 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm whitespace-pre-wrap overflow-x-auto">{@html highlightedContent}</pre>
							{:else}
								<pre
									class="w-full p-4 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm whitespace-pre-wrap overflow-x-auto">{selectedDocument?.content ||
										""}</pre>
							{/if}
						{:else}
							<!-- Formatted markdown content -->
							<div
								class="markdown-content prose prose-sm max-w-none
								prose-headings:text-gray-900
								prose-p:text-gray-700
								prose-strong:text-gray-900
								prose-code:text-pink-600 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
								prose-pre:bg-gray-900 prose-pre:text-gray-100
								prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:text-gray-700
								prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
								prose-li:text-gray-700
								prose-hr:border-gray-300"
							>
								{@html parsedContent}
							</div>
						{/if}
					{:else}
						<div
							class="flex items-center justify-center h-full"
						>
							<div
								class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"
							></div>
						</div>
					{/if}
				</div>

				<!-- Document Actions -->
				<div
					class="px-6 py-3 border-t border-gray-200 flex items-center justify-between flex-shrink-0"
				>
					<div class="text-xs text-gray-500">
						{#if isEditMode && hasChanges}
							<span
								class="text-orange-600 font-medium"
								>Unsaved changes</span
							>
						{:else}
							Document ID: {selectedDocument.id.slice(
								0,
								8,
							)}...
						{/if}
					</div>
					<div class="flex gap-2">
						{#if isEditMode}
							<button
								on:click={exitEditMode}
								class="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
							>
								Cancel
							</button>
							<button
								on:click={saveChanges}
								disabled={!hasChanges}
								class="px-3 py-1.5 text-xs rounded-lg transition-colors {hasChanges
									? 'bg-blue-500 hover:bg-blue-600 text-white'
									: 'bg-gray-200 text-gray-400 cursor-not-allowed'}"
							>
								Save Changes
							</button>
						{:else}
							<button
								class="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
								title="Copy content"
								on:click={() => {
									navigator.clipboard.writeText(
										selectedDocument?.content ||
											"",
									);
								}}
							>
								Copy Content
							</button>
						{/if}
					</div>
				</div>
			</div>
		{:else}
			<div
				class="flex-1 flex items-center justify-center text-gray-400"
			>
				<div class="text-center">
					<div class="text-6xl mb-4">📖</div>
					<div class="text-lg font-medium">
						Select a document to view
					</div>
					<div class="text-sm mt-2">
						Choose from your knowledge base
						on the left
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Upload Modal -->
{#if showUploadModal}
	<div
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
	>
		<div
			class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4"
		>
			<div class="p-6">
				<div
					class="flex items-center justify-between mb-4"
				>
					<h3
						class="text-lg font-semibold text-gray-800"
					>
						Upload Document
					</h3>
					<button
						on:click={() =>
							(showUploadModal = false)}
						class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
					>
						<svg
							class="w-5 h-5 text-gray-500"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				</div>

				<div
					class="border-2 border-dashed rounded-lg p-8 text-center transition-colors {isDragging
						? 'border-blue-500 bg-blue-50'
						: 'border-gray-300'}"
					on:dragover={handleDragOver}
					on:dragleave={handleDragLeave}
					on:drop={handleDrop}
				>
					<input
						type="file"
						id="fileUpload"
						accept=".pdf,.txt,.md,.docx"
						multiple
						on:change={handleFileUpload}
						class="hidden"
						disabled={uploadLoading}
					/>

					{#if uploadLoading}
						<div
							class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"
						></div>
						<p
							class="text-sm text-gray-600 mb-3"
						>
							Uploading {uploadedFiles.length}
							file{uploadedFiles.length >
							1
								? "s"
								: ""}...
						</p>
						{#if Object.keys(uploadProgress).length > 0}
							<div
								class="space-y-2 max-h-48 overflow-y-auto"
							>
								{#each Object.entries(uploadProgress) as [filename, progress]}
									<div
										class="text-xs text-left"
									>
										<div
											class="flex items-center justify-between mb-1"
										>
											<span
												class="truncate flex-1"
												>{filename}</span
											>
											<span
												class="ml-2"
											>
												{#if progress.status === "completed"}
													✓
												{:else if progress.status === "failed"}
													✗
												{:else}
													{Math.round(
														progress.progress,
													)}%
												{/if}
											</span>
										</div>
										<div
											class="w-full bg-gray-200 rounded-full h-1.5"
										>
											<div
												class="h-1.5 rounded-full transition-all {progress.status ===
												'failed'
													? 'bg-red-500'
													: progress.status ===
														  'completed'
														? 'bg-green-500'
														: 'bg-blue-500'}"
												style="width: {progress.progress}%"
											></div>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					{:else}
						<svg
							class="w-12 h-12 text-gray-400 mx-auto mb-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
							/>
						</svg>
						<p
							class="text-sm text-gray-600 mb-2"
						>
							{isDragging
								? "Drop files here"
								: "Drag & drop files here or click to browse"}
						</p>
						<p
							class="text-xs text-gray-500 mb-4"
						>
							Supports PDF, TXT, MD,
							and DOCX files (max 50MB
							each)
						</p>
						<label
							for="fileUpload"
							class="inline-flex items-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer transition-colors"
						>
							<svg
								class="w-4 h-4 mr-2"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 4v16m8-8H4"
								></path>
							</svg>
							Select Files
						</label>
					{/if}
				</div>

				<div class="flex justify-end gap-2 mt-6">
					<button
						on:click={() =>
							(showUploadModal = false)}
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

<!-- Delete Confirmation Modal -->
{#if showDeleteModal && documentToDelete}
	<div
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
	>
		<div
			class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4"
		>
			<div class="p-6">
				<div
					class="flex items-center justify-between mb-4"
				>
					<h3
						class="text-lg font-semibold text-gray-800"
					>
						Delete Document
					</h3>
					<button
						on:click={() => {
							showDeleteModal = false;
							documentToDelete = null;
						}}
						class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
					>
						<svg
							class="w-5 h-5 text-gray-500"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				</div>

				<div class="mb-6">
					<div
						class="flex items-center gap-3 mb-3"
					>
						<div
							class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center"
						>
							<svg
								class="w-6 h-6 text-red-600"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
								></path>
							</svg>
						</div>
						<div>
							<p
								class="text-sm text-gray-600"
							>
								Are you sure you
								want to delete
								this document?
							</p>
							<p
								class="font-medium text-gray-900 mt-1"
							>
								"{documentToDelete.title}"
							</p>
						</div>
					</div>
					<div
						class="bg-yellow-50 border border-yellow-200 rounded-lg p-3"
					>
						<p
							class="text-sm text-yellow-800"
						>
							<strong>Warning:</strong
							> This action cannot be undone.
							The document and all its
							content will be permanently
							removed from your knowledge
							base.
						</p>
					</div>
				</div>

				<div class="flex justify-end gap-3">
					<button
						on:click={() => {
							showDeleteModal = false;
							documentToDelete = null;
						}}
						class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
					>
						Cancel
					</button>
					<button
						on:click={deleteDocument}
						class="px-4 py-2 text-sm bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors font-medium"
					>
						Delete Document
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
		font-family: "Monaco", "Courier New", monospace;
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

	/* Chunk highlighting styles */
	:global(.chunk-highlight) {
		background-color: rgba(255, 255, 0, 0.3);
		padding: 2px 4px;
		border-radius: 3px;
		font-weight: inherit;
		font-style: normal;
	}
</style>
