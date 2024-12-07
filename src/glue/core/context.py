# src/glue/core/context.py

"""GLUE Context Analysis System"""

import re
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum, auto

class InteractionType(Enum):
    """Types of user interactions"""
    CHAT = auto()          # Simple conversation
    RESEARCH = auto()      # Information gathering
    TASK = auto()          # Specific task execution
    UNKNOWN = auto()       # Fallback type

class ComplexityLevel(Enum):
    """Task complexity levels"""
    SIMPLE = 1        # Single-step, straightforward
    MODERATE = 2      # Multi-step, clear path
    COMPLEX = 3       # Multi-step, unclear path
    UNKNOWN = 0       # Fallback level

    def __lt__(self, other):
        if not isinstance(other, ComplexityLevel):
            return NotImplemented
        return self.value < other.value

    def __gt__(self, other):
        if not isinstance(other, ComplexityLevel):
            return NotImplemented
        return self.value > other.value

    def __le__(self, other):
        if not isinstance(other, ComplexityLevel):
            return NotImplemented
        return self.value <= other.value

    def __ge__(self, other):
        if not isinstance(other, ComplexityLevel):
            return NotImplemented
        return self.value >= other.value

@dataclass
class ContextState:
    """Represents the current context state"""
    interaction_type: InteractionType
    complexity: ComplexityLevel
    tools_required: Set[str]
    requires_research: bool
    requires_memory: bool
    requires_persistence: bool
    confidence: float  # 0.0 to 1.0

