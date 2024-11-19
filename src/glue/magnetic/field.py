# src/glue/magnetic/field.py

# ==================== Imports ====================
from typing import Any, Dict, List, Optional, Set, Type, Callable
from enum import Enum, auto
from contextlib import asynccontextmanager
import asyncio
from dataclasses import dataclass, field
from collections import defaultdict

# ==================== Enums ====================
class AttractionStrength(Enum):
    """Magnetic attraction strength levels"""
    WEAK = 1      # Easily broken, temporary bindings
    MEDIUM = 2    # Standard strength for most operations
    STRONG = 3    # High priority, persistent bindings
    SUPER = 4     # Immutable, permanent bindings

class ResourceState(Enum):
    """States a resource can be in"""
    IDLE = auto()      # Not currently in use
    ACTIVE = auto()    # Currently in use
    LOCKED = auto()    # Cannot be used by others
    SHARED = auto()    # Being shared between resources

# ==================== Event Types ====================
class FieldEvent:
    """Base class for field events"""
    pass

class ResourceAddedEvent(FieldEvent):
    """Event fired when a resource is added to the field"""
    def __init__(self, resource: 'MagneticResource'):
        self.resource = resource

class ResourceRemovedEvent(FieldEvent):
    """Event fired when a resource is removed from the field"""
    def __init__(self, resource: 'MagneticResource'):
        self.resource = resource

class AttractionEvent(FieldEvent):
    """Event fired when resources are attracted"""
    def __init__(self, source: 'MagneticResource', target: 'MagneticResource'):
        self.source = source
        self.target = target

class RepulsionEvent(FieldEvent):
    """Event fired when resources are repelled"""
    def __init__(self, source: 'MagneticResource', target: 'MagneticResource'):
        self.source = source
        self.target = target

# ==================== Data Classes ====================
class MagneticResource:
    """Base class for resources that can be shared via magnetic fields"""
    def __init__(
        self,
        name: str,
        strength: AttractionStrength = AttractionStrength.MEDIUM
    ):
        self.name = name
        self.strength = strength
        self._current_field: Optional['MagneticField'] = None
        self._attracted_to: Set['MagneticResource'] = set()
        self._repelled_by: Set['MagneticResource'] = set()
        self._state: ResourceState = ResourceState.IDLE
        self._lock_holder: Optional['MagneticResource'] = None

    def __hash__(self) -> int:
        """Make resource hashable based on name"""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """Compare resources based on name"""
        if not isinstance(other, MagneticResource):
            return NotImplemented
        return self.name == other.name

    async def attract_to(self, other: 'MagneticResource') -> bool:
        """Attempt to create attraction to another resource"""
        if other in self._repelled_by or self in other._repelled_by:
            return False
        
        # Check lock states
        if self._state == ResourceState.LOCKED and self._lock_holder != other:
            return False
        if other._state == ResourceState.LOCKED and other._lock_holder != self:
            return False
        
        self._attracted_to.add(other)
        other._attracted_to.add(self)
        
        if self._state == ResourceState.IDLE:
            self._state = ResourceState.SHARED
        if other._state == ResourceState.IDLE:
            other._state = ResourceState.SHARED
            
        return True

    async def repel_from(self, other: 'MagneticResource') -> None:
        """Create repulsion from another resource"""
        self._repelled_by.add(other)
        other._repelled_by.add(self)
        
        # Remove any existing attractions
        self._attracted_to.discard(other)
        other._attracted_to.discard(self)
        
        # Update states
        if not self._attracted_to:
            self._state = ResourceState.IDLE
        if not other._attracted_to:
            other._state = ResourceState.IDLE

    async def enter_field(self, field: 'MagneticField') -> None:
        """Enter a magnetic field"""
        if self._current_field and self._current_field != field:
            await self.exit_field()
        self._current_field = field
        self._state = ResourceState.IDLE

    async def exit_field(self) -> None:
        """Exit current magnetic field"""
        if self._current_field:
            self._current_field = None
            self._attracted_to.clear()
            self._repelled_by.clear()
            self._state = ResourceState.IDLE
            self._lock_holder = None

    async def lock(self, holder: 'MagneticResource') -> bool:
        """Lock the resource for exclusive use"""
        if self._state == ResourceState.LOCKED:
            return False
        
        # Clear existing attractions except with holder
        for other in list(self._attracted_to):
            if other != holder:
                await self.repel_from(other)
        
        self._state = ResourceState.LOCKED
        self._lock_holder = holder
        return True

    async def unlock(self) -> None:
        """Unlock the resource"""
        self._state = ResourceState.IDLE
        self._lock_holder = None

    def __str__(self) -> str:
        return f"{self.name} (Strength: {self.strength.name}, State: {self._state.name})"

