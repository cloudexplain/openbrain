<script lang="ts">
	import { page } from "$app/stores";
	import { onMount } from "svelte";
	import { authService } from "$lib/stores/auth";
	import PDFViewer from "$lib/components/PDFViewer.svelte";

	let { data } = $props();

	let document = $state<any>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let pdfUrl = $state<string | null>(null);
	let pdfViewer = $state<PDFViewer>();

	// Extract highlight parameters from URL using Svelte 5 syntax
	let messageId = $derived($page.url.searchParams.get("messageId"));
	let highlightChunks = $derived(
		$page.url.searchParams.get("chunks")?.split(",") || [],
	);
	let highlightPages = $derived(
		$page.url.searchParams.get("pages")?.split(",").map(Number) ||
			[],
	);

	// Determine if this is highlighting mode or normal viewing mode
	let isHighlightingMode = $derived(
		!!(
			messageId ||
			highlightChunks.length > 0 ||
			highlightPages.length > 0
		),
	);

	// View mode for highlighting
	let viewMode = $state("pdf");

	// Chunk data for highlighting
	let chunkData: any[] = $state([]);
	let highlightedContent = $state("");

	onMount(async () => {
		await loadDocument();
	});

	// Load chunk data when document changes (for highlighting)
	$effect(async () => {
		if (
			document &&
			isHighlightingMode &&
			highlightChunks.length > 0
		) {
			await loadChunkDataForHighlighting();
		}
	});

	async function loadDocument() {
		console.log("🔍 Knowledge page: Starting to load document");
		console.log(
			"🔍 Knowledge page: Document ID from params:",
			$page.params.id,
		);

		try {
			loading = true;
			error = null;

			// Fetch document details
			const docUrl = `/api/v1/documents/${$page.params.id}`;
			console.log(
				"🔍 Knowledge page: Fetching document from:",
				docUrl,
			);

			const response = await fetch(docUrl, {
				headers: authService.getAuthHeaders(),
			});

			console.log(
				"🔍 Knowledge page: Document response status:",
				response.status,
			);

			if (!response.ok) {
				const errorText = await response.text();
				console.error(
					"🔍 Knowledge page: Document fetch failed:",
					response.status,
					errorText,
				);
				throw new Error(
					`Failed to load document: ${response.status} ${errorText}`,
				);
			}

			document = await response.json();
			console.log(
				"🔍 Knowledge page: Document loaded successfully:",
				document,
			);

			// If it's a PDF, get the file URL
			if (document.file_type === "application/pdf") {
				// For now, assume static file serving
				// This will need to be adjusted based on your backend setup
				pdfUrl = `/api/documents/${document.id}/file`;
				console.log(
					"🔍 Knowledge page: PDF URL set to:",
					pdfUrl,
				);
			}
		} catch (err) {
			error =
				err instanceof Error
					? err.message
					: "Failed to load document";
			console.error(
				"🔍 Knowledge page: Error loading document:",
				err,
			);
		} finally {
			loading = false;
			console.log(
				"🔍 Knowledge page: Document loading completed. Loading:",
				loading,
			);
		}
	}

	function handleBackToChat() {
		// If we came from a chat, go back
		if (messageId) {
			window.history.back();
		} else {
			// Otherwise go to main page
			window.location.href = "/";
		}
	}

	function handleChunkClick(
		event: CustomEvent<{ pageNum: number; chunks: any[] }>,
	) {
		const { pageNum, chunks } = event.detail;
		console.log("Clicked on highlighted chunks:", {
			pageNum,
			chunks,
		});
		// Could show a modal or sidebar with chunk details
	}

	async function loadChunkDataForHighlighting() {
		if (!document || !highlightChunks.length) {
			highlightedContent = document?.content || "";
			return;
		}

		try {
			// Load ALL chunks first (like PDF viewer does)
			const allChunksUrl = `/api/v1/documents/${document.id}/chunks`;
			console.log(
				"Loading all chunk data for highlighting:",
				allChunksUrl,
			);

			const response = await fetch(allChunksUrl, {
				headers: authService.getAuthHeaders(),
			});

			if (response.ok) {
				const data = await response.json();
				const allChunks = data.chunks || [];
				console.log("Loaded all chunk data:", allChunks.length, "chunks");

				// Filter to only highlight the specific chunks requested in the URL
				const requestedChunkIds = new Set(highlightChunks);
				console.log("Requested chunk IDs from URL:", highlightChunks);
				
				chunkData = allChunks.filter((chunk) => {
					const chunkId = chunk.id || chunk.chunk_id;
					const isIncluded = requestedChunkIds.has(chunkId);
					console.log(`RAW Highlighting: Chunk ${chunkId} - included: ${isIncluded}`);
					return isIncluded;
				});

				console.log(`RAW Highlighting: Filtered to ${chunkData.length} chunks to highlight`);

				// Apply highlights to raw content
				if (document.content) {
					highlightedContent = highlightTextInRaw(
						document.content,
						chunkData,
					);
				}
			} else {
				console.error(
					"Failed to load chunk data:",
					response.status,
				);
				highlightedContent = document?.content || "";
			}
		} catch (err) {
			console.error("Error loading chunk data:", err);
			highlightedContent = document?.content || "";
		}
	}

	function highlightTextInRaw(content: string, chunks: any[]): string {
		if (!chunks.length) return content;

		console.log(
			"Highlighting raw content with",
			chunks.length,
			"chunks",
		);
		console.log("Content length:", content.length);
		console.log(
			"First few chunks:",
			chunks.slice(0, 3).map((c) => ({
				id: c.id,
				text:
					(
						c.content ||
						c.chunk_text ||
						c.text ||
						""
					).substring(0, 100) + "...",
			})),
		);

		let highlightedText = content;
		let processedRanges: Array<{ start: number; end: number }> = [];

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

			// Clean the chunk text - remove extra whitespace and normalize
			const cleanChunkText = chunkText
				.trim()
				.replace(/\s+/g, " ");
			console.log(
				`Processing chunk ${index}:`,
				cleanChunkText.substring(0, 150) + "...",
			);

			// Try to find exact matches first, then partial matches
			const exactMatch = findExactMatch(
				highlightedText,
				cleanChunkText,
			);

			if (
				exactMatch &&
				!isOverlapping(exactMatch, processedRanges)
			) {
				console.log(
					`Found exact match for chunk ${index} at position ${exactMatch.start}-${exactMatch.end}`,
				);

				// Mark this range as processed
				processedRanges.push(exactMatch);

				// Get the actual text from the original position
				const actualText = highlightedText.substring(
					exactMatch.start,
					exactMatch.end,
				);

				// Replace with highlighted version
				const highlightedChunk = `<mark class="chunk-highlight" data-chunk-id="${chunk.id}" data-chunk-index="${index}">${actualText}</mark>`;

				highlightedText =
					highlightedText.substring(
						0,
						exactMatch.start,
					) +
					highlightedChunk +
					highlightedText.substring(
						exactMatch.end,
					);

				// Adjust remaining ranges for the length change
				const lengthDiff =
					highlightedChunk.length -
					actualText.length;
				processedRanges = processedRanges.map(
					(range) => ({
						start:
							range.start >
							exactMatch.start
								? range.start +
									lengthDiff
								: range.start,
						end:
							range.end >
							exactMatch.start
								? range.end +
									lengthDiff
								: range.end,
					}),
				);
			} else {
				console.log(
					`No suitable match found for chunk ${index}`,
				);
			}
		});

		console.log(
			`Processed ${processedRanges.length} chunks successfully`,
		);
		return highlightedText;
	}

	function findExactMatch(
		content: string,
		searchText: string,
	): { start: number; end: number } | null {
		// Normalize both texts for comparison
		const normalizedContent = content
			.toLowerCase()
			.replace(/\s+/g, " ");
		const normalizedSearch = searchText
			.toLowerCase()
			.replace(/\s+/g, " ");

		const index = normalizedContent.indexOf(normalizedSearch);

		if (index !== -1) {
			// Map back to original content positions
			return {
				start: index,
				end: index + normalizedSearch.length,
			};
		}

		return null;
	}

	function isOverlapping(
		newRange: { start: number; end: number },
		existingRanges: Array<{ start: number; end: number }>,
	): boolean {
		return existingRanges.some(
			(range) =>
				newRange.start < range.end &&
				newRange.end > range.start,
		);
	}
