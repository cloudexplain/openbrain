const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface Message {
	id: string;
	content: string;
	role: 'user' | 'assistant';
	timestamp: Date;
	chat_id: string;
	token_count?: number;
}

export interface Chat {
	id: string;
	title: string;
	created_at: string;
	updated_at: string;
	messages: Message[];
}

export interface ChatListItem {
	id: string;
	title: string;
	created_at: string;
	updated_at: string;
	last_message?: string;
	message_count: number;
}

export interface StreamResponse {
	type: 'content' | 'done' | 'error';
	content?: string;
	message_id?: string;
	chat_id?: string;
	error?: string;
}

class ApiClient {
	private baseUrl: string;

	constructor(baseUrl: string = API_BASE_URL) {
		this.baseUrl = baseUrl;
	}

	private async request(endpoint: string, options: RequestInit = {}): Promise<Response> {
		const url = `${this.baseUrl}${endpoint}`;
		const response = await fetch(url, {
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			...options
		});

		if (!response.ok) {
			throw new Error(`API request failed: ${response.status} ${response.statusText}`);
		}

		return response;
	}

	async getChats(): Promise<ChatListItem[]> {
		const response = await this.request('/chats');
		const chats = await response.json();
		
		return chats.map((chat: any) => ({
			...chat,
			timestamp: new Date(chat.updated_at)
		}));
	}

	async getChat(chatId: string): Promise<Chat> {
		const response = await this.request(`/chats/${chatId}`);
		const chat = await response.json();
		
		return {
			...chat,
			messages: chat.messages.map((msg: any) => ({
				...msg,
				timestamp: new Date(msg.created_at)
			}))
		};
	}

	async createChat(title: string): Promise<Chat> {
		const response = await this.request('/chats', {
			method: 'POST',
			body: JSON.stringify({ title })
		});
		
		return await response.json();
	}

	async deleteChat(chatId: string): Promise<void> {
		await this.request(`/chats/${chatId}`, {
			method: 'DELETE'
		});
	}

	async sendMessage(message: string, chatId?: string): Promise<ReadableStream<StreamResponse>> {
		const response = await fetch(`${this.baseUrl}/chat`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				message,
				chat_id: chatId || null
			})
		});

		if (!response.ok) {
			throw new Error(`Chat request failed: ${response.status} ${response.statusText}`);
		}

		if (!response.body) {
			throw new Error('No response body received');
		}

		// Create a readable stream that parses SSE data
		const reader = response.body.getReader();
		const decoder = new TextDecoder();

		return new ReadableStream<StreamResponse>({
			start(controller) {
				let buffer = '';

				function pump(): Promise<void> {
					return reader.read().then(({ done, value }) => {
						if (done) {
							controller.close();
							return;
						}

						buffer += decoder.decode(value, { stream: true });
						const lines = buffer.split('\n');
						buffer = lines.pop() || '';

						for (const line of lines) {
							if (line.startsWith('data: ')) {
								try {
									const data = JSON.parse(line.slice(6));
									controller.enqueue(data);
								} catch (error) {
									console.error('Error parsing SSE data:', error);
								}
							}
						}

						return pump();
					}).catch((error) => {
						controller.error(error);
					});
				}

				return pump();
			}
		});
	}
}

export const apiClient = new ApiClient();