# ==================== Main Classes ====================
class MagneticField:
    """
    Context manager for managing magnetic resources and their interactions.
    
    Example:
        ```python
        async with MagneticField("research") as field:
            await field.add_resource(tool1)
            await field.add_resource(tool2)
            await field.attract(tool1, tool2)
        ```
    """
    def __init__(
        self,
        name: str,
        strength: AttractionStrength = AttractionStrength.MEDIUM,
        parent: Optional['MagneticField'] = None
    ):
        self.name = name
        self.strength = strength
        self.parent = parent
        self._resources: Dict[str, MagneticResource] = {}
        self._active = False
        self._event_handlers: Dict[Type[FieldEvent], List[Callable]] = defaultdict(list)
        self._child_fields: List['MagneticField'] = []

    async def __aenter__(self) -> 'MagneticField':
        """Enter the magnetic field context"""
        self._active = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the magnetic field context"""
        await self.cleanup()

    async def cleanup(self) -> None:
        """Clean up the magnetic field"""
        # Clean up child fields first
        for child in self._child_fields:
            await child.cleanup()
        self._child_fields.clear()
        
        # Clean up resources
        for resource in list(self._resources.values()):
            await resource.exit_field()
        self._resources.clear()
        
        self._active = False

    async def add_resource(self, resource: MagneticResource) -> None:
        """Add a resource to the field"""
        if not self._active:
            raise RuntimeError("Cannot add resources to inactive field")
        
        if resource.name in self._resources:
            raise ValueError(f"Resource {resource.name} already exists in field")
        
        self._resources[resource.name] = resource
        # Ensure field membership is set
        await resource.enter_field(self)
        self._emit_event(ResourceAddedEvent(resource))

    async def remove_resource(self, resource: MagneticResource) -> None:
        """Remove a resource from the field"""
        if resource.name in self._resources:
            del self._resources[resource.name]
            await resource.exit_field()
            self._emit_event(ResourceRemovedEvent(resource))

    async def attract(
        self,
        source: MagneticResource,
        target: MagneticResource
    ) -> bool:
        """Create attraction between two resources"""
        if not (source.name in self._resources and target.name in self._resources):
            raise ValueError("Both resources must be in the field")
        
        # Check strength compatibility
        if source.strength.value < self.strength.value or \
           target.strength.value < self.strength.value:
            return False
        
        success = await source.attract_to(target)
        if success:
            self._emit_event(AttractionEvent(source, target))
        return success

    async def repel(
        self,
        source: MagneticResource,
        target: MagneticResource
    ) -> None:
        """Create repulsion between two resources"""
        if not (source.name in self._resources and target.name in self._resources):
            raise ValueError("Both resources must be in the field")
        
        await source.repel_from(target)
        self._emit_event(RepulsionEvent(source, target))

    def create_child_field(
        self,
        name: str,
        strength: Optional[AttractionStrength] = None
    ) -> 'MagneticField':
        """Create a child field that inherits from this field"""
        child_strength = strength or self.strength
        child = MagneticField(name, child_strength, parent=self)
        child._active = True  # Activate child field immediately
        self._child_fields.append(child)
        return child

    def on_event(
        self,
        event_type: Type[FieldEvent],
        handler: Callable[[FieldEvent], None]
    ) -> None:
        """Register an event handler"""
        self._event_handlers[event_type].append(handler)

    def _emit_event(self, event: FieldEvent) -> None:
        """Emit an event to all registered handlers"""
        for handler in self._event_handlers[type(event)]:
            handler(event)
        # Propagate to parent field
        if self.parent:
            self.parent._emit_event(event)

    def get_resource(self, name: str) -> Optional[MagneticResource]:
        """Get a resource by name"""
        return self._resources.get(name)

    def list_resources(self) -> List[str]:
        """List all resources in the field"""
        return list(self._resources.keys())

    def get_attractions(
        self,
        resource: MagneticResource
    ) -> Set[MagneticResource]:
        """Get all resources attracted to the given resource"""
        if resource.name not in self._resources:
            raise ValueError(f"Resource {resource.name} not in field")
        return resource._attracted_to.copy()

    def get_repulsions(
        self,
        resource: MagneticResource
    ) -> Set[MagneticResource]:
        """Get all resources repelled by the given resource"""
        if resource.name not in self._resources:
            raise ValueError(f"Resource {resource.name} not in field")
        return resource._repelled_by.copy()

    def get_resource_state(
        self,
        resource: MagneticResource
    ) -> ResourceState:
        """Get the current state of a resource"""
        if resource.name not in self._resources:
            raise ValueError(f"Resource {resource.name} not in field")
        return resource._state

    async def lock_resource(
        self,
        resource: MagneticResource,
        holder: MagneticResource
    ) -> bool:
        """Lock a resource for exclusive use"""
        if resource.name not in self._resources:
            raise ValueError(f"Resource {resource.name} not in field")
        return await resource.lock(holder)

    async def unlock_resource(
        self,
        resource: MagneticResource
    ) -> None:
        """Unlock a resource"""
        if resource.name not in self._resources:
            raise ValueError(f"Resource {resource.name} not in field")
        await resource.unlock()

    def __str__(self) -> str:
        return f"MagneticField({self.name}, strength={self.strength.name}, resources={len(self._resources)})"