</script>

<div class="min-h-screen bg-gray-50">
	<!-- Header -->
	<div class="bg-white shadow-sm border-b">
		<div class="px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-4">
					<button
						on:click={handleBackToChat}
						class="text-gray-500 hover:text-gray-700"
					>
						<svg
							class="w-6 h-6"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 19l-7-7m0 0l7-7m-7 7h18"
							/>
						</svg>
					</button>

					{#if document}
						<div>
							<h1
								class="text-xl font-semibold text-gray-900"
							>
								{document.title ||
									"Untitled Document"}
							</h1>
							<p
								class="text-sm text-gray-500"
							>
								{document.source_type ===
								"chat"
									? "Chat"
									: document.file_type}
								{#if isHighlightingMode && highlightChunks.length > 0}
									• {highlightChunks.length}
									highlighted
									sections
								{/if}
							</p>

							<!-- View mode toggle for PDF documents in highlighting mode -->
							{#if isHighlightingMode && document.file_type === "application/pdf"}
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
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 p-4 sm:p-6 lg:p-8">
		{#if loading}
			<div class="flex justify-center items-center h-64">
				<div class="text-gray-500">
					Loading document...
				</div>
			</div>
		{:else if error}
			<div class="bg-red-50 p-4 rounded-lg">
				<p class="text-red-800">{error}</p>
			</div>
		{:else if document}
			<!-- Document viewer based on mode and type -->
			{#if isHighlightingMode}
				<!-- HIGHLIGHTING MODE: Show our new highlighting interface -->
				{#if document.source_type === "chat"}
					<!-- Chat document display -->
					<div
						class="bg-white rounded-lg shadow p-6 max-w-4xl mx-auto"
					>
						<div class="prose max-w-none">
							<p
								class="text-gray-600"
							>
								Chat
								conversation
								saved as
								knowledge
							</p>
							<!-- TODO: Display chat messages with highlights -->
						</div>
					</div>
				{:else if document.file_type === "application/pdf"}
					<!-- PDF Highlighting Viewer with Raw/PDF toggle -->
					{#if viewMode === "pdf"}
						<div
							class="bg-white rounded-lg shadow h-screen"
						>
							<PDFViewer
								bind:this={
									pdfViewer
								}
								documentUrl={`/api/v1/documents/${document.id}/file`}
								{highlightChunks}
								{highlightPages}
								documentId={document.id}
								on:chunkClick={handleChunkClick}
							/>
						</div>
					{:else}
						<!-- Raw content with highlighting -->
						<div
							class="bg-white rounded-lg shadow p-6 max-w-4xl mx-auto"
						>
							<div class="mb-4">
								<h2
									class="text-lg font-semibold mb-2"
								>
									Raw
									Content
								</h2>
								<p
									class="text-sm text-gray-600"
								>
									Showing {highlightChunks.length}
									highlighted
									sections
								</p>
							</div>
							<div
								class="raw-content-highlighted"
							>
								<pre
									class="w-full p-4 bg-gray-50 border border-gray-200 rounded-lg font-mono text-sm whitespace-pre-wrap overflow-x-auto">{@html highlightedContent}</pre>
							</div>
						</div>
					{/if}
				{:else}
					<div
						class="bg-yellow-50 p-4 rounded-lg"
					>
						<p class="text-yellow-800">
							Highlighting not yet
							supported for file_type:
							"{document.file_type}"
						</p>
						<div
							class="text-sm text-gray-600 mt-2"
						>
							<p>
								<strong
									>Available
									fields:</strong
								>
								{Object.keys(
									document,
								).join(", ")}
							</p>
							<p>
								<strong
									>filename:</strong
								>
								{document.filename}
							</p>
							<p>
								<strong
									>source_type:</strong
								>
								{document.source_type}
							</p>
							<p>
								<strong
									>All
									document
									data:</strong
								>
							</p>
							<pre
								class="text-xs bg-gray-100 p-2 mt-1 rounded overflow-x-auto">{JSON.stringify(
									document,
									null,
									2,
								)}</pre>
						</div>
					</div>
				{/if}
			{:else}
				<!-- NORMAL MODE: Show existing PDF viewer like the current interface -->
				{#if document.file_type === "application/pdf"}
					<!-- PDF Viewer (Normal Mode) -->
					<div
						class="bg-white rounded-lg shadow h-screen"
					>
						<PDFViewer
							bind:this={pdfViewer}
							documentUrl={`/api/v1/documents/${document.id}/file`}
							highlightChunks={[]}
							highlightPages={[]}
							documentId={document.id}
							on:chunkClick={handleChunkClick}
						/>
					</div>
				{:else if document.source_type === "chat"}
					<!-- Chat document display -->
					<div
						class="bg-white rounded-lg shadow p-6 max-w-4xl mx-auto"
					>
						<div class="prose max-w-none">
							<p
								class="text-gray-600"
							>
								Chat
								conversation
								saved as
								knowledge
							</p>
							<!-- TODO: Display chat messages with highlights -->
						</div>
					</div>
				{:else if document.file_type?.startsWith("text/")}
					<!-- Text document display -->
					<div
						class="bg-white rounded-lg shadow p-6 max-w-4xl mx-auto"
					>
						<pre
							class="whitespace-pre-wrap font-mono text-sm">{document.content ||
								"Loading content..."}</pre>
					</div>
				{:else}
					<!-- Unsupported type -->
					<div
						class="bg-yellow-50 p-4 rounded-lg"
					>
						<p class="text-yellow-800">
							Document type "{document.file_type}"
							viewer not yet
							implemented
						</p>
						<div
							class="text-sm text-gray-600 mt-2"
						>
							<p>
								<strong
									>Available
									fields:</strong
								>
								{Object.keys(
									document,
								).join(", ")}
							</p>
							<p>
								<strong
									>filename:</strong
								>
								{document.filename}
							</p>
							<p>
								<strong
									>source_type:</strong
								>
								{document.source_type}
							</p>
							<p>
								<strong
									>All
									document
									data:</strong
								>
							</p>
							<pre
								class="text-xs bg-gray-100 p-2 mt-1 rounded overflow-x-auto">{JSON.stringify(
									document,
									null,
									2,
								)}</pre>
						</div>
					</div>
				{/if}
			{/if}
		{/if}
	</div>
</div>

<style>
	:global(body) {
		overflow-y: auto;
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

