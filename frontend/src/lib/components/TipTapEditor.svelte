<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { marked } from 'marked';
	import { Editor } from '@tiptap/core';
	import StarterKit from '@tiptap/starter-kit';
	import Link from '@tiptap/extension-link';
	import { Table, TableRow, TableCell, TableHeader } from '@tiptap/extension-table';
	import TaskList from '@tiptap/extension-task-list';
	import TaskItem from '@tiptap/extension-task-item';
	
	export let content: string = '';
	export let onChange: (html: string, markdown: string) => void = () => {};
	export let placeholder: string = 'Start writing...';
	export let height: string = '400px';
	export let editable: boolean = true;

	let editorElement: HTMLDivElement;
	let editor: any = null;

	// Convert HTML to markdown (basic conversion)
	function htmlToMarkdown(html: string): string {
		// Create a temporary element to parse HTML
		const temp = document.createElement('div');
		temp.innerHTML = html;
		
		let markdown = html;
		
		// Basic HTML to markdown conversion
		markdown = markdown
			.replace(/<strong[^>]*>(.*?)<\/strong>/gi, '**$1**')
			.replace(/<b[^>]*>(.*?)<\/b>/gi, '**$1**')
			.replace(/<em[^>]*>(.*?)<\/em>/gi, '*$1*')
			.replace(/<i[^>]*>(.*?)<\/i>/gi, '*$1*')
			.replace(/<h1[^>]*>(.*?)<\/h1>/gi, '# $1\n')
			.replace(/<h2[^>]*>(.*?)<\/h2>/gi, '## $1\n')
			.replace(/<h3[^>]*>(.*?)<\/h3>/gi, '### $1\n')
			.replace(/<h4[^>]*>(.*?)<\/h4>/gi, '#### $1\n')
			.replace(/<h5[^>]*>(.*?)<\/h5>/gi, '##### $1\n')
			.replace(/<h6[^>]*>(.*?)<\/h6>/gi, '###### $1\n')
			.replace(/<p[^>]*>(.*?)<\/p>/gi, '$1\n\n')
			.replace(/<br\s*\/?>/gi, '\n')
			.replace(/<ul[^>]*>/gi, '')
			.replace(/<\/ul>/gi, '\n')
			.replace(/<ol[^>]*>/gi, '')
			.replace(/<\/ol>/gi, '\n')
			.replace(/<li[^>]*>(.*?)<\/li>/gi, '- $1\n')
			.replace(/<a[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/gi, '[$2]($1)')
			.replace(/<code[^>]*>(.*?)<\/code>/gi, '`$1`')
			.replace(/<pre[^>]*><code[^>]*>(.*?)<\/code><\/pre>/gi, '```\n$1\n```')
			.replace(/<blockquote[^>]*>(.*?)<\/blockquote>/gi, '> $1\n')
			.replace(/<hr\s*\/?>/gi, '---\n')
			.replace(/<[^>]+>/g, '') // Remove remaining HTML tags
			.replace(/&nbsp;/g, ' ')
			.replace(/&lt;/g, '<')
			.replace(/&gt;/g, '>')
			.replace(/&amp;/g, '&')
			.replace(/\n\n+/g, '\n\n') // Clean up multiple newlines
			.trim();
			
		return markdown;
	}

	// Convert markdown to HTML using the marked library (same as the rest of the app)
	function markdownToHTML(markdown: string): string {
		if (!markdown || markdown.trim() === '') {
			return '<p></p>';
		}
		
		try {
			console.log('Converting markdown to HTML:', markdown);
			const html = marked.parse(markdown) as string;
			console.log('Converted HTML:', html);
			return html;
		} catch (error) {
			console.error('Error parsing markdown:', error);
			// Fallback: just wrap in paragraph tags
			return `<p>${markdown.replace(/\n/g, '<br>')}</p>`;
		}
	}

	onMount(() => {
		if (!browser) return;
		
		try {
			console.log('Initializing TipTap editor with content:', content);
			const initialHTML = content ? markdownToHTML(content) : '<p></p>';
			console.log('Initial HTML for editor:', initialHTML);

			// Create the editor
			editor = new Editor({
				element: editorElement,
				extensions: [
					StarterKit.configure({
						heading: {
							levels: [1, 2, 3, 4, 5, 6],
						},
					}),
					Link.configure({
						openOnClick: false,
						HTMLAttributes: {
							class: 'text-blue-600 underline hover:text-blue-800',
						},
					}),
					Table.configure({
						resizable: true,
					}),
					TableRow,
					TableHeader,
					TableCell,
					TaskList,
					TaskItem.configure({
						nested: true,
					}),
				],
				content: initialHTML,
				editable: editable,
				onUpdate: ({ editor }) => {
					if (!isUpdatingFromProp) {
						const html = editor.getHTML();
						const markdown = htmlToMarkdown(html);
						console.log('Editor updated - HTML:', html, 'Markdown:', markdown);
						onChange(html, markdown);
					}
				},
				onCreate: ({ editor }) => {
					console.log('Editor created successfully');
				},
				editorProps: {
					attributes: {
						class: 'prose prose-sm max-w-none focus:outline-none p-4 min-h-[300px]',
						'data-placeholder': placeholder,
					},
				},
				parseOptions: {
					preserveWhitespace: 'full',
				},
			});

		} catch (error) {
			console.error('Failed to initialize TipTap editor:', error);
		}
	});

	onDestroy(() => {
		if (editor) {
			editor.destroy();
		}
	});

	// Function to add formatting
	export function toggleBold() {
		editor?.chain().focus().toggleBold().run();
	}

	export function toggleItalic() {
		editor?.chain().focus().toggleItalic().run();
	}

	export function toggleCode() {
		editor?.chain().focus().toggleCode().run();
	}

	export function setHeading(level: number) {
		editor?.chain().focus().toggleHeading({ level }).run();
	}

	export function toggleBulletList() {
		editor?.chain().focus().toggleBulletList().run();
	}

	export function toggleOrderedList() {
		editor?.chain().focus().toggleOrderedList().run();
	}

	export function addLink(url: string) {
		editor?.chain().focus().setLink({ href: url }).run();
	}

	export function removeLink() {
		editor?.chain().focus().unsetLink().run();
	}

	// Update editor content when prop changes (but not during user editing)
	let isUpdatingFromProp = false;
	$: if (editor && content !== undefined && !isUpdatingFromProp) {
		const newHTML = markdownToHTML(content);
		const currentHTML = editor.getHTML();
		const currentMarkdown = htmlToMarkdown(currentHTML);
		
		// Only update if the content actually differs and we're not in the middle of editing
		if (currentMarkdown !== content && !editor.isFocused) {
			console.log('Updating editor content from external source');
			isUpdatingFromProp = true;
			editor.commands.setContent(newHTML);
			setTimeout(() => {
				isUpdatingFromProp = false;
			}, 100);
		}
	}

	// Update editable state
	$: if (editor) {
		editor.setEditable(editable);
	}
</script>

<div class="tiptap-editor border border-gray-300 rounded-lg overflow-hidden bg-white" style="height: {height};">
	<!-- Toolbar -->
	{#if editable}
		<div class="border-b border-gray-200 p-2 flex flex-wrap gap-1 bg-gray-50">
			<button
				type="button"
				on:click={toggleBold}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('bold') ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Bold (Ctrl+B)"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
					<path d="M6 4c0-.553.447-1 1-1h4.5c1.381 0 2.5 1.119 2.5 2.5 0 .617-.22 1.17-.6 1.6.816.392 1.4 1.17 1.4 2.1 0 1.381-1.119 2.8-2.5 2.8H7c-.553 0-1-.447-1-1V4zm2 1v2h3.5c.275 0 .5-.225.5-.5S11.775 6 11.5 6H8zm0 4v3h4c.275 0 .5-.225.5-.5s-.225-.5-.5-.5H8z"/>
				</svg>
			</button>
			
			<button
				type="button"
				on:click={toggleItalic}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('italic') ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Italic (Ctrl+I)"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
					<path d="M8 2h6v2h-1.5l-2 10H12v2H6v-2h1.5l2-10H8V2z"/>
				</svg>
			</button>

			<button
				type="button"
				on:click={toggleCode}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('code') ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Inline Code"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clip-rule="evenodd"/>
				</svg>
			</button>

			<div class="border-l border-gray-300 mx-2"></div>

			<button
				type="button"
				on:click={() => setHeading(1)}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('heading', { level: 1 }) ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Heading 1"
			>
				H1
			</button>

			<button
				type="button"
				on:click={() => setHeading(2)}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('heading', { level: 2 }) ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Heading 2"
			>
				H2
			</button>

			<button
				type="button"
				on:click={() => setHeading(3)}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('heading', { level: 3 }) ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Heading 3"
			>
				H3
			</button>

			<div class="border-l border-gray-300 mx-2"></div>

			<button
				type="button"
				on:click={toggleBulletList}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('bulletList') ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Bullet List"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"/>
				</svg>
			</button>

			<button
				type="button"
				on:click={toggleOrderedList}
				class="p-2 rounded hover:bg-gray-200 transition-colors {editor?.isActive('orderedList') ? 'bg-blue-100 text-blue-700' : 'text-gray-700'}"
				title="Numbered List"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"/>
				</svg>
			</button>
		</div>
	{/if}

	<!-- Editor Content -->
	<div 
		bind:this={editorElement}
		class="h-full overflow-y-auto"
		style="height: calc({height} - {editable ? '60px' : '0px'});"
	></div>
</div>

<style>
	/* TipTap Editor Styles */
	:global(.tiptap-editor .ProseMirror) {
		outline: none;
		height: 100%;
		overflow-y: auto;
	}

	:global(.tiptap-editor .ProseMirror h1) {
		font-size: 1.5em;
		font-weight: 600;
		margin: 1.5em 0 0.5em 0;
		color: #1f2937;
	}

	:global(.tiptap-editor .ProseMirror h2) {
		font-size: 1.3em;
		font-weight: 600;
		margin: 1.5em 0 0.5em 0;
		color: #1f2937;
	}

	:global(.tiptap-editor .ProseMirror h3) {
		font-size: 1.15em;
		font-weight: 600;
		margin: 1.5em 0 0.5em 0;
		color: #1f2937;
	}

	:global(.tiptap-editor .ProseMirror p) {
		margin: 0 0 1em 0;
		line-height: 1.7;
		color: #374151;
	}

	:global(.tiptap-editor .ProseMirror strong) {
		color: #1f2937;
		font-weight: 600;
	}

	:global(.tiptap-editor .ProseMirror em) {
		color: #1f2937;
	}

	:global(.tiptap-editor .ProseMirror code) {
		background: #f3f4f6;
		color: #ec4899;
		padding: 0.125rem 0.25rem;
		border-radius: 0.25rem;
		font-size: 0.875em;
		font-family: 'Monaco', 'Courier New', monospace;
	}

	:global(.tiptap-editor .ProseMirror pre) {
		background: #1f2937;
		color: #e5e7eb;
		padding: 1rem;
		border-radius: 0.5rem;
		overflow-x: auto;
		margin: 1em 0;
	}

	:global(.tiptap-editor .ProseMirror pre code) {
		background: transparent;
		color: inherit;
		padding: 0;
	}

	:global(.tiptap-editor .ProseMirror ul),
	:global(.tiptap-editor .ProseMirror ol) {
		margin: 0 0 1em 1.5em;
	}

	:global(.tiptap-editor .ProseMirror li) {
		margin-bottom: 0.25em;
		color: #374151;
	}

	:global(.tiptap-editor .ProseMirror a) {
		color: #2563eb;
		text-decoration: underline;
	}

	:global(.tiptap-editor .ProseMirror a:hover) {
		color: #1d4ed8;
	}

	:global(.tiptap-editor .ProseMirror blockquote) {
		border-left: 4px solid #3b82f6;
		background: #eff6ff;
		padding: 0.75rem 1rem;
		margin: 1em 0;
		color: #374151;
	}

	:global(.tiptap-editor .ProseMirror hr) {
		border: none;
		border-top: 1px solid #d1d5db;
		margin: 1.5em 0;
	}

	/* Placeholder */
	:global(.tiptap-editor .ProseMirror p.is-editor-empty:first-child::before) {
		content: attr(data-placeholder);
		float: left;
		color: #9ca3af;
		pointer-events: none;
		height: 0;
	}
</style>