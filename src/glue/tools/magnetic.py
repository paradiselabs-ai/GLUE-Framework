# src/glue/tools/magnetic.py

# ==================== Imports ====================
from typing import Any, Dict, List, Optional, Type, Tuple
from ..magnetic.field import MagneticResource, AttractionStrength, ResourceState
from .base import BaseTool, ToolConfig, ToolPermission

# ==================== Exceptions ====================
class ResourceLockedException(Exception):
    """Raised when attempting to use a locked resource"""
    pass

class ResourceStateException(Exception):
    """Raised when resource is in invalid state for operation"""
    pass

# ==================== Main Classes ====================
class MagneticTool(BaseTool, MagneticResource):
    """
    Base class for tools with magnetic capabilities.
    
    Combines tool functionality with magnetic resource features for:
    - State-aware execution
    - Resource sharing
    - Field management
    - Event propagation
    - Tool chaining
    
    Example:
        ```python
        class WebSearchTool(MagneticTool):
            async def execute(self, **kwargs):
                # State and permissions checked automatically
                return await super().execute(**kwargs)
        
        async with MagneticField("research") as field:
            tool = WebSearchTool()
            field.add_resource(tool)
            result = await tool.execute(query="search term")
        ```
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        strength: AttractionStrength = AttractionStrength.MEDIUM,
        config: Optional[ToolConfig] = None
    ):
        """
        Initialize magnetic tool.
        
        Args:
            name: Tool name
            description: Tool description
            strength: Magnetic strength
            config: Tool configuration
        """
        # Initialize tool with magnetic permission
        base_config = config or ToolConfig(required_permissions=[])
        if ToolPermission.MAGNETIC not in base_config.required_permissions:
            base_config.required_permissions.append(ToolPermission.MAGNETIC)
        
        # Initialize both parent classes
        BaseTool.__init__(self, name, description, base_config)
        MagneticResource.__init__(self, name, strength)
    
    async def execute(self, **kwargs) -> Any:
        """
        Execute tool with state awareness.
        
        Checks:
        - Resource state
        - Lock status
        - Field membership
        - Required permissions
        
        Raises:
            ResourceLockedException: If resource is locked
            ResourceStateException: If in invalid state
            PermissionError: If missing permissions
        """
        # Check resource state
        if self._state == ResourceState.LOCKED:
            raise ResourceLockedException(
                f"Tool {self.name} is locked by {self._lock_holder.name}"
            )
        
        # Check field membership
        if not self._current_field:
            raise ResourceStateException(
                f"Tool {self.name} is not in any magnetic field"
            )
        
        # Track shared usage
        was_idle = self._state == ResourceState.IDLE
        if was_idle:
            self._state = ResourceState.ACTIVE
        
        try:
            # Execute with parent implementation
            result = await super().execute(**kwargs)
            
            # Update state if was idle
            if was_idle:
                if self._attracted_to:
                    self._state = ResourceState.SHARED
                else:
                    self._state = ResourceState.IDLE
                    
            return result
            
        except Exception as e:
            # Reset state on error if was idle
            if was_idle:
                self._state = ResourceState.IDLE
            raise e
    
    async def initialize(self) -> None:
        """Initialize tool and magnetic resources"""
        await BaseTool.initialize(self)
        self._state = ResourceState.IDLE
    
    async def cleanup(self) -> None:
        """Clean up tool and magnetic resources"""
        # Clean up magnetic resources
        await MagneticResource.exit_field(self)
        # Clean up tool resources
        await BaseTool.cleanup(self)
    
    async def enter_field(self, field: 'MagneticField') -> None:
        """Enter a magnetic field"""
        if self._current_field and self._current_field != field:
            await self.exit_field()
        self._current_field = field
        self._state = ResourceState.IDLE
    
    def __rshift__(self, other: 'MagneticTool') -> Tuple['MagneticTool', 'MagneticTool']:
        """Support >> operator for tool chaining"""
        return (self, other)
    
    def __str__(self) -> str:
        """String representation"""
        return (
            f"{self.name}: {self.description} "
            f"(Magnetic Tool, Strength: {self.strength.name}, "
            f"State: {self._state.name})"
        )
