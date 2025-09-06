import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	// Simple loader - actual document loading happens client-side
	// This allows for search and filtering without page reloads
	return {
		title: 'Knowledge Base'
	};
};