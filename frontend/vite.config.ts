import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	optimizeDeps: {
		include: [
			'@tiptap/core',
			'@tiptap/starter-kit',
			'@tiptap/extension-link',
			'@tiptap/extension-table',
			'@tiptap/extension-task-list',
			'@tiptap/extension-task-item'
		]
	}
});
