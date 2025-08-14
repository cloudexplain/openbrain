import asyncio
from typing import AsyncGenerator, Optional
from openai import AsyncAzureOpenAI
from app.config import settings
import tiktoken


class AzureOpenAIService:
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        self.deployment_name = settings.azure_openai_deployment_name
        self.embedding_deployment_name = settings.azure_openai_embedding_deployment_name
        
        # Initialize tokenizer for token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except KeyError:
            # Fallback to cl100k_base encoding
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))
    
    async def generate_chat_completion(
        self, 
        messages: list,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Generate chat completion with streaming support"""
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                stream=stream,
                # temperature=temperature,
                max_completion_tokens=max_tokens,
            )
            print("response", response)
            
            if stream:
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                if response.choices:
                    yield response.choices[0].message.content or ""
                    
        except Exception as e:
            raise Exception(f"Azure OpenAI API error: {str(e)}")
    
    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embeddings for text"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_deployment_name,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Azure OpenAI Embedding API error: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_deployment_name,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            raise Exception(f"Azure OpenAI Batch Embedding API error: {str(e)}")


# Global service instance
azure_openai_service = AzureOpenAIService()