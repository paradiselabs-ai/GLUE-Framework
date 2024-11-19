# src/glue/providers/openrouter.py

"""OpenRouter Provider Implementation"""

import os
import json
import aiohttp
from typing import Dict, Any, Optional
from .base import BaseProvider
from ..core.model import ModelConfig

class OpenRouterProvider(BaseProvider):
    """Provider for OpenRouter API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "liquid/lfm-40b:free",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        # Create model config
        config = ModelConfig(
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt
        )
        
        # Initialize base provider
        super().__init__(
            name=model,
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            config=config,
            base_url="https://openrouter.ai/api/v1"
        )
        
        if not self.api_key:
            raise ValueError("OpenRouter API key not found")
    
    async def _prepare_request(self, prompt: str) -> Dict[str, Any]:
        """Prepare request for OpenRouter API"""
        messages = []
        
        # Add system prompt if provided
        if self.config.system_prompt:
            messages.append({
                "role": "system",
                "content": self.config.system_prompt
            })
        
        # Add user prompt
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return {
            "model": self.name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "presence_penalty": self.config.presence_penalty,
            "frequency_penalty": self.config.frequency_penalty,
            "stop": self.config.stop_sequences if self.config.stop_sequences else None
        }
    
    async def _process_response(self, response: Dict[str, Any]) -> str:
        """Process response from OpenRouter API"""
        return response["choices"][0]["message"]["content"]
    
    async def _make_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make request to OpenRouter API"""
        headers = self._get_headers()
        headers["HTTP-Referer"] = "https://github.com/paradiseLabs/glue"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=request_data
            ) as response:
                result = await response.json()
                
                if response.status != 200:
                    await self._handle_error(Exception(f"OpenRouter API error: {result}"))
                
                return result
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle OpenRouter API errors"""
        # For now, just raise the error
        raise error
