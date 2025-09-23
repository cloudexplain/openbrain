<script lang="ts">
	import { onMount, createEventDispatcher } from "svelte";
	import { browser } from "$app/environment";

	let pdfjsLib: any = null;

	let {
		documentUrl,
		highlightChunks = [],
		highlightPages = [],
		documentId,
	} = $props();


	const dispatch = createEventDispatcher();

	let container: HTMLDivElement;
	let pdfDoc: any = null;
	let loading = $state(true);
	let error = $state<string | null>(null);
	let currentPage = $state(1);
	let totalPages = $state(0);
	let scale = $state(1.2);

	// Search functionality
	let searchQuery = $state("");
	let searchResults: Array<{
		pageNum: number;
		matchIndex: number;
		startChar: number;
		endChar: number;
	}> = $state([]);
	let currentSearchIndex = $state(0);
	let isSearching = $state(false);
	let showSearch = $state(false);

	// Chunk data for highlighting
	let chunkData: any[] = [];

	onMount(async () => {

		if (browser) {
			try {
				loading = true;
				// Initialize PDF.js only in the browser
				const pdfjs = await import("pdfjs-dist");
				pdfjsLib = pdfjs;

				// Set the worker source
				pdfjsLib.GlobalWorkerOptions.workerSrc =
					"/pdf.worker.js";

				const loadResult = await loadPDF();
				// Note: loadPDF now handles loading chunk data internally for highlighting mode
			} catch (err) {
				error =
					err instanceof Error
						? err.message
						: "Failed to initialize PDF viewer";
			} finally {
				loading = false;
			}
		}

		// Add keyboard event listener
		document.addEventListener("keydown", handleKeydown);

		// Cleanup on unmount
		return () => {
			document.removeEventListener("keydown", handleKeydown);
		};
	});

	async function loadPDF() {
		if (!pdfjsLib) {
			error = "PDF library not initialized";
			loading = false;
			return;
		}

		if (!container) {
			loading = false;
			error = "Container not ready";
			return;
		}
		try {
			error = null;

			// Load the PDF document
			const loadingTask = pdfjsLib.getDocument({
				url: documentUrl,
			});

			pdfDoc = await loadingTask.promise;
			totalPages = pdfDoc.numPages;

			// Wait for chunk data if we're in highlighting mode
			if (highlightChunks.length > 0) {
				await loadChunkData();
			}

			// Render pages (filtered or all depending on mode)
			await renderAllPages();

			// Apply highlights after pages are rendered
			if (highlightChunks.length > 0 && chunkData.length > 0) {
				await applyHighlights();
			}
		} catch (err) {
			error =
				err instanceof Error
					? err.message
					: "Failed to load PDF";
		}
	}

	async function loadChunkData() {
		try {
			// Load ALL chunks for the document (not filtered)
			const chunkUrl = `/api/v1/documents/${documentId}/chunks`;

			const response = await fetch(chunkUrl);

			if (response.ok) {
				const data = await response.json();
				chunkData = data.chunks || data || [];


				// Don't apply highlights here - they will be applied after pages are rendered
			}
		} catch (err) {
			// Error loading chunk data
		}
	}

	async function renderAllPages() {
		if (!pdfDoc || !container) {
			console.log("🔍 PDFViewer: Cannot render pages - pdfDoc:", !!pdfDoc, "container:", !!container);
			return;
		}

		console.log(`🔍 PDFViewer: Rendering all ${totalPages} pages`);

		// Clear container
		container.innerHTML = "";

		// Always render all pages
		for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
			console.log(`🔍 PDFViewer: Rendering page ${pageNum}`);
			await renderPage(pageNum);
		}

		console.log(`🔍 PDFViewer: Finished rendering all ${totalPages} pages`);
	}

	async function renderPage(pageNum: number) {
		try {
			if (!pdfDoc) {
				console.log(`🔍 PDFViewer: Cannot render page ${pageNum} - no pdfDoc`);
				return;
			}

			const page = await pdfDoc.getPage(pageNum);
			const viewport = page.getViewport({ scale });

			// Create page container
			const pageContainer = document.createElement("div");
			pageContainer.className = "pdf-page-container";
			pageContainer.id = `page-${pageNum}`;
			pageContainer.style.cssText = `
				position: relative;
				display: block;
				margin: 20px auto 40px auto;
				border: 1px solid #ccc;
				box-shadow: 0 2px 10px rgba(0,0,0,0.1);
				background: white;
				width: ${viewport.width}px;
				height: ${viewport.height}px;
				clear: both;
			`;

			// Create canvas for PDF rendering
			const canvas = document.createElement("canvas");
			const context = canvas.getContext("2d");
			canvas.height = viewport.height;
			canvas.width = viewport.width;
			canvas.style.cssText = `
				display: block;
				position: absolute;
				top: 0;
				left: 0;
				z-index: 1;
			`;

			pageContainer.appendChild(canvas);

			// Create overlay for highlights
			const overlay = document.createElement("div");
			overlay.className = "highlight-overlay";
			overlay.style.cssText = `
				position: absolute;
				top: 0;
				left: 0;
				width: 100%;
				height: 100%;
				pointer-events: none;
				z-index: 2;
			`;
			pageContainer.appendChild(overlay);

			// Add page number indicator
			const pageIndicator = document.createElement("div");
			pageIndicator.className = "page-indicator";
			pageIndicator.textContent = `Page ${pageNum}`;
			pageIndicator.style.cssText = `
				position: absolute;
				top: -25px;
				left: 0;
				font-size: 12px;
				color: #666;
				background: white;
				padding: 2px 8px;
				border-radius: 4px;
				border: 1px solid #ddd;
			`;
			pageContainer.appendChild(pageIndicator);

			console.log(`🔍 PDFViewer: Appending page ${pageNum} container to DOM`);
			container.appendChild(pageContainer);

			// Render PDF content
			const renderContext = {
				canvasContext: context,
				viewport: viewport,
			};

			console.log(`🔍 PDFViewer: Starting render of page ${pageNum} content...`);
			console.log(`🔍 PDFViewer: Canvas context:`, context ? 'exists' : 'null');
			console.log(`🔍 PDFViewer: Canvas dimensions:`, canvas.width, 'x', canvas.height);
			
			try {
				// Use setTimeout to allow the browser to properly handle each render
				await new Promise((resolve) => {
					page.render(renderContext).promise.then(() => {
						console.log(`🔍 PDFViewer: Completed rendering page ${pageNum} content`);
						// Small delay to ensure browser processes the render
						setTimeout(resolve, 10);
					});
				});
			} catch (renderError) {
				console.error(`🔍 PDFViewer: Error rendering page ${pageNum}:`, renderError);
			}

			// Extract text content for highlighting
			const textContent = await page.getTextContent();

			// Store text content for highlighting
			pageContainer.dataset.textContent =
				JSON.stringify(textContent);

			console.log(`🔍 PDFViewer: Page ${pageNum} fully rendered and added to DOM`);
		} catch (err) {
			console.error(`🔍 PDFViewer: Error rendering page ${pageNum}:`, err);
		}
	}

	async function applyHighlights() {
		if (!chunkData.length) return;

		console.log(`🔍 Highlighting: Starting with ${chunkData.length} total chunks`);
		console.log(`🔍 Highlighting: Requested chunk IDs from URL:`, highlightChunks);

		// Filter to only highlight the specific chunks requested in the URL
		let chunksToHighlight = chunkData;

		if (highlightChunks.length > 0) {
			// Only highlight the specific chunks requested
			const requestedChunkIds = new Set(highlightChunks);
			console.log(`🔍 Highlighting: Requested chunk IDs set:`, requestedChunkIds);
			
			chunksToHighlight = chunkData.filter((chunk) => {
				const chunkId = chunk.id || chunk.chunk_id;
				const isIncluded = requestedChunkIds.has(chunkId);
				console.log(`🔍 Highlighting: Chunk ${chunkId} - included: ${isIncluded}`);
				return isIncluded;
			});

			console.log(`🔍 Highlighting: Filtered to ${chunksToHighlight.length} chunks to highlight`);

			if (chunksToHighlight.length === 0) {
				console.log(`🔍 Highlighting: No chunks matched the requested IDs, exiting`);
				return; // Don't highlight anything if no matches
			}
		}

		// Group filtered chunks by page based on text position
		const chunksByPage: { [key: number]: any[] } = {};
		
		// First, we need to build a map of character positions to page numbers
		// by examining the text content of each page
		const pageCharacterRanges: Array<{ start: number; end: number; pageNum: number }> = [];
		let currentCharPos = 0;
		
		for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
			const pageContainer = document.getElementById(`page-${pageNum}`);
			if (pageContainer && pageContainer.dataset.textContent) {
				try {
					const textContent = JSON.parse(pageContainer.dataset.textContent);
					const textItems = textContent.items || [];
					let pageText = "";
					
					textItems.forEach((item: any) => {
						const text = item.str || "";
						pageText += text;
						// Add space between items if they're on the same line but separated
						if (textItems.indexOf(item) < textItems.length - 1) {
							pageText += " ";
						}
					});
					
					const pageStartChar = currentCharPos;
					const pageEndChar = currentCharPos + pageText.length;
					
					pageCharacterRanges.push({
						start: pageStartChar,
						end: pageEndChar,
						pageNum: pageNum
					});
					
					console.log(`🔍 Highlighting: Page ${pageNum} text range: ${pageStartChar}-${pageEndChar} (${pageText.length} chars)`);
					currentCharPos = pageEndChar;
				} catch (e) {
					console.log(`🔍 Highlighting: Failed to process page ${pageNum} text content:`, e);
				}
			}
		}
		
		// Now we need to actually find each chunk in the page text and assign it to the correct page
		chunksToHighlight.forEach((chunk, chunkIndex) => {
			const chunkText = chunk.chunk_text || chunk.content || chunk.text || "";
			if (!chunkText.trim()) return;
			
			let assignedPageNum = 1; // default
			let found = false;
			
			console.log(`🔍 Highlighting: Processing chunk ${chunkIndex + 1}/${chunksToHighlight.length}: "${chunkText.substring(0, 50)}..."`);
			
			// Search each page's text content for this chunk
			for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
				if (found) break; // Only break the inner loop, not the outer forEach
				
				const pageContainer = document.getElementById(`page-${pageNum}`);
				if (pageContainer && pageContainer.dataset.textContent) {
					try {
						const textContent = JSON.parse(pageContainer.dataset.textContent);
						const textItems = textContent.items || [];
						
						// Build full text for this page
						let pageText = "";
						textItems.forEach((item: any, itemIndex: number) => {
							const text = item.str || "";
							pageText += text;
							// Add space between items if needed
							if (itemIndex < textItems.length - 1) {
								const currentItem = textItems[itemIndex];
								const nextItem = textItems[itemIndex + 1];
								// Add space if there's a gap between items or they're on different lines
								pageText += " ";
							}
						});
						
						// Normalize both texts for comparison
						const normalizedPageText = pageText.toLowerCase().replace(/\s+/g, " ").trim();
						const normalizedChunkText = chunkText.toLowerCase().replace(/\s+/g, " ").trim();
						
						// Try to find the chunk text in this page
						if (normalizedPageText.includes(normalizedChunkText.substring(0, Math.min(100, normalizedChunkText.length)))) {
							assignedPageNum = pageNum;
							found = true;
							console.log(`🔍 Highlighting: Found chunk ${chunkIndex + 1} "${chunkText.substring(0, 50)}..." on page ${pageNum}`);
						}
					} catch (e) {
						console.log(`🔍 Highlighting: Error processing page ${pageNum}:`, e);
					}
				}
			}
			
			if (!found) {
				console.log(`🔍 Highlighting: Could not find page for chunk ${chunkIndex + 1} "${chunkText.substring(0, 50)}...", defaulting to page 1`);
			}

			if (!chunksByPage[assignedPageNum]) {
				chunksByPage[assignedPageNum] = [];
			}
			chunksByPage[assignedPageNum].push(chunk);
		});
		
		console.log(`🔍 Highlighting: Chunks grouped by page:`, chunksByPage);

		// Apply highlights to each page (await each one)
		for (const [pageNum, chunks] of Object.entries(chunksByPage)) {
			await highlightPageChunks(parseInt(pageNum), chunks);
		}
	}

	async function highlightPageChunks(pageNum: number, chunks: any[]) {
		console.log(`🔍 Highlighting: Processing page ${pageNum} with ${chunks.length} chunks`);
		
		const pageContainer = document.getElementById(
			`page-${pageNum}`,
		);
		if (!pageContainer) {
			console.log(`🔍 Highlighting: No page container found for page ${pageNum}`);
			return;
		}

		const overlay = pageContainer.querySelector(
			".highlight-overlay",
		) as HTMLElement;
		if (!overlay) {
			console.log(`🔍 Highlighting: No overlay found for page ${pageNum}`);
			return;
		}
		
		console.log(`🔍 Highlighting: Found overlay for page ${pageNum}`, overlay);

		// Get stored text content for this page
		const textContentStr = pageContainer.dataset.textContent;
		if (!textContentStr) return;

		let textContent;
		try {
			textContent = JSON.parse(textContentStr);
		} catch (e) {
			return;
		}

		// Get page viewport for coordinate calculation
		const page = await pdfDoc.getPage(pageNum);
		const viewport = page.getViewport({ scale });

		// Build a searchable text string and position mapping
		let fullText = "";
		const textItems = textContent.items || [];
		const charPositions: Array<{
			x: number;
			y: number;
			width: number;
			height: number;
			itemIndex: number;
			charIndex: number;
		}> = [];

		// Track which character positions have already been highlighted
		const highlightedRanges: Array<{ start: number; end: number }> =
			[];

		textItems.forEach((item: any, itemIndex: number) => {
			const text = item.str || "";

			// Transform coordinates from PDF space to screen space using viewport
			const tx = pdfjsLib.Util.transform(
				viewport.transform,
				item.transform,
			);
			const x = tx[4];
			const y = tx[5];

			// Calculate the scaled width based on viewport
			const scaledWidth = item.width * viewport.scale;

			// Add positions for each character
			for (let i = 0; i < text.length; i++) {
				const charWidth = scaledWidth / text.length;
				charPositions.push({
					x: x + charWidth * i,
					y: y,
					width: charWidth,
					height:
						item.height * viewport.scale ||
						12,
					itemIndex,
					charIndex: i,
				});
			}

			fullText += text;

			// Add a space between text items (PDF often breaks at word boundaries)
			// But only if the next item is on the same line and there's a gap
			if (itemIndex < textItems.length - 1) {
				const nextItem = textItems[itemIndex + 1];
				const currentEndX = x + scaledWidth;

				// Transform next item's coordinates
				const nextTx = pdfjsLib.Util.transform(
					viewport.transform,
					nextItem.transform,
				);
				const nextX = nextTx[4];
				const nextY = nextTx[5];

				// If items are on the same line and there's a gap, add a space
				if (
					Math.abs(y - nextY) < 2 &&
					nextX > currentEndX + 2
				) {
					fullText += " ";
					// Add a position for the space character
					charPositions.push({
						x: currentEndX,
						y: y,
						width: nextX - currentEndX,
						height:
							item.height *
								viewport.scale ||
							12,
						itemIndex: -1, // Mark as synthetic space
						charIndex: -1,
					});
				}
			}
		});

		// Collect all highlight ranges from all chunks first
		const allHighlightRanges: Array<{
			start: number;
			end: number;
			chunkId: string;
			chunkIndex: number;
		}> = [];

		chunks.forEach((chunk, index) => {
			const chunkText =
				chunk.chunk_text ||
				chunk.content ||
				chunk.text ||
				"";

			if (!chunkText.trim()) {
				return;
			}

			// Find the character range for this chunk
			const range = findChunkRangeFuzzy(
				chunkText,
				fullText,
				charPositions,
				viewport,
			);
			if (range) {
				allHighlightRanges.push({
					start: range.start,
					end: range.end,
					chunkId: chunk.id,
					chunkIndex: index,
				});
			}
		});

		// Merge overlapping ranges
		const mergedRanges = mergeOverlappingRanges(allHighlightRanges);

		// Create highlights for merged ranges
		mergedRanges.forEach((range, index) => {

			// Create highlights for this range
			if (
				range.start < charPositions.length &&
				range.end <= charPositions.length
			) {
				const highlights = createLineHighlights(
					range.start,
					range.end,
					charPositions,
					viewport,
				);

				highlights.forEach(
					(highlightPos, highlightIndex) => {
						const highlight =
							document.createElement(
								"div",
							);
						highlight.className =
							"chunk-highlight";

						highlight.style.cssText = `
						position: absolute;
						left: ${highlightPos.left}px;
						top: ${highlightPos.top}px;
						width: ${highlightPos.width}px;
						height: ${highlightPos.height}px;
						background: rgba(255, 255, 0, 0.3);
						pointer-events: none;
						z-index: 10;
					`;

						overlay.appendChild(highlight);
					},
				);
			}
		});

		// Add a subtle page indicator for highlighted pages
		const pageIndicator = pageContainer.querySelector(
			".page-indicator",
		) as HTMLElement;
		if (pageIndicator && chunks.length > 0) {
			pageIndicator.style.background = "#fef3c7";
			pageIndicator.style.borderColor = "#fbbf24";
			pageIndicator.style.color = "#92400e";
		}
	}

	function normalizeText(text: string): string {
		// Normalize text for comparison: remove multiple spaces, line breaks, special chars
		return text
			.toLowerCase()
			.replace(/[\r\n]+/g, " ") // Replace line breaks with spaces
			.replace(/\s+/g, " ") // Collapse multiple spaces
			.replace(/[^\w\s]/g, "") // Remove all non-word characters except spaces
			.replace(/\s+/g, " ") // Collapse spaces again after removal
			.trim();
	}

	function extractKeyPhrase(text: string, maxWords: number = 15): string {
		// Extract a key phrase from text, removing common stop words
		const stopWords = new Set([
			"the",
			"a",
			"an",
			"and",
			"or",
			"but",
			"in",
			"on",
			"at",
			"to",
			"for",
			"of",
			"with",
			"by",
			"from",
			"as",
			"is",
			"was",
			"are",
			"were",
			"been",
			"be",
			"have",
			"has",
			"had",
			"do",
			"does",
			"did",
			"will",
			"would",
			"could",
			"should",
			"may",
			"might",
		]);

		const words = text.toLowerCase().split(/\s+/);
		const significantWords = words.filter(
			(w) => !stopWords.has(w) && w.length > 3,
		);

		// Return the first N significant words joined
		return significantWords.slice(0, maxWords).join(" ");
	}

	function mergeOverlappingRanges(
		ranges: Array<{
			start: number;
			end: number;
			chunkId: string;
			chunkIndex: number;
		}>,
	): Array<{ start: number; end: number }> {
		if (ranges.length === 0) return [];

		// Sort ranges by start position
		const sorted = [...ranges].sort((a, b) => a.start - b.start);

		const merged: Array<{ start: number; end: number }> = [];
		let current = { start: sorted[0].start, end: sorted[0].end };

		for (let i = 1; i < sorted.length; i++) {
			const next = sorted[i];

			// If ranges overlap or are adjacent, merge them
			if (next.start <= current.end) {
				current.end = Math.max(current.end, next.end);
			} else {
				// No overlap, add current range and start new one
				merged.push({ ...current });
				current = { start: next.start, end: next.end };
			}
		}

		// Add the last range
		merged.push(current);

		return merged;
	}

	function findChunkRangeFuzzy(
		searchText: string,
		fullText: string,
		charPositions: any[],
		viewport: any,
	): { start: number; end: number } | null {
		// Split into words and normalize
		const chunkWords = searchText.trim().split(/\s+/);
		const pageWords = fullText.split(/\s+/);
		const normalizeWord = (w: string) =>
			w.toLowerCase().replace(/[^\w]/g, "");

		const windowSize = 5;
		const minMatches = 4; // Need at least 4 out of 5 words to match

		// Find the START of the chunk using the first few words
		let chunkStartPageIndex = -1;
		const startSearchWords = Math.min(
			windowSize,
			chunkWords.length,
		);
		if (startSearchWords >= windowSize) {
			const startChunkWindow = chunkWords.slice(
				0,
				windowSize,
			);
			const normalizedStartChunkWindow =
				startChunkWindow.map(normalizeWord);

			// Search for this window in the page
			for (
				let pageStart = 0;
				pageStart <= pageWords.length - windowSize;
				pageStart++
			) {
				const pageWindow = pageWords.slice(
					pageStart,
					pageStart + windowSize,
				);
				const normalizedPageWindow =
					pageWindow.map(normalizeWord);

				// Count matches
				let matches = 0;
				for (let i = 0; i < windowSize; i++) {
					if (
						normalizedStartChunkWindow[
							i
						] === normalizedPageWindow[i]
					) {
						matches++;
					}
				}

				if (matches >= minMatches) {
					chunkStartPageIndex = pageStart;
					break;
				}
			}
		}

		// Find the END of the chunk using the last few words
		let chunkEndPageIndex = -1;
		if (
			chunkWords.length >= windowSize &&
			chunkStartPageIndex !== -1
		) {
			const endChunkWindow = chunkWords.slice(-windowSize);
			const normalizedEndChunkWindow =
				endChunkWindow.map(normalizeWord);

			// Start searching from where we found the beginning (optimization)
			const searchStart = Math.max(chunkStartPageIndex, 0);
			for (
				let pageStart = searchStart;
				pageStart <= pageWords.length - windowSize;
				pageStart++
			) {
				const pageWindow = pageWords.slice(
					pageStart,
					pageStart + windowSize,
				);
				const normalizedPageWindow =
					pageWindow.map(normalizeWord);

				// Count matches
				let matches = 0;
				for (let i = 0; i < windowSize; i++) {
					if (
						normalizedEndChunkWindow[i] ===
						normalizedPageWindow[i]
					) {
						matches++;
					}
				}

				if (matches >= minMatches) {
					// End index is at the end of this window
					chunkEndPageIndex =
						pageStart + windowSize;
				}
			}
		}

		// If we couldn't find the end, try to estimate based on chunk length
		if (chunkStartPageIndex !== -1 && chunkEndPageIndex === -1) {
			// Estimate the end based on the chunk word count
			chunkEndPageIndex = Math.min(
				chunkStartPageIndex + chunkWords.length,
				pageWords.length,
			);
		}

		// Now convert word indices to character positions and create a continuous highlight
		if (chunkStartPageIndex !== -1 && chunkEndPageIndex !== -1) {

			// Find character position for start
			let chunkStartChar = -1;
			let wordCount = 0;
			let inWord = false;
			for (
				let i = 0;
				i < fullText.length &&
				wordCount <= chunkStartPageIndex;
				i++
			) {
				const isWordChar = /\w/.test(fullText[i]);
				if (isWordChar && !inWord) {
					// Starting a new word
					inWord = true;
					if (wordCount === chunkStartPageIndex) {
						chunkStartChar = i;
						break;
					}
				} else if (!isWordChar && inWord) {
					// Ending a word
					inWord = false;
					wordCount++;
				}
			}

			// Find character position for end
			let chunkEndChar = -1;
			wordCount = 0;
			inWord = false;
			for (
				let i = 0;
				i < fullText.length &&
				wordCount < chunkEndPageIndex;
				i++
			) {
				const isWordChar = /\w/.test(fullText[i]);
				if (isWordChar && !inWord) {
					// Starting a new word
					inWord = true;
				} else if (!isWordChar && inWord) {
					// Ending a word
					inWord = false;
					wordCount++;
					if (wordCount === chunkEndPageIndex) {
						chunkEndChar = i;
						break;
					}
				}
				// Keep track of the last character position in case we reach the end
				if (
					wordCount === chunkEndPageIndex - 1 &&
					isWordChar
				) {
					chunkEndChar = i + 1;
				}
			}

			// If we're still in a word at the end, use the text length
			if (
				chunkEndChar === -1 &&
				wordCount === chunkEndPageIndex - 1
			) {
				chunkEndChar = fullText.length;
			}

			if (chunkStartChar !== -1 && chunkEndChar !== -1) {
				return {
					start: chunkStartChar,
					end: chunkEndChar,
				};
			}
		}

		return null;
	}

	function createLineHighlights(
		startIndex: number,
		endIndex: number,
		charPositions: any[],
		viewport: any,
	): Array<{ left: number; top: number; width: number; height: number }> {
		const highlights: Array<{
			left: number;
			top: number;
			width: number;
			height: number;
		}> = [];

		if (
			startIndex >= charPositions.length ||
			endIndex > charPositions.length
		) {
			return highlights;
		}

		let currentLineStart = startIndex;
		let currentY = charPositions[startIndex]?.y;

		for (let i = startIndex; i < endIndex; i++) {
			const pos = charPositions[i];
			if (!pos) continue;

			// Check if we've moved to a new line (significant Y difference)
			if (Math.abs(pos.y - currentY) > 5) {
				// Create highlight for previous line
				if (currentLineStart < i) {
					const lineStart =
						charPositions[currentLineStart];
					const lineEnd = charPositions[i - 1];
					if (lineStart && lineEnd) {
						highlights.push({
							left: lineStart.x,
							top:
								lineStart.y -
								lineStart.height, // Y is already in screen space (top-down)
							width: Math.max(
								lineEnd.x +
									lineEnd.width -
									lineStart.x,
								20,
							),
							height: Math.max(
								lineStart.height,
								20,
							),
						});
					}
				}

				// Start new line
				currentLineStart = i;
				currentY = pos.y;
			}
		}

		// Create highlight for the final line
		if (currentLineStart < endIndex) {
			const lineStart = charPositions[currentLineStart];
			const lineEnd = charPositions[endIndex - 1];
			if (lineStart && lineEnd) {
				highlights.push({
					left: lineStart.x,
					top: lineStart.y - lineStart.height, // Y is already in screen space (top-down)
					width: Math.max(
						lineEnd.x +
							lineEnd.width -
							lineStart.x,
						20,
					),
					height: Math.max(lineStart.height, 20),
				});
			}
		}

		return highlights;
	}

	function zoomIn() {
		scale = Math.min(scale * 1.2, 3);
		if (pdfjsLib) {
			renderAllPages().then(() => {
				if (highlightChunks.length > 0 && chunkData.length > 0) {
					applyHighlights();
				}
			});
		}
	}

	function zoomOut() {
		scale = Math.max(scale / 1.2, 0.5);
		if (pdfjsLib) {
			renderAllPages().then(() => {
				if (highlightChunks.length > 0 && chunkData.length > 0) {
					applyHighlights();
				}
			});
		}
	}

	function scrollToPage(pageNum: number) {
		const pageElement = document.getElementById(`page-${pageNum}`);
		if (pageElement) {
			pageElement.scrollIntoView({
				behavior: "smooth",
				block: "start",
			});
		}
	}

	// Search functionality
	async function performSearch() {
		if (!searchQuery.trim() || !pdfDoc) return;

		isSearching = true;
		searchResults = [];
		currentSearchIndex = 0;

		// Clear existing search highlights
		clearSearchHighlights();

		const query = searchQuery.toLowerCase();

		// Search through all pages
		for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
			const pageContainer = document.getElementById(
				`page-${pageNum}`,
			);
			if (!pageContainer) continue;

			const textContentStr =
				pageContainer.dataset.textContent;
			if (!textContentStr) continue;

			try {
				const textContent = JSON.parse(textContentStr);
				const textItems = textContent.items || [];

				// Build full text for this page
				let fullText = "";
				textItems.forEach((item: any) => {
					fullText += item.str || "";
				});

				// Find all matches on this page
				const pageText = fullText.toLowerCase();
				let matchIndex = 0;
				let searchIndex = pageText.indexOf(query);

				while (searchIndex !== -1) {
					searchResults.push({
						pageNum,
						matchIndex: matchIndex++,
						startChar: searchIndex,
						endChar:
							searchIndex +
							query.length,
					});

					searchIndex = pageText.indexOf(
						query,
						searchIndex + 1,
					);
				}
			} catch (e) {
				// Error searching page
			}
		}

		// Highlight all search results
		if (searchResults.length > 0) {
			highlightSearchResults();
			goToSearchResult(0);
		}

		isSearching = false;
	}

	function clearSearchHighlights() {
		// Remove all search highlight elements
		const allHighlights =
			document.querySelectorAll(".search-highlight");
		allHighlights.forEach((el) => el.remove());
	}

	async function highlightSearchResults() {
		// Group results by page
		const resultsByPage: { [key: number]: typeof searchResults } =
			{};
		searchResults.forEach((result) => {
			if (!resultsByPage[result.pageNum]) {
				resultsByPage[result.pageNum] = [];
			}
			resultsByPage[result.pageNum].push(result);
		});

		// Highlight each page's results
		for (const [pageNum, pageResults] of Object.entries(
			resultsByPage,
		)) {
			await highlightPageSearchResults(
				parseInt(pageNum),
				pageResults,
			);
		}
	}

	async function highlightPageSearchResults(
		pageNum: number,
		results: typeof searchResults,
	) {
		const pageContainer = document.getElementById(
			`page-${pageNum}`,
		);
		if (!pageContainer) return;

		const overlay = pageContainer.querySelector(
			".highlight-overlay",
		) as HTMLElement;
		if (!overlay) return;

		const textContentStr = pageContainer.dataset.textContent;
		if (!textContentStr) return;

		try {
			const textContent = JSON.parse(textContentStr);
			const page = await pdfDoc.getPage(pageNum);
			const viewport = page.getViewport({ scale });

			// Build character positions
			const charPositions: Array<{
				x: number;
				y: number;
				width: number;
				height: number;
			}> = [];
			const textItems = textContent.items || [];

			textItems.forEach((item: any) => {
				const tx = pdfjsLib.Util.transform(
					viewport.transform,
					item.transform,
				);
				const x = tx[4];
				const y = tx[5];
				const scaledWidth = item.width * viewport.scale;
				const text = item.str || "";

				for (let i = 0; i < text.length; i++) {
					const charWidth =
						scaledWidth / text.length;
					charPositions.push({
						x: x + charWidth * i,
						y: y,
						width: charWidth,
						height:
							item.height *
								viewport.scale ||
							12,
					});
				}
			});

			// Create highlights for each search result
			results.forEach((result, index) => {
				if (
					result.startChar <
						charPositions.length &&
					result.endChar <= charPositions.length
				) {
					const highlights = createLineHighlights(
						result.startChar,
						result.endChar,
						charPositions,
						viewport,
					);

					highlights.forEach((highlightPos) => {
						const highlight =
							document.createElement(
								"div",
							);
						highlight.className =
							"search-highlight";
						highlight.dataset.resultIndex =
							searchResults
								.indexOf(result)
								.toString();

						// Use different style for current search result
						const isCurrentResult =
							searchResults.indexOf(
								result,
							) ===
							currentSearchIndex;

						highlight.style.cssText = `
							position: absolute;
							left: ${highlightPos.left}px;
							top: ${highlightPos.top}px;
							width: ${highlightPos.width}px;
							height: ${highlightPos.height}px;
							background: ${isCurrentResult ? "rgba(255, 140, 0, 0.4)" : "rgba(128, 0, 128, 0.3)"};
							pointer-events: none;
							z-index: 11;
						`;

						overlay.appendChild(highlight);
					});
				}
			});
		} catch (e) {
			// Error highlighting search results
		}
	}

	function goToSearchResult(index: number) {
		if (searchResults.length === 0) return;

		// Wrap around
		if (index < 0) {
			currentSearchIndex = searchResults.length - 1;
		} else if (index >= searchResults.length) {
			currentSearchIndex = 0;
		} else {
			currentSearchIndex = index;
		}

		const result = searchResults[currentSearchIndex];

		// Scroll to the page
		scrollToPage(result.pageNum);

		// Re-highlight to show current result
		clearSearchHighlights();
		highlightSearchResults();
	}

	function nextSearchResult() {
		goToSearchResult(currentSearchIndex + 1);
	}

	function previousSearchResult() {
		goToSearchResult(currentSearchIndex - 1);
	}

	function toggleSearch() {
		showSearch = !showSearch;
		if (!showSearch) {
			clearSearchHighlights();
			searchQuery = "";
			searchResults = [];
		}
	}

	// Handle keyboard shortcuts
	function handleKeydown(e: KeyboardEvent) {
		// Ctrl+F or Cmd+F to open search
		if ((e.ctrlKey || e.metaKey) && e.key === "f") {
			e.preventDefault();
			showSearch = true;
		}

		// Escape to close search
		if (e.key === "Escape" && showSearch) {
			toggleSearch();
		}

		// Enter for next result, Shift+Enter for previous
		if (e.key === "Enter" && showSearch && searchQuery) {
			e.preventDefault();
			if (e.shiftKey) {
				previousSearchResult();
			} else {
				if (searchResults.length === 0) {
					performSearch();
				} else {
					nextSearchResult();
				}
			}
		}
	}

	// Expose scrollToPage for parent component
	function scrollToPageExposed(pageNum: number) {
		scrollToPage(pageNum);
	}

	export { scrollToPageExposed as scrollToPage };
