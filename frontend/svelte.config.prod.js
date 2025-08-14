import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			// Options for the Node.js adapter
			out: 'build',
			precompress: false,
			envPrefix: ''
		}),
		csrf: {
			checkOrigin: false
		}
	}
};

export default config;
