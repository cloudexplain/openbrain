import asyncio
import random
import time
from typing import AsyncGenerator, Optional
from openai import AsyncAzureOpenAI, RateLimitError
from openai._exceptions import APIStatusError
from app.config import get_settings
import tiktoken
import logging

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=get_settings().azure_openai_api_key,
            api_version=get_settings().azure_openai_api_version,
            azure_endpoint=get_settings().azure_openai_endpoint
        )
        self.deployment_name = get_settings().azure_openai_deployment_name
        self.embedding_deployment_name = get_settings().azure_openai_embedding_deployment_name
        
        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except KeyError:
            # Fallback to cl100k_base encoding
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))
    
    async def _execute_with_retry(self, operation, max_retries: int = 3):
        """Execute an operation with exponential backoff for rate limits"""
        for attempt in range(max_retries):
            try:
                return await operation()
            except (RateLimitError, APIStatusError) as e:
                # Check if it's a rate limit error (429 status code)
                is_rate_limit = (
                    isinstance(e, RateLimitError) or
                    (isinstance(e, APIStatusError) and e.status_code == 429) or
                    "429" in str(e) or
                    "rate limit" in str(e).lower()
                )

                if not is_rate_limit:
                    # Not a rate limit error, don't retry
                    logger.error(f"Azure OpenAI API error: {str(e)}")
                    raise Exception(f"Azure OpenAI API error: {str(e)}")

                if attempt == max_retries - 1:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts: {str(e)}")
                    raise Exception(f"Rate limit exceeded after {max_retries} attempts. Please try again later.")

                # Extract retry-after from headers if available
                retry_after = None
                if hasattr(e, 'response') and e.response and hasattr(e.response, 'headers'):
                    retry_after = e.response.headers.get('retry-after') or e.response.headers.get('Retry-After')

                if retry_after:
                    delay = min(float(retry_after) + random.uniform(0, 2), 60)
                else:
                    # Exponential backoff: 2^attempt + jitter
                    delay = min(2 ** attempt + random.uniform(0, 1), 60)

                logger.warning(f"Rate limit hit, retrying in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
            except Exception as e:
                # For other non-rate-limit errors, don't retry
                logger.error(f"Azure OpenAI API error: {str(e)}")
                raise Exception(f"Azure OpenAI API error: {str(e)}")

    async def generate_chat_completion(
        self,
        messages: list,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Generate chat completion with streaming support and rate limit retry"""
        async def _generate():
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                stream=stream,
                # temperature=temperature,
                max_completion_tokens=max_tokens,
            )
            print("response", response)
            return response

        response = await self._execute_with_retry(_generate)

        if stream:
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            if response.choices:
                yield response.choices[0].message.content or ""
    
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embeddings for text with rate limit retry"""
        async def _generate():
            return await self.client.embeddings.create(
                model=self.embedding_deployment_name,
                input=text
            )

        response = await self._execute_with_retry(_generate)
        return response.data[0].embedding

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts with rate limit retry"""
        async def _generate():
            return await self.client.embeddings.create(
                model=self.embedding_deployment_name,
                input=texts
            )

        response = await self._execute_with_retry(_generate)
        return [data.embedding for data in response.data]


# Global service instance
azure_openai_service = AzureOpenAIService()