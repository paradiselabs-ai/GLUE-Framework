# src/glue/core/conversation.py

# ==================== Imports ====================
from typing import Dict, List, Any, Optional
from datetime import datetime
from .model import Model
from .memory import MemoryManager  # NEW import

# ==================== Class Definition ====================
class ConversationManager:
    """Manages conversations between models in a CBM"""
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.active_conversation: Optional[str] = None
        self.model_states: Dict[str, Dict[str, Any]] = {}
        # NEW: Initialize memory manager
        self.memory_manager = MemoryManager()

# ==================== Core Processing ====================
    async def process(
        self, 
        models: Dict[str, Model], 
        binding_patterns: Dict[str, List], 
        user_input: str
    ) -> str:
        """Process user input through the bound models"""
        try:
            # Store user input in history and memory
            message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now()
            }
            self.history.append(message)
            
            # NEW: Store in memory
            self.memory_manager.store(
                key=f"user_input_{message['timestamp'].timestamp()}",
                content=message,
                memory_type="short_term"
            )

            # Determine conversation flow based on binding patterns
            flow = self._determine_flow(binding_patterns)
            
            # Process through model chain
            current_input = user_input
            responses = []
            
            for model_name in flow:
                if model_name in models:
                    model = models[model_name]
                    
                    # NEW: Retrieve relevant memory for model
                    context = self._get_model_context(model_name)
                    
                    # Update current input with context
                    enhanced_input = self._enhance_input_with_context(current_input, context)
                    
                    response = await model.generate(enhanced_input)
                    
                    responses.append({
                        "model": model_name,
                        "content": response,
                        "timestamp": datetime.now()
                    })
                    
                    # NEW: Store model response in memory
                    self.memory_manager.store(
                        key=f"response_{model_name}_{datetime.now().timestamp()}",
                        content=response,
                        memory_type="short_term"
                    )
                    
                    # Update for next model in chain
                    current_input = response
                    
                    # Store in history
                    self.history.append({
                        "role": "assistant",
                        "model": model_name,
                        "content": response,
                        "timestamp": datetime.now()
                    })

            # Synthesize final response
            final_response = self._synthesize_responses(responses)
            return final_response

        except Exception as e:
            # Log error and return error message
            error_msg = f"Error processing conversation: {str(e)}"
            self.history.append({
                "role": "error",
                "content": error_msg,
                "timestamp": datetime.now()
            })
            raise

# ==================== Flow Management ====================
    def _determine_flow(self, binding_patterns: Dict[str, List]) -> List[str]:
        """Determine the order of model execution based on binding patterns"""
        flow = []
        visited = set()
        
        def add_chain(model_chain):
            for item in model_chain:
                if len(item) == 2:
                    model1, model2 = item
                    binding_type = None
                elif len(item) == 3:
                    model1, model2, binding_type = item
                else:
                    raise ValueError("Invalid binding pattern")
                
                if model1 not in visited:
                    flow.append(model1)
                    visited.add(model1)
                if model2 not in visited:
                    flow.append(model2)
                    visited.add(model2)

        # Process permanent (glue) connections first
        add_chain(binding_patterns['glue'])
        
        # Then velcro (if active)
        add_chain(binding_patterns['velcro'])
        
        # Then magnetic (if in range)
        add_chain(binding_patterns['magnet'])
        
        # Temporary bindings last
        add_chain(binding_patterns['tape'])
        
        return flow

# ==================== Response Processing ====================
    def _synthesize_responses(self, responses: List[Dict[str, str]]) -> str:
        """Combine multiple model responses into a final response"""
        if not responses:
            return ""
            
        # For now, return the last response
        # TODO: Implement more sophisticated response synthesis
        return responses[-1]["content"]

# ==================== Memory Management (NEW) ====================
    def _get_model_context(self, model_name: str) -> Dict[str, Any]:
        """Retrieve relevant context for a model from memory"""
        context = {
            "recent_history": [],
            "shared_memory": {},
            "model_state": self.model_states.get(model_name, {})
        }
        
        # Get recent conversation history
        recent_messages = [
            msg for msg in self.memory_manager.short_term.values()
            if isinstance(msg.content, dict) and msg.content.get("role") in ["user", "assistant"]
        ][-5:]  # Last 5 messages
        context["recent_history"] = [msg.content for msg in recent_messages]
        
        # Get shared memories for this model
        if model_name in self.memory_manager.shared:
            context["shared_memory"] = {
                key: segment.content
                for key, segment in self.memory_manager.shared[model_name].items()
            }
        
        return context

    def _enhance_input_with_context(self, current_input: str, context: Dict[str, Any]) -> str:
        """Enhance the input with context from memory"""
        # Simple concatenation for now
        # TODO: Implement more sophisticated context integration
        history_str = "\n".join(
            f"{msg['role']}: {msg['content']}" 
            for msg in context["recent_history"]
        )
        
        return f"""Context:
{history_str}

Current Input:
{current_input}"""

# ==================== State Management ====================
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.history

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.history = []
        # NEW: Also clear short-term memory
        self.memory_manager.clear("short_term")

    def save_state(self) -> Dict[str, Any]:
        """Save conversation state"""
        return {
            "history": self.history,
            "active_conversation": self.active_conversation,
            "model_states": self.model_states
        }

    def load_state(self, state: Dict[str, Any]) -> None:
        """Load conversation state"""
        self.history = state.get("history", [])
        self.active_conversation = state.get("active_conversation")
        self.model_states = state.get("model_states", {})