</script>

<div class="pdf-viewer">
	<!-- Toolbar -->
	<div class="toolbar">
		<div class="toolbar-group">
			<button
				on:click={zoomOut}
				class="btn-icon"
				title="Zoom Out"
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
						d="M20 12H4"
					/>
				</svg>
			</button>
			<span class="zoom-level"
				>{Math.round(scale * 100)}%</span
			>
			<button
				on:click={zoomIn}
				class="btn-icon"
				title="Zoom In"
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
						d="M12 6v6m0 0v6m0-6h6m-6 0H6"
					/>
				</svg>
			</button>
		</div>

		<div class="toolbar-group">
			<!-- Search toggle button -->
			<button
				on:click={toggleSearch}
				class="btn-icon"
				title="Search (Ctrl+F)"
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
						d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
					/>
				</svg>
			</button>

			{#if showSearch}
				<div class="search-controls">
					<input
						type="text"
						bind:value={searchQuery}
						on:input={performSearch}
						placeholder="Search..."
						class="search-input"
						autofocus
					/>

					{#if searchResults.length > 0}
						<span class="search-status">
							{currentSearchIndex + 1}
							of {searchResults.length}
						</span>

						<button
							on:click={previousSearchResult}
							class="btn-icon small"
							title="Previous (Shift+Enter)"
						>
							<svg
								class="w-3 h-3"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M15 19l-7-7 7-7"
								/>
							</svg>
						</button>

						<button
							on:click={nextSearchResult}
							class="btn-icon small"
							title="Next (Enter)"
						>
							<svg
								class="w-3 h-3"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 5l7 7-7 7"
								/>
							</svg>
						</button>
					{:else if searchQuery && !isSearching}
						<span
							class="search-status no-results"
							>No results</span
						>
					{/if}

					<button
						on:click={toggleSearch}
						class="btn-icon small"
						title="Close (Esc)"
					>
						<svg
							class="w-3 h-3"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>
			{/if}
		</div>

		{#if totalPages > 0}
			<div class="page-info">
				{totalPages} page{totalPages !== 1 ? "s" : ""}
				{#if highlightChunks.length > 0}
					• {highlightChunks.length} highlighted sections
				{/if}
			</div>
		{/if}
	</div>

	<!-- Loading State -->
	{#if loading}
		<div class="loading">
			<div class="flex items-center space-x-2">
				<svg
					class="animate-spin w-5 h-5"
					fill="none"
					viewBox="0 0 24 24"
				>
					<circle
						class="opacity-25"
						cx="12"
						cy="12"
						r="10"
						stroke="currentColor"
						stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
				<span
					>{pdfjsLib
						? "Loading PDF..."
						: "Initializing PDF viewer..."}</span
				>
			</div>
		</div>
	{/if}

	<!-- Error State -->
	{#if error}
		<div class="error">
			<p>Failed to load PDF: {error}</p>
			<button on:click={loadPDF} class="retry-btn"
				>Try Again</button
			>
		</div>
	{/if}

	<!-- PDF Container -->
	<div class="pdf-container" bind:this={container} id="pdf-container">
		<!-- PDF pages will be rendered here -->
	</div>
</div>

<style>
	.pdf-viewer {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: #f5f5f5;
	}

	.toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		background: white;
		border-bottom: 1px solid #e5e7eb;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.toolbar-group {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.btn-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: 1px solid #d1d5db;
		background: white;
		border-radius: 4px;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-icon:hover {
		background: #f9fafb;
		border-color: #9ca3af;
	}

	.btn-icon.small {
		width: 24px;
		height: 24px;
	}

	.search-controls {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 0 12px;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 4px;
	}

	.search-input {
		width: 200px;
		padding: 4px 8px;
		border: none;
		outline: none;
		font-size: 14px;
	}

	.search-input:focus {
		outline: none;
	}

	.search-status {
		font-size: 12px;
		color: #6b7280;
		white-space: nowrap;
		padding: 0 4px;
	}

	.search-status.no-results {
		color: #dc2626;
	}

	.zoom-level {
		font-size: 14px;
		font-weight: 500;
		color: #4b5563;
		min-width: 50px;
		text-align: center;
	}

	.page-info {
		font-size: 14px;
		color: #6b7280;
	}

	.loading {
		display: flex;
		justify-content: center;
		align-items: center;
		padding: 60px 20px;
		color: #6b7280;
	}

	.error {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 60px 20px;
		color: #dc2626;
		text-align: center;
	}

	.retry-btn {
		margin-top: 12px;
		padding: 8px 16px;
		background: #dc2626;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}

	.retry-btn:hover {
		background: #b91c1c;
	}

	.pdf-container {
		flex: 1;
		overflow-y: auto;
		padding: 20px;
	}

	:global(.pdf-page-container) {
		position: relative !important;
		display: block !important;
		margin-bottom: 40px !important;
	}

	:global(.highlight-overlay) {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}

	:global(.page-indicator) {
		position: absolute;
		top: -25px;
		left: 0;
		font-size: 12px;
		color: #666;
		background: white;
		padding: 2px 8px;
		border-radius: 4px;
		border: 1px solid #ddd;
		transition: all 0.2s ease;
	}
</style>

