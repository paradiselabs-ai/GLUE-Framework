# src/glue/core/memory.py
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

@dataclass
class MemorySegment:
    """Represents a single memory segment"""
    content: Any
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    last_accessed: Optional[datetime] = None

class MemoryManager:
    """Manages different types of memory for models"""
    def __init__(self):
        self.short_term: Dict[str, MemorySegment] = {}
        self.long_term: Dict[str, MemorySegment] = {}
        self.working: Dict[str, MemorySegment] = {}
        self.shared: Dict[str, Dict[str, MemorySegment]] = {}
        
    def store(
        self,
        key: str,
        content: Any,
        memory_type: str = "short_term",
        duration: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store content in specified memory type"""
        expires_at = datetime.now() + duration if duration else None
        segment = MemorySegment(
            content=content,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        if memory_type == "short_term":
            self.short_term[key] = segment
        elif memory_type == "long_term":
            self.long_term[key] = segment
        elif memory_type == "working":
            self.working[key] = segment
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

    def recall(
        self,
        key: str,
        memory_type: str = "short_term"
    ) -> Optional[Any]:
        """Retrieve content from specified memory type"""
        memory_store = self._get_memory_store(memory_type)
        
        if key not in memory_store:
            return None
            
        segment = memory_store[key]
        
        # Check expiration
        if segment.expires_at and datetime.now() > segment.expires_at:
            del memory_store[key]
            return None
            
        # Update access metadata
        segment.access_count += 1
        segment.last_accessed = datetime.now()
        
        return segment.content

    def share(
        self,
        from_model: str,
        to_model: str,
        key: str,
        content: Any,
        duration: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Share memory between models"""
        if from_model not in self.shared:
            self.shared[from_model] = {}
            
        expires_at = datetime.now() + duration if duration else None
        segment = MemorySegment(
            content=content,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self.shared[from_model][key] = segment
        
        # Create reverse lookup
        if to_model not in self.shared:
            self.shared[to_model] = {}
        self.shared[to_model][f"from_{from_model}_{key}"] = segment

    def forget(self, key: str, memory_type: str = "short_term") -> None:
        """Remove content from specified memory type"""
        memory_store = self._get_memory_store(memory_type)
        if key in memory_store:
            del memory_store[key]

    def clear(self, memory_type: Optional[str] = None) -> None:
        """Clear specified or all memory types"""
        if memory_type:
            memory_store = self._get_memory_store(memory_type)
            memory_store.clear()
        else:
            self.short_term.clear()
            self.long_term.clear()
            self.working.clear()
            self.shared.clear()

    def _get_memory_store(self, memory_type: str) -> Dict[str, MemorySegment]:
        """Get the appropriate memory store"""
        if memory_type == "short_term":
            return self.short_term
        elif memory_type == "long_term":
            return self.long_term
        elif memory_type == "working":
            return self.working
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")

    def cleanup_expired(self) -> None:
        """Remove all expired memory segments"""
        now = datetime.now()
        
        for memory_store in [self.short_term, self.long_term, self.working]:
            expired_keys = [
                key for key, segment in memory_store.items()
                if segment.expires_at and now > segment.expires_at
            ]
            for key in expired_keys:
                del memory_store[key]
                
        # Clean shared memories
        for model in list(self.shared.keys()):
            expired_keys = [
                key for key, segment in self.shared[model].items()
                if segment.expires_at and now > segment.expires_at
            ]
            for key in expired_keys:
                del self.shared[model][key]