class ContextAnalyzer:
    """Analyzes user input to determine context and requirements"""
    
    # Patterns indicating research needs
    RESEARCH_PATTERNS = {
        r"(?i)research": 0.8,
        r"(?i)find (?:information|details|data) (?:about|on|for)": 0.8,
        r"(?i)look up": 0.7,
        r"(?i)search for": 0.7,
        r"(?i)tell me about": 0.6,
        r"(?i)what (?:is|are|was|were)": 0.6,
        r"(?i)how (?:does|do|did)": 0.6
    }
    
    # Patterns indicating task execution
    TASK_PATTERNS = {
        r"(?i)create(?: a)?": 0.8,
        r"(?i)generate": 0.8,
        r"(?i)make(?: a)?": 0.7,
        r"(?i)build": 0.7,
        r"(?i)execute": 0.8,
        r"(?i)run": 0.7,
        r"(?i)analyze": 0.7
    }
    
    # Patterns indicating chat
    CHAT_PATTERNS = {
        r"(?i)^(?:hi|hello|hey)(?:\s|$)": 0.9,
        r"(?i)^(?:thanks|thank you)": 0.9,
        r"(?i)how are you": 0.9,
        r"(?i)nice to": 0.8,
        r"(?i)good (?:morning|afternoon|evening)": 0.9
    }
    
    # Tool requirement patterns
    TOOL_PATTERNS = {
        "web_search": [
            r"(?i)search",
            r"(?i)look up",
            r"(?i)find (?:information|details|data)",
            r"(?i)research"
        ],
        "file_handler": [
            r"(?i)save",
            r"(?i)create (?:a )?(?:file|document)",
            r"(?i)write (?:to|a) (?:file|document)",
            r"(?i)store"
        ],
        "code_interpreter": [
            r"(?i)run",
            r"(?i)execute",
            r"(?i)analyze code",
            r"(?i)debug"
        ]
    }
    
    def __init__(self):
        """Initialize the context analyzer"""
        self.interaction_history: List[ContextState] = []
    
    def analyze(self, input_text: str, available_tools: Optional[List[str]] = None) -> ContextState:
        """
        Analyze input text to determine context and requirements
        
        Args:
            input_text: The user's input text
            available_tools: List of available tool names
            
        Returns:
            ContextState object representing the analysis results
        """
        # Determine interaction type and confidence
        interaction_type, confidence = self._determine_type(input_text)
        
        # Determine complexity
        complexity = self._assess_complexity(input_text)
        
        # Identify required tools
        tools_required = self._identify_tools(input_text, available_tools)
        
        # Analyze requirements
        requires_research = self._requires_research(input_text)
        requires_memory = self._requires_memory(input_text)
        requires_persistence = self._requires_persistence(input_text)
        
        # Create context state
        state = ContextState(
            interaction_type=interaction_type,
            complexity=complexity,
            tools_required=tools_required,
            requires_research=requires_research,
            requires_memory=requires_memory,
            requires_persistence=requires_persistence,
            confidence=confidence
        )
        
        # Update history
        self.interaction_history.append(state)
        
        return state
    
    def _determine_type(self, text: str) -> tuple[InteractionType, float]:
        """Determine the type of interaction and confidence level"""
        # Initialize confidences
        chat_confidence = 0.0
        research_confidence = 0.0
        task_confidence = 0.0
        
        # Check chat patterns first (highest priority for simple interactions)
        for pattern, conf in self.CHAT_PATTERNS.items():
            if re.search(pattern, text):
                chat_confidence = max(chat_confidence, conf)
        
        if chat_confidence > 0.7:  # High confidence threshold for chat
            return InteractionType.CHAT, chat_confidence
        
        # Check research patterns
        for pattern, conf in self.RESEARCH_PATTERNS.items():
            if re.search(pattern, text):
                research_confidence = max(research_confidence, conf)
        
        # Check task patterns
        for pattern, conf in self.TASK_PATTERNS.items():
            if re.search(pattern, text):
                task_confidence = max(task_confidence, conf)
        
        # Determine type based on highest confidence
        if research_confidence > task_confidence:
            if research_confidence > 0.5:
                return InteractionType.RESEARCH, research_confidence
        elif task_confidence > 0.5:
            return InteractionType.TASK, task_confidence
            
        # Default to UNKNOWN if no clear pattern
        return InteractionType.UNKNOWN, 0.3
    
    def _assess_complexity(self, text: str) -> ComplexityLevel:
        """Assess the complexity of the interaction"""
        # Count potential steps/requirements
        steps = len(re.findall(r"(?i)(?:and|then|after|next|finally)", text))
        
        # Count question words (indicating information needs)
        questions = len(re.findall(r"(?i)(?:what|why|how|where|when|who)", text))
        
        # Analyze sentence structure
        sentences = len(re.findall(r"[.!?]+", text)) + 1
        words = len(text.split())
        avg_sentence_length = words / sentences
        
        if steps > 2 or questions > 2 or avg_sentence_length > 20:
            return ComplexityLevel.COMPLEX
        elif steps > 0 or questions > 0 or avg_sentence_length > 15:
            return ComplexityLevel.MODERATE
        return ComplexityLevel.SIMPLE
    
    def _identify_tools(self, text: str, available_tools: Optional[List[str]] = None) -> Set[str]:
        """Identify required tools based on input text"""
        required_tools = set()
        
        # Only check available tools if provided
        tools_to_check = (set(available_tools) if available_tools else 
                         set(self.TOOL_PATTERNS.keys()))
        
        for tool in tools_to_check:
            if tool in self.TOOL_PATTERNS:
                for pattern in self.TOOL_PATTERNS[tool]:
                    if re.search(pattern, text):
                        required_tools.add(tool)
                        break
        
        return required_tools
    
    def _requires_research(self, text: str) -> bool:
        """Determine if the interaction requires research"""
        return any(re.search(pattern, text) 
                  for pattern in self.RESEARCH_PATTERNS.keys())
    
    def _requires_memory(self, text: str) -> bool:
        """Determine if the interaction requires memory of past interactions"""
        memory_patterns = [
            r"(?i)(?:like|as) (?:before|previously|last time)",
            r"(?i)(?:again|repeat)",
            r"(?i)(?:remember|recall)",
            r"(?i)(?:you|we) (?:mentioned|discussed|talked about)"
        ]
        return any(re.search(pattern, text) for pattern in memory_patterns)
    
    def _requires_persistence(self, text: str) -> bool:
        """Determine if the interaction requires persistent storage"""
        persistence_patterns = [
            r"(?i)save",
            r"(?i)store",
            r"(?i)keep",
            r"(?i)remember this",
            r"(?i)create a (?:file|document)"
        ]
        return any(re.search(pattern, text) for pattern in persistence_patterns)
    
    def get_recent_context(self, n: int = 5) -> List[ContextState]:
        """Get the n most recent context states"""
        return self.interaction_history[-n:]
    
    def clear_history(self) -> None:
        """Clear the interaction history"""
        self.interaction_history.clear()
