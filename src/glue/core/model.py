# src/glue/core/model.py
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ModelConfig:
    """Configuration for a model"""
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop_sequences: list[str] = field(default_factory=list)
    system_prompt: Optional[str] = None

class Model:
    """Base class for individual models within a CBM"""
    def __init__(
        self, 
        name: str,
        provider: str,
        api_key: Optional[str] = None,
        config: Optional[ModelConfig] = None
    ):
        self.name = name
        self.provider = provider
        self.api_key = api_key
        self.config = config or ModelConfig()
        self.role: Optional[str] = None
        self._prompts: Dict[str, str] = {}
        self._tools: Dict[str, Any] = {}
        self._bound_models: Dict[str, 'Model'] = {}

    def add_prompt(self, name: str, content: str) -> None:
        """Add a prompt template"""
        self._prompts[name] = content

    def get_prompt(self, name: str) -> Optional[str]:
        """Get a prompt template"""
        return self._prompts.get(name)

    def set_role(self, role: str) -> None:
        """Set the model's role in the CBM"""
        self.role = role
        # Also set as system prompt if not already set
        if not self.config.system_prompt:
            self.config.system_prompt = role

    def add_tool(self, name: str, tool: Any) -> None:
        """Add a tool that this model can use"""
        self._tools[name] = tool

    def bind_to(self, model: 'Model', binding_type: str = 'glue') -> None:
        """Create a binding to another model"""
        self._bound_models[model.name] = model
        
    async def generate(self, prompt: str) -> str:
        """Generate a response (to be implemented by provider-specific classes)"""
        raise NotImplementedError
