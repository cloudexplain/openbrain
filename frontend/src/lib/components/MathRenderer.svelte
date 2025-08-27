<script lang="ts">
	import { marked } from 'marked';
	import katex from 'katex';
	
	export let content: string;
	
	// Types for our content segments
	type ContentSegment = {
		type: 'text' | 'math';
		content: string;
		display?: boolean; // for math segments
	};
	
	// Configure marked options
	marked.setOptions({
		breaks: true,
		gfm: true,
	});
	
	// Parse content into segments, grouping inline math with surrounding text
	function parseContent(rawContent: string): ContentSegment[] {
		const segments: ContentSegment[] = [];
		
		// First, find all display math expressions (these will be separate segments)
		const displayMathExpressions = [];
		let match;
		
		// Find \begin{equation}...\end{equation}
		const equationRegex = /\\begin\{equation\}([\s\S]*?)\\end\{equation\}/g;
		while ((match = equationRegex.exec(rawContent)) !== null) {
			displayMathExpressions.push({
				start: match.index,
				end: match.index + match[0].length,
				tex: match[1].trim(),
				type: 'display'
			});
		}
		
		// Find $$...$$ display math
		const displayMathRegex = /\$\$([\s\S]*?)\$\$/g;
		while ((match = displayMathRegex.exec(rawContent)) !== null) {
			displayMathExpressions.push({
				start: match.index,
				end: match.index + match[0].length,
				tex: match[1].trim(),
				type: 'display'
			});
		}
		
		// Find \[...\] display math
		const latexDisplayRegex = /\\\[([\s\S]*?)\\\]/g;
		while ((match = latexDisplayRegex.exec(rawContent)) !== null) {
			displayMathExpressions.push({
				start: match.index,
				end: match.index + match[0].length,
				tex: match[1].trim(),
				type: 'display'
			});
		}
		
		// Sort display math by position
		displayMathExpressions.sort((a, b) => a.start - b.start);
		
		// Split content by display math expressions
		let lastEnd = 0;
		
		for (const displayExpr of displayMathExpressions) {
			// Add text segment before display math (may contain inline math)
			if (displayExpr.start > lastEnd) {
				const textContent = rawContent.slice(lastEnd, displayExpr.start);
				if (textContent.trim()) {
					segments.push({
						type: 'text',
						content: textContent
					});
				}
			}
			
			// Add display math as separate segment
			segments.push({
				type: 'math',
				content: displayExpr.tex,
				display: true
			});
			
			lastEnd = displayExpr.end;
		}
		
		// Add remaining text (may contain inline math)
		if (lastEnd < rawContent.length) {
			const textContent = rawContent.slice(lastEnd);
			if (textContent.trim()) {
				segments.push({
					type: 'text',
					content: textContent
				});
			}
		}
		
		// If no display math found, return whole content as text
		if (segments.length === 0) {
			segments.push({
				type: 'text',
				content: rawContent
			});
		}
		
		return segments;
	}
	
	// Process content reactively
	$: segments = parseContent(content);
	
	// Function to render markdown text with inline math
	function renderMarkdown(text: string): string {
		// First process inline math within the text
		let processedText = text;
		
		// Find and replace inline math expressions
		// \(...\) inline math
		processedText = processedText.replace(/\\\((.*?)\\\)/g, (match, tex) => {
			return renderMath(tex.trim(), false);
		});
		
		// $...$ inline math (but not currency)
		processedText = processedText.replace(/\$(?!\d)([^\$\n]+?)\$/g, (match, tex) => {
			if (/^\d/.test(tex.trim())) {
				return match; // Keep currency as-is
			}
			return renderMath(tex.trim(), false);
		});
		
		// Then process with markdown
		return marked.parse(processedText) as string;
	}
	
	// Function to render LaTeX
	function renderMath(tex: string, display: boolean = false): string {
		try {
			return katex.renderToString(tex, {
				displayMode: display,
				throwOnError: false,
				trust: true,
				macros: {
					"\\RR": "\\mathbb{R}",
					"\\NN": "\\mathbb{N}",
					"\\ZZ": "\\mathbb{Z}",
					"\\QQ": "\\mathbb{Q}",
					"\\CC": "\\mathbb{C}"
				}
			});
		} catch (e) {
			console.error('KaTeX rendering error:', e);
			return `<code class="latex-error">${tex}</code>`;
		}
	}
</script>

<div class="math-content">
	{#each segments as segment}
		{#if segment.type === 'text'}
			{@html renderMarkdown(segment.content)}
		{:else if segment.type === 'math' && segment.display}
			<div class="math-display">
				{@html renderMath(segment.content, true)}
			</div>
		{/if}
	{/each}
</div>

<style>
	:global(.math-content) {
		word-wrap: break-word;
		overflow-wrap: break-word;
		line-height: 1.6;
	}
	
	/* LaTeX math styles */
	:global(.math-display) {
		display: block;
		margin: 1em 0;
		text-align: center;
		overflow-x: auto;
		overflow-y: hidden;
	}
	
	:global(.math-inline) {
		display: inline;
		margin: 0 0.1em;
	}
	
	:global(.math-block) {
		display: block;
		margin: 1em 0;
		text-align: center;
		overflow-x: auto;
		padding: 1em;
		background: rgba(0, 0, 0, 0.03);
		border-radius: 4px;
	}
	
	/* KaTeX specific styles */
	:global(.katex) {
		font-size: 1.05em;
	}
	
	:global(.katex-display) {
		overflow-x: auto;
		overflow-y: hidden;
		padding: 0.5em 0;
	}
	
	:global(.latex-error) {
		color: #cc0000;
		background: #fee;
		padding: 0.2em 0.4em;
		border-radius: 3px;
		font-family: monospace;
		font-size: 0.9em;
	}
	
	/* Ensure math doesn't break layout */
	:global(.katex-display > .katex) {
		max-width: 100%;
	}
	
	/* Override some default marked styles for better integration */
	:global(.math-content p) {
		margin-bottom: 1em;
	}
	
	:global(.math-content ul),
	:global(.math-content ol) {
		margin-left: 1.5em;
		margin-bottom: 1em;
	}
	
	:global(.math-content li) {
		margin-bottom: 0.25em;
	}
	
	:global(.math-content blockquote) {
		border-left: 4px solid #ddd;
		padding-left: 1em;
		margin-left: 0;
		color: #666;
	}
	
	:global(.math-content h1),
	:global(.math-content h2),
	:global(.math-content h3),
	:global(.math-content h4),
	:global(.math-content h5),
	:global(.math-content h6) {
		margin-top: 1.5em;
		margin-bottom: 0.5em;
		font-weight: 600;
	}
	
	:global(.math-content h1) { font-size: 1.5em; }
	:global(.math-content h2) { font-size: 1.3em; }
	:global(.math-content h3) { font-size: 1.15em; }
	:global(.math-content h4) { font-size: 1.05em; }
	:global(.math-content h5) { font-size: 1em; }
	:global(.math-content h6) { font-size: 0.95em; }
	
	:global(.math-content table) {
		border-collapse: collapse;
		margin: 1em 0;
		width: 100%;
	}
	
	:global(.math-content th),
	:global(.math-content td) {
		border: 1px solid #ddd;
		padding: 0.5em;
		text-align: left;
	}
	
	:global(.math-content th) {
		background: #f5f5f5;
		font-weight: 600;
	}
	
	:global(.math-content hr) {
		border: none;
		border-top: 1px solid #ddd;
		margin: 1.5em 0;
	}
</style>