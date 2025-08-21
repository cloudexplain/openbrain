import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
	console.log(`[Hooks] Incoming request: ${event.request.method} ${event.url.pathname}`);
	console.log(`[Hooks] Full URL: ${event.url.href}`);
	
	// Special logging for upload endpoint
	if (event.url.pathname === '/api/v1/documents/upload') {
		console.log(`[Hooks] UPLOAD ENDPOINT HIT!`);
		console.log(`[Hooks] Content-Type:`, event.request.headers.get('content-type'));
		console.log(`[Hooks] Content-Length:`, event.request.headers.get('content-length'));
		console.log(`[Hooks] All Headers:`, Array.from(event.request.headers.entries()));
	}
	
	// Proxy all API requests to backend
	if (event.url.pathname.startsWith('/api')) {
		const backendUrl = `http://backend:8000${event.url.pathname}${event.url.search}`;
		
		console.log(`[Proxy] MATCHED API PATH`);
		console.log(`[Proxy] ${event.request.method} ${event.url.pathname} -> ${backendUrl}`);
		
		try {
			const fetchOptions: RequestInit = {
				method: event.request.method,
				headers: event.request.headers,
			};
			
			// Add body and duplex option for non-GET/HEAD requests
			if (event.request.method !== 'GET' && event.request.method !== 'HEAD') {
				fetchOptions.body = event.request.body;
				// @ts-ignore - duplex is required for Node.js fetch with streams
				fetchOptions.duplex = 'half';
			}
			
			const response = await fetch(backendUrl, fetchOptions);
			
			console.log(`[Proxy] Response: ${response.status} ${response.statusText}`);
			console.log(`[Proxy] Response headers:`, Array.from(response.headers.entries()));
			
			// Return raw response - no JSON parsing
			return new Response(response.body, {
				status: response.status,
				statusText: response.statusText,
				headers: response.headers
			});
		} catch (error) {
			console.error('[Proxy] Error forwarding request:', error);
			return new Response('Backend service unavailable', { status: 503 });
		}
	}
	
	// For all other requests, proceed normally
	console.log(`[Hooks] NOT an API path, proceeding normally`);
	const response = await resolve(event);
	console.log(`[Hooks] Normal response: ${response.status}`);
	return response;
};