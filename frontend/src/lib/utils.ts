import type { Cookies } from '@sveltejs/kit';

export function getAuthHeaders(cookies: Cookies): HeadersInit {
	const sessionId = cookies.get('sessionid');
	if (sessionId) {
		return {
			'Cookie': `sessionid=${sessionId}`
		};
	}
	return {};
}
