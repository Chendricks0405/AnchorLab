import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class MemoryNode:
    """Individual memory unit with decay and reinforcement"""
    def __init__(self, content: str, memory_type: str = "interaction", 
                 importance: float = 0.5, anchor_context: Dict = None):
        self.id = f"mem_{int(time.time() * 1000)}"
        self.content = content
        self.memory_type = memory_type  # interaction, pattern, preference, crisis
        self.importance = importance
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 1
        self.anchor_context = anchor_context or {}
        self.decay_rate = self._calculate_decay_rate()
        
    def _calculate_decay_rate(self) -> float:
        """Memory decay based on type and importance"""
        base_rates = {
            "interaction": 0.95,
            "pattern": 0.98,
            "preference": 0.99,
            "crisis": 0.999
        }
        return base_rates.get(self.memory_type, 0.95) + (self.importance * 0.05)
    
    def access(self):
        """Reinforce memory on access"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        self.importance = min(1.0, self.importance + 0.01)
    
    def get_current_strength(self) -> float:
        """Calculate current memory strength with decay"""
        days_since_access = (datetime.now() - self.last_accessed).days
        return self.importance * (self.decay_rate ** days_since_access)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "anchor_context": self.anchor_context,
            "current_strength": self.get_current_strength()
        }

class EnhancedMemorySystem:
    """Advanced memory system with persistence and intelligent retrieval"""
    
    def __init__(self, max_memories: int = 1000, cleanup_threshold: float = 0.1):
        self.max_memories = max_memories
        self.cleanup_threshold = cleanup_threshold
        self.memories: Dict[str, MemoryNode] = {}
        self.memory_clusters: Dict[str, List[str]] = {}
        
    def store_memory(self, content: str, memory_type: str = "interaction",
                    importance: float = 0.5, anchor_context: Dict = None) -> str:
        """Store new memory with automatic clustering"""
        node = MemoryNode(content, memory_type, importance, anchor_context)
        self.memories[node.id] = node
        
        # Add to cluster
        if memory_type not in self.memory_clusters:
            self.memory_clusters[memory_type] = []
        self.memory_clusters[memory_type].append(node.id)
        
        # Trigger cleanup if needed
        if len(self.memories) > self.max_memories:
            self._cleanup_weak_memories()
            
        return node.id
    
    def retrieve_memories(self, query_type: str = None, 
                         anchor_context: Dict = None,
                         limit: int = 10) -> List[Dict]:
        """Intelligent memory retrieval with context matching"""
        candidates = []
        
        for memory_id, memory in self.memories.items():
            strength = memory.get_current_strength()
            if strength < self.cleanup_threshold:
                continue
                
            score = strength
            
            # Type matching bonus
            if query_type and memory.memory_type == query_type:
                score += 0.2
                
            # Anchor context similarity bonus
            if anchor_context and memory.anchor_context:
                similarity = self._calculate_anchor_similarity(
                    anchor_context, memory.anchor_context
                )
                score += similarity * 0.3
                
            candidates.append((score, memory))
        
        # Sort by relevance and return top results
        candidates.sort(key=lambda x: x[0], reverse=True)
        results = []
        
        for score, memory in candidates[:limit]:
            memory.access()  # Reinforce accessed memories
            result = memory.to_dict()
            result["relevance_score"] = score
            results.append(result)
            
        return results
    
    def _calculate_anchor_similarity(self, context1: Dict, context2: Dict) -> float:
        """Calculate similarity between anchor contexts"""
        if not context1 or not context2:
            return 0.0
            
        common_keys = set(context1.keys()) & set(context2.keys())
        if not common_keys:
            return 0.0
            
        similarities = []
        for key in common_keys:
            diff = abs(context1[key] - context2[key])
            similarity = 1.0 - diff  # Assuming 0-1 values
            similarities.append(similarity)
            
        return sum(similarities) / len(similarities)
    
    def _cleanup_weak_memories(self):
        """Remove memories below threshold strength"""
        to_remove = []
        for memory_id, memory in self.memories.items():
            if memory.get_current_strength() < self.cleanup_threshold:
                to_remove.append(memory_id)
        
        for memory_id in to_remove:
            memory = self.memories[memory_id]
            # Remove from clusters
            if memory.memory_type in self.memory_clusters:
                if memory_id in self.memory_clusters[memory.memory_type]:
                    self.memory_clusters[memory.memory_type].remove(memory_id)
            # Remove from main storage
            del self.memories[memory_id]
    
    def get_memory_stats(self) -> Dict:
        """Get memory system statistics"""
        total_memories = len(self.memories)
        type_counts = {}
        avg_strength = 0
        
        for memory in self.memories.values():
            memory_type = memory.memory_type
            type_counts[memory_type] = type_counts.get(memory_type, 0) + 1
            avg_strength += memory.get_current_strength()
        
        if total_memories > 0:
            avg_strength /= total_memories
            
        return {
            "total_memories": total_memories,
            "memory_types": type_counts,
            "average_strength": avg_strength,
            "cluster_info": {k: len(v) for k, v in self.memory_clusters.items()}
        }
    
    def save_to_file(self, filepath: str):
        """Persist memory system to file"""
        data = {
            "memories": {mid: mem.to_dict() for mid, mem in self.memories.items()},
            "clusters": self.memory_clusters,
            "config": {
                "max_memories": self.max_memories,
                "cleanup_threshold": self.cleanup_threshold
            }
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Load memory system from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Restore memories
            self.memories = {}
            for mid, mem_data in data.get("memories", {}).items():
                node = MemoryNode(
                    content=mem_data["content"],
                    memory_type=mem_data["memory_type"],
                    importance=mem_data["importance"],
                    anchor_context=mem_data["anchor_context"]
                )
                node.id = mem_data["id"]
                node.created_at = datetime.fromisoformat(mem_data["created_at"])
                node.last_accessed = datetime.fromisoformat(mem_data["last_accessed"])
                node.access_count = mem_data["access_count"]
                self.memories[mid] = node
            
            # Restore clusters and config
            self.memory_clusters = data.get("clusters", {})
            config = data.get("config", {})
            self.max_memories = config.get("max_memories", self.max_memories)
            self.cleanup_threshold = config.get("cleanup_threshold", self.cleanup_threshold)
            
        except FileNotFoundError:
            pass  # Start fresh if no file exists

# Integration with AnchorSession
class AnchorSessionWithMemory:
    """Enhanced AnchorSession with memory system integration"""
    
    def __init__(self, persona: str = None, memory_file: str = None):
        # Initialize base anchor system (your existing code)
        self.core = {"Fear": 0.5, "Safety": 0.5, "Time": 0.5, "Choice": 0.5}
        self.goal_vector = {"Fear": 0.3, "Safety": 0.7, "Time": 0.6, "Choice": 0.8}
        self.memory_file = memory_file or f"memories_{persona or 'default'}.json"
        
        # Initialize enhanced memory system
        self.memory_system = EnhancedMemorySystem()
        if self.memory_file:
            self.memory_system.load_from_file(self.memory_file)
    
    def process_input(self, user_input: str, response: str) -> Dict:
        """Process interaction and store in memory"""
        # Store interaction memory with current anchor context
        memory_id = self.memory_system.store_memory(
            content=f"User: {user_input}\nResponse: {response}",
            memory_type="interaction",
            importance=0.5,
            anchor_context=self.core.copy()
        )
        
        # Check for pattern recognition
        self._detect_and_store_patterns(user_input, response)
        
        # Save to file
        if self.memory_file:
            self.memory_system.save_to_file(self.memory_file)
        
        return {"memory_id": memory_id, "anchor_state": self.core.copy()}
    
    def _detect_and_store_patterns(self, user_input: str, response: str):
        """Detect patterns and store as higher-importance memories"""
        # Simple pattern detection - can be enhanced
        crisis_keywords = ["crisis", "emergency", "urgent", "help", "scared"]
        preference_keywords = ["like", "prefer", "want", "enjoy", "love"]
        
        importance = 0.5
        memory_type = "interaction"
        
        if any(word in user_input.lower() for word in crisis_keywords):
            memory_type = "crisis"
            importance = 0.9
        elif any(word in user_input.lower() for word in preference_keywords):
            memory_type = "preference"
            importance = 0.7
        
        if memory_type != "interaction":
            self.memory_system.store_memory(
                content=f"Pattern: {memory_type} - {user_input}",
                memory_type=memory_type,
                importance=importance,
                anchor_context=self.core.copy()
            )
    
    def get_relevant_context(self, current_input: str, limit: int = 5) -> List[Dict]:
        """Get relevant memories for current context"""
        # Simple context matching - can be enhanced with NLP
        if "crisis" in current_input.lower():
            return self.memory_system.retrieve_memories("crisis", self.core, limit)
        elif any(word in current_input.lower() for word in ["remember", "recall", "before"]):
            return self.memory_system.retrieve_memories(anchor_context=self.core, limit=limit)
        else:
            return self.memory_system.retrieve_memories("interaction", self.core, limit)
