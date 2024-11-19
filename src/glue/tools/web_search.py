# src/glue/tools/web_search.py

"""Web Search Tool Implementation"""

from typing import Dict, List, Optional, Any, Type
from .base import ToolConfig, ToolPermission
from .magnetic import MagneticTool
from ..magnetic.field import AttractionStrength
from .search_providers import get_provider, SearchProvider, GenericSearchProvider

class WebSearchTool(MagneticTool):
    """Tool for performing web searches with magnetic capabilities"""
    
    def __init__(
        self,
        api_key: str,
        name: str = "web_search",
        description: str = "Performs web searches and returns results",
        provider: str = "serp",
        max_results: int = 5,
        strength: AttractionStrength = AttractionStrength.MEDIUM,
        **provider_config
    ):
        super().__init__(
            name=name,
            description=description,
            strength=strength,
            config=ToolConfig(
                required_permissions=[
                    ToolPermission.NETWORK,
                    ToolPermission.READ,
                    ToolPermission.MAGNETIC
                ],
                timeout=10.0,
                cache_results=True
            )
        )
        
        # Get provider class and config
        provider_class = get_provider(provider, **provider_config)
        
        # If endpoint not in config but provider has default endpoint, add it
        if issubclass(provider_class, GenericSearchProvider):
            provider_endpoints = {
                "tavily": "https://api.tavily.com/search",
                "serp": "https://serpapi.com/search",
                "bing": "https://api.bing.microsoft.com/v7.0/search",
                "you": "https://api.you.com/search",
            }
            if provider in provider_endpoints and "endpoint" not in provider_config:
                provider_config["endpoint"] = provider_endpoints[provider]
        
        # Initialize provider
        self.provider = provider_class(
            api_key=api_key,
            **provider_config
        )
        self.max_results = max_results

    async def initialize(self) -> None:
        """Initialize search provider"""
        await self.provider.initialize()
        await super().initialize()

    async def cleanup(self) -> None:
        """Clean up search provider"""
        await self.provider.cleanup()
        await super().cleanup()

    async def prepare_input(self, input_data: Any) -> str:
        """Prepare input for search"""
        # If input is a string, use it directly
        if isinstance(input_data, str):
            return input_data
        
        # If input is a dict with a 'query' field, use that
        if isinstance(input_data, dict) and 'query' in input_data:
            return input_data['query']
        
        # Otherwise, convert to string
        return str(input_data)

    async def execute(self, input_data: Any, **kwargs) -> List[Dict[str, str]]:
        """
        Execute web search with state awareness
        
        Args:
            input_data: Search query (can be string, dict with query field, or other)
            **kwargs: Additional search parameters
            
        Returns:
            List of search results, each containing title, url, and snippet
            
        Raises:
            ResourceLockedException: If tool is locked
            ResourceStateException: If tool is not in a field
            RuntimeError: If search request or processing fails
        """
        # State checks handled by parent
        await super().execute(input_data=input_data, **kwargs)
        
        try:
            # Get query from input
            query = await self.prepare_input(input_data)
            
            # Perform search
            results = await self.provider.search(
                query=query,
                max_results=self.max_results,
                **kwargs
            )
            
            # Convert to dictionary format
            return [result.to_dict() for result in results]
            
        except Exception as e:
            raise RuntimeError(f"Search failed: {str(e)}")

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.description} "
            f"(Magnetic Web Search Tool, Provider: {self.provider}, "
            f"Strength: {self.strength.name}, State: {self._state.name})"
        )
