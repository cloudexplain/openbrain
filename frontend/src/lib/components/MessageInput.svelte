<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import TagAutocomplete from './TagAutocomplete.svelte';
	import DocumentAutocomplete from './DocumentAutocomplete.svelte';

	export let disabled = false;
	export let placeholder = 'Send a message...';
	
	let message = '';
	let textarea: HTMLTextAreaElement;
	
	// Tag autocomplete state
	let showTagAutocomplete = false;
	let tagAutocompletePosition = { x: 0, y: 0 };
	let tagQuery = '';
	let tagStartIndex = -1;
	
	// Document autocomplete state
	let showDocumentAutocomplete = false;
	let documentAutocompletePosition = { x: 0, y: 0 };
	let documentQuery = '';
	let documentStartIndex = -1;
	
	const dispatch = createEventDispatcher<{
		send: { content: string };
	}>();

	function autoResize() {
		if (textarea) {
			textarea.style.height = '24px';
			textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
		}
	}

	function handleSubmit() {
		if (message.trim() && !disabled) {
			dispatch('send', { content: message.trim() });
			message = '';
			showTagAutocomplete = false;
			showDocumentAutocomplete = false;
			setTimeout(autoResize, 0); // Delay to ensure DOM update
		}
	}

	function getCaretPosition() {
		if (!textarea) return 0;
		return textarea.selectionStart;
	}

	function getCaretCoordinates(caretPos: number) {
		if (!textarea) return { x: 0, y: 0 };
		
		// Create a hidden div to measure text dimensions
		const hiddenDiv = document.createElement('div');
		const computedStyle = window.getComputedStyle(textarea);
		
		// Copy textarea styles to hidden div for accurate measurement
		hiddenDiv.style.position = 'absolute';
		hiddenDiv.style.visibility = 'hidden';
		hiddenDiv.style.whiteSpace = 'pre-wrap';
		hiddenDiv.style.wordWrap = 'break-word';
		hiddenDiv.style.fontSize = computedStyle.fontSize;
		hiddenDiv.style.fontFamily = computedStyle.fontFamily;
		hiddenDiv.style.fontWeight = computedStyle.fontWeight;
		hiddenDiv.style.lineHeight = computedStyle.lineHeight;
		hiddenDiv.style.padding = computedStyle.padding;
		hiddenDiv.style.border = computedStyle.border;
		hiddenDiv.style.width = computedStyle.width;
		hiddenDiv.style.top = '-9999px';
		hiddenDiv.style.left = '-9999px';
		
		document.body.appendChild(hiddenDiv);
		
		// Set text content up to caret position
		const textBeforeCaret = textarea.value.substring(0, caretPos);
		hiddenDiv.textContent = textBeforeCaret;
		
		// Create a span to measure the exact end position
		const caretSpan = document.createElement('span');
		caretSpan.textContent = '|'; // Use a character to measure position
		hiddenDiv.appendChild(caretSpan);
		
		// Get the position relative to the hidden div
		const spanRect = caretSpan.getBoundingClientRect();
		const divRect = hiddenDiv.getBoundingClientRect();
		
		// Clean up
		document.body.removeChild(hiddenDiv);
		
		// Get textarea position
		const textareaRect = textarea.getBoundingClientRect();
		
		// Calculate relative position within the textarea
		const relativeX = spanRect.left - divRect.left;
		const relativeY = spanRect.top - divRect.top;
		
		// Convert to absolute screen coordinates
		return {
			x: textareaRect.left + relativeX,
			y: textareaRect.top + relativeY + 20 // Add a small offset below the line
		};
	}

	function checkForTagTrigger(event: Event) {
		const caretPos = getCaretPosition();
		const textBeforeCaret = message.substring(0, caretPos);
		
		// Look for # followed by word characters, working backwards from caret
		const match = textBeforeCaret.match(/#([\w-]*)$/);
		
		if (match) {
			tagStartIndex = caretPos - match[0].length;
			tagQuery = match[1];
			
			if (tagQuery.length >= 0) { // Show immediately when # is typed
				// Position the dropdown right at the "#" character position
				const coords = getCaretCoordinates(tagStartIndex);
				tagAutocompletePosition = coords;
				showTagAutocomplete = true;
			}
		} else {
			showTagAutocomplete = false;
			tagStartIndex = -1;
			tagQuery = '';
		}
	}

	function checkForDocumentTrigger(event: Event) {
		const caretPos = getCaretPosition();
		const textBeforeCaret = message.substring(0, caretPos);
		
		// Look for /doc or /document followed by optional space and text (with or without quotes)
		// Patterns: /doc, /doc partial, /doc "partial", /document text, etc.
		const docMatch = textBeforeCaret.match(/\/(doc|document)(?:\s+((?:"([^"]*)"?)|([^\s]*)))?$/);
		
		if (docMatch) {
			documentStartIndex = caretPos - docMatch[0].length;
			// Extract query: either from quotes (match[3]) or unquoted text (match[4])
			documentQuery = docMatch[3] || docMatch[4] || ''; 
			
			// Show autocomplete immediately when /doc or /document is typed
			const coords = getCaretCoordinates(documentStartIndex);
			documentAutocompletePosition = coords;
			showDocumentAutocomplete = true;
		} else {
			showDocumentAutocomplete = false;
			documentStartIndex = -1;
			documentQuery = '';
		}
	}

	function handleInput(event: Event) {
		autoResize();
		checkForTagTrigger(event);
		checkForDocumentTrigger(event);
	}

	function handleKeydown(event: KeyboardEvent) {
		// If any autocomplete is showing, let it handle certain keys
		if (showTagAutocomplete || showDocumentAutocomplete) {
			if (event.key === 'Escape') {
				event.preventDefault();
				showTagAutocomplete = false;
				showDocumentAutocomplete = false;
				return;
			}
			// Don't handle Enter if autocomplete is showing - let it handle selection
			if (event.key === 'Enter' || event.key === 'ArrowUp' || event.key === 'ArrowDown') {
				return; // Let autocomplete components handle these
			}
		}
		
		if (event.key === 'Enter' && !event.shiftKey && !showTagAutocomplete && !showDocumentAutocomplete) {
			event.preventDefault();
			handleSubmit();
		}
	}

	function handleTagSelect(event: CustomEvent) {
		const { tag } = event.detail;
		
		if (tagStartIndex >= 0) {
			const before = message.substring(0, tagStartIndex);
			const after = message.substring(getCaretPosition());
			message = before + `#${tag.name} ` + after;
			
			// Set cursor position after the inserted tag
			setTimeout(() => {
				if (textarea) {
					const newPos = tagStartIndex + tag.name.length + 2; // +2 for # and space
					textarea.setSelectionRange(newPos, newPos);
					textarea.focus();
				}
			}, 0);
		}
		
		showTagAutocomplete = false;
		tagStartIndex = -1;
		tagQuery = '';
	}

	function handleDocumentSelect(event: CustomEvent) {
		const { document } = event.detail;
		
		if (documentStartIndex >= 0) {
			const before = message.substring(0, documentStartIndex);
			const after = message.substring(getCaretPosition());
			
			// Use quotes only if the document title contains spaces, otherwise no quotes
			const needsQuotes = document.title.includes(' ');
			const documentRef = needsQuotes 
				? `/doc "${document.title}" `
				: `/doc ${document.title} `;
			
			message = before + documentRef + after;
			
			// Set cursor position after the inserted document reference
			setTimeout(() => {
				if (textarea) {
					const newPos = documentStartIndex + documentRef.length;
					textarea.setSelectionRange(newPos, newPos);
					textarea.focus();
				}
			}, 0);
		}
		
		showDocumentAutocomplete = false;
		documentStartIndex = -1;
		documentQuery = '';
	}

	function handleClickOutside(event: MouseEvent) {
		if (showTagAutocomplete && !event.target?.closest('.tag-autocomplete')) {
			showTagAutocomplete = false;
		}
		if (showDocumentAutocomplete && !event.target?.closest('.document-autocomplete')) {
			showDocumentAutocomplete = false;
		}
	}

	// Extract referenced tags from the current message
	function getReferencedTags(text: string): string[] {
		const tagPattern = /#([\w-]+)/g;
		const matches = [...text.matchAll(tagPattern)];
		return matches.map(match => match[1]);
	}

	// Extract referenced documents from the current message
	function getReferencedDocuments(text: string): string[] {
		// Match both quoted and unquoted document references
		// /doc "Document Name" or /doc DocumentName
		const docPattern = /\/(doc|document)\s+(?:"([^"]+)"|(\S+))/g;
		const matches = [...text.matchAll(docPattern)];
		return matches.map(match => match[2] || match[3]); // Return quoted (match[2]) or unquoted (match[3]) name
	}

	function removeDocumentReference(docName: string) {
		// Remove the document reference from the message
		// Handle both quoted and unquoted formats
		const quotedPattern = new RegExp(`/(?:doc|document)\\s+"${docName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"\\s*`, 'g');
		const unquotedPattern = new RegExp(`/(?:doc|document)\\s+${docName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*`, 'g');
		
		message = message.replace(quotedPattern, '').replace(unquotedPattern, '').trim();
		
		// Clean up extra spaces
		message = message.replace(/\s+/g, ' ').trim();
	}

	function removeTagReference(tagName: string) {
		// Remove the tag reference from the message
		const tagPattern = new RegExp(`#${tagName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g');
		message = message.replace(tagPattern, '').trim();
		
		// Clean up extra spaces
		message = message.replace(/\s+/g, ' ').trim();
	}

	$: referencedTags = getReferencedTags(message);
	$: referencedDocuments = getReferencedDocuments(message);

	// Handle auto-referencing of uploaded documents
	function handleAutoReferenceDocuments(event: CustomEvent) {
		const { documents } = event.detail;
		
		// Add document references to the current message
		const documentRefs = documents.map(doc => {
			const needsQuotes = doc.title.includes(' ');
			return needsQuotes ? `/doc "${doc.title}"` : `/doc ${doc.title}`;
		}).join(' ');
		
		// Append to current message with proper spacing
		if (message.trim()) {
			message = `${message.trim()} ${documentRefs}`;
		} else {
			message = documentRefs;
		}
		
		// Focus the textarea and move cursor to end
		if (textarea) {
			setTimeout(() => {
				textarea.focus();
				textarea.setSelectionRange(message.length, message.length);
				autoResize();
			}, 0);
		}
	}

	onMount(() => {
		// Listen for auto-reference events from file uploads
		const handleAutoReference = (event: CustomEvent) => {
			handleAutoReferenceDocuments(event);
		};
		
		window.addEventListener('auto-reference-documents', handleAutoReference);
		
		return () => {
			window.removeEventListener('auto-reference-documents', handleAutoReference);
		};
	});
</script>

<svelte:window on:click={handleClickOutside} />

<div class="border-t border-gray-200 bg-white">
	<div class="max-w-3xl mx-auto px-6 py-6">
		<div class="relative">
			<!-- Referenced Tags and Documents Indicator -->
			{#if referencedTags.length > 0 || referencedDocuments.length > 0}
				<div class="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
					<div class="flex items-center justify-between mb-2">
						<div class="flex items-center gap-2">
							<svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.1a2.995 2.995 0 00.275-3.9l-.169-.311.1.1a.99.99 0 001.227.042l.092-.088a4 4 0 00-.275-5.924l-.016-.017a4 4 0 00-.023 0zm6.828 0a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.1a2.995 2.995 0 00.275-3.9l-.169-.311.1.1a.99.99 0 001.227.042l.092-.088a4 4 0 00-.275-5.924l-.016-.017a4 4 0 00-.023 0z" />
							</svg>
							<span class="text-sm font-medium text-gray-700">
								Context References ({referencedTags.length + referencedDocuments.length})
							</span>
						</div>
						<span class="text-xs text-gray-500">Click to remove</span>
					</div>
					<div class="flex flex-wrap gap-2">
						{#each referencedTags as tag}
							<span 
								class="inline-flex items-center px-3 py-1.5 rounded-lg text-xs bg-orange-50 text-orange-900 border border-orange-200 hover:bg-orange-100 transition-colors cursor-pointer group"
								title="Tag reference - click to remove"
								on:click={() => removeTagReference(tag)}
							>
								<span class="w-2 h-2 rounded-full bg-orange-400 mr-2"></span>
								<span class="font-medium">#{tag}</span>
								<svg class="w-3 h-3 ml-1.5 text-orange-500 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</span>
						{/each}
						{#each referencedDocuments as doc}
							<span 
								class="inline-flex items-center px-3 py-1.5 rounded-lg text-xs bg-blue-50 text-blue-900 border border-blue-200 hover:bg-blue-100 transition-colors cursor-pointer group"
								title="Document reference - click to remove"
								on:click={() => removeDocumentReference(doc)}
							>
								<svg class="w-3.5 h-3.5 mr-1.5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
								</svg>
								<span class="font-medium">{doc}</span>
								<svg class="w-3 h-3 ml-1.5 text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</span>
						{/each}
					</div>
				</div>
			{/if}
			
			<!-- Input Container -->
			<div class="relative flex items-end bg-white border border-gray-300 rounded-2xl shadow-sm hover:border-gray-400 focus-within:border-orange-500 focus-within:ring-2 focus-within:ring-orange-500/20 transition-all duration-200">
				<textarea
					bind:this={textarea}
					bind:value={message}
					on:input={handleInput}
					on:keydown={handleKeydown}
					{placeholder}
					{disabled}
					rows="1"
					class="flex-1 resize-none border-0 outline-0 bg-transparent px-4 py-3 text-[15px] leading-6 text-gray-900 placeholder-gray-500 focus:ring-0 message-input"
					style="min-height: 24px; max-height: 200px;"
				></textarea>
				
				<!-- Send Button -->
				<div class="flex-shrink-0 pr-3 pb-3">
					<button
						on:click={handleSubmit}
						disabled={!message.trim() || disabled}
						class="flex items-center justify-center w-8 h-8 rounded-full transition-all duration-200 {
							message.trim() && !disabled 
								? 'bg-gray-900 hover:bg-gray-800 text-white shadow-sm' 
								: 'bg-gray-100 text-gray-400 cursor-not-allowed'
						}"
						title="Send message"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
						</svg>
					</button>
				</div>
			</div>
			
			<!-- Helper Text -->
			<div class="flex items-center justify-between mt-2 px-2">
				<div class="text-xs text-gray-500">
					Press Enter to send, Shift+Enter for new line • Type # for tags, /doc for documents
				</div>
				<div class="text-xs text-gray-400">
					{message.length}/2000
				</div>
			</div>
		</div>
	</div>
</div>

<!-- Tag Autocomplete -->
<TagAutocomplete
	show={showTagAutocomplete}
	position={tagAutocompletePosition}
	query={tagQuery}
	on:select={handleTagSelect}
/>

<!-- Document Autocomplete -->
<DocumentAutocomplete
	show={showDocumentAutocomplete}
	position={documentAutocompletePosition}
	query={documentQuery}
	on:select={handleDocumentSelect}
/>

<style>
	/* Tag highlighting */
	:global(.message-input) {
		position: relative;
	}
	
	/* Override textarea selection color for tags */
	:global(.message-input::selection) {
		background: rgba(249, 115, 22, 0.2);
	}
	
	/* Custom scrollbar for message input */
	:global(.message-input::-webkit-scrollbar) {
		width: 4px;
	}
	
	:global(.message-input::-webkit-scrollbar-track) {
		background: transparent;
	}
	
	:global(.message-input::-webkit-scrollbar-thumb) {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 2px;
	}
	
	:global(.message-input::-webkit-scrollbar-thumb:hover) {
		background: rgba(156, 163, 175, 0.7);
	}
</style>