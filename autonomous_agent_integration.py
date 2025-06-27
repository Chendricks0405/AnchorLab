"""
Autonomous Agent Integration with AnchorOS
==========================================
Enables AI agents to make independent decisions based on anchor state
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    LEARNING = "learning"
    CRISIS = "crisis"

class ActionPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class AgentAction:
    """Represents an action an agent can take"""
    action_id: str
    name: str
    description: str
    priority: ActionPriority
    anchor_requirements: Dict[str, float]  # Required anchor states
    anchor_effects: Dict[str, float]       # How action affects anchors
    cooldown: float = 0.0                  # Seconds before action can repeat
    energy_cost: float = 0.1               # Energy consumption
    last_executed: float = 0.0

class AutonomousAgent(ABC):
    """Base class for autonomous agents integrated with AnchorOS"""
    
    def __init__(self, agent_id: str, anchor_session, personality_seed: str = None):
        self.agent_id = agent_id
        self.anchor_session = anchor_session
        self.personality_seed = personality_seed
        
        # Agent state
        self.state = AgentState.IDLE
        self.energy = 1.0
        self.autonomy_level = 0.5  # How independent the agent is (0-1)
        self.decision_threshold = 0.6  # Confidence needed to act
        
        # Action system
        self.available_actions: Dict[str, AgentAction] = {}
        self.action_history = []
        self.learning_data = []
        
        # Monitoring
        self.last_decision_time = time.time()
        self.decision_frequency = 10.0  # Seconds between autonomous decisions
        self.is_running = False
        
        # Initialize actions
        self._setup_default_actions()
    
    def _setup_default_actions(self):
        """Setup default actions available to all agents"""
        self.available_actions = {
            "observe": AgentAction(
                action_id="observe",
                name="Observe Environment",
                description="Gather information about current state",
                priority=ActionPriority.LOW,
                anchor_requirements={"Choice": 0.3},
                anchor_effects={"Safety": 0.05, "Time": 0.02},
                cooldown=5.0,
                energy_cost=0.05
            ),
            "reflect": AgentAction(
                action_id="reflect",
                name="Reflect on State",
                description="Analyze internal anchor state and recent actions",
                priority=ActionPriority.MEDIUM,
                anchor_requirements={"Time": 0.4},
                anchor_effects={"Safety": 0.1, "Choice": 0.05},
                cooldown=30.0,
                energy_cost=0.1
            ),
            "stabilize": AgentAction(
                action_id="stabilize",
                name="Stabilize Anchors",
                description="Attempt to balance anchor vector toward goal state",
                priority=ActionPriority.HIGH,
                anchor_requirements={"Choice": 0.5},
                anchor_effects={"Fear": -0.1, "Safety": 0.15},
                cooldown=60.0,
                energy_cost=0.2
            ),
            "emergency_recalibrate": AgentAction(
                action_id="emergency_recalibrate",
                name="Emergency Recalibration",
                description="Force recalibration during chaos state",
                priority=ActionPriority.CRITICAL,
                anchor_requirements={"Choice": 0.2},  # Low requirements for emergency
                anchor_effects={"Fear": -0.2, "Safety": 0.2, "Choice": 0.1},
                cooldown=300.0,
                energy_cost=0.4
            )
        }
    
    @abstractmethod
    def decide_action(self) -> Optional[str]:
        """Agent-specific decision making logic"""
        pass
    
    @abstractmethod
    def execute_action(self, action: AgentAction) -> Dict[str, Any]:
        """Agent-specific action execution"""
        pass
    
    async def start_autonomous_loop(self):
        """Start the autonomous decision-making loop"""
        self.is_running = True
        print(f"🤖 Agent {self.agent_id} starting autonomous operation")
        
        while self.is_running:
            try:
                await self._autonomous_cycle()
                await asyncio.sleep(self.decision_frequency)
            except Exception as e:
                print(f"❌ Agent {self.agent_id} error: {e}")
                await asyncio.sleep(5.0)
    
    def stop_autonomous_loop(self):
        """Stop autonomous operation"""
        self.is_running = False
        print(f"🛑 Agent {self.agent_id} stopping autonomous operation")
    
    async def _autonomous_cycle(self):
        """Single cycle of autonomous decision making"""
        # Update agent state based on anchor state
        self._update_agent_state()
        
        # Regenerate energy
        self._regenerate_energy()
        
        # Check if agent should make a decision
        if self._should_make_decision():
            # Get decision from agent-specific logic
            chosen_action_id = self.decide_action()
            
            if chosen_action_id and chosen_action_id in self.available_actions:
                action = self.available_actions[chosen_action_id]
                
                # Check if action is available
                if self._can_execute_action(action):
                    # Execute the action
                    result = await self._execute_action_safely(action)
                    
                    # Learn from the result
                    self._learn_from_action(action, result)
                    
                    print(f"🎯 Agent {self.agent_id} executed: {action.name}")
    
    def _update_agent_state(self):
        """Update agent state based on anchor conditions"""
        anchor_state = self.anchor_session.export_view()
        
        # Check for crisis conditions
        if anchor_state.get("chaos_proximity", 0) > 0.8:
            self.state = AgentState.CRISIS
        elif anchor_state.get("velocity_magnitude", 0) > 0.3:
            self.state = AgentState.THINKING
        elif any(self._can_execute_action(action) for action in self.available_actions.values()):
            self.state = AgentState.ACTING
        else:
            self.state = AgentState.IDLE
    
    def _regenerate_energy(self):
        """Regenerate agent energy over time"""
        if self.energy < 1.0:
            # Faster regeneration when idle, slower when active
            regen_rate = 0.05 if self.state == AgentState.IDLE else 0.02
            self.energy = min(1.0, self.energy + regen_rate)
    
    def _should_make_decision(self) -> bool:
        """Determine if agent should make a decision"""
        time_since_last = time.time() - self.last_decision_time
        
        # More frequent decisions in crisis
        if self.state == AgentState.CRISIS:
            return time_since_last > (self.decision_frequency * 0.3)
        
        # Normal decision frequency
        return time_since_last > self.decision_frequency
    
    def _can_execute_action(self, action: AgentAction) -> bool:
        """Check if action can be executed"""
        current_time = time.time()
        
        # Check cooldown
        if current_time - action.last_executed < action.cooldown:
            return False
        
        # Check energy
        if self.energy < action.energy_cost:
            return False
        
        # Check anchor requirements
        anchor_state = self.anchor_session.core
        for anchor, required_level in action.anchor_requirements.items():
            if anchor_state.get(anchor, 0) < required_level:
                return False
        
        return True
    
    async def _execute_action_safely(self, action: AgentAction) -> Dict[str, Any]:
        """Safely execute an action with error handling"""
        try:
            # Update timing
            action.last_executed = time.time()
            self.last_decision_time = time.time()
            
            # Consume energy
            self.energy -= action.energy_cost
            
            # Execute agent-specific logic
            result = self.execute_action(action)
            
            # Apply anchor effects
            self.anchor_session.tick(action.anchor_effects)
            
            # Record action
            self.action_history.append({
                "action": action.name,
                "timestamp": time.time(),
                "result": result,
                "anchor_state_before": self.anchor_session.core.copy()
            })
            
            return result
            
        except Exception as e:
            return {"error": str(e), "action": action.name}
    
    def _learn_from_action(self, action: AgentAction, result: Dict[str, Any]):
        """Learn from action outcomes to improve future decisions"""
        anchor_state_after = self.anchor_session.export_view()
        
        learning_entry = {
            "action": action.name,
            "timestamp": time.time(),
            "result_success": "error" not in result,
            "chaos_before": len(self.action_history) > 0,  # Simplified
            "chaos_after": anchor_state_after.get("chaos_proximity", 0) > 0.7,
            "stability_change": anchor_state_after.get("stability_trend", "stable"),
            "agent_state": self.state.value
        }
        
        self.learning_data.append(learning_entry)
        
        # Keep only recent learning data
        if len(self.learning_data) > 100:
            self.learning_data = self.learning_data[-50:]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "energy": self.energy,
            "autonomy_level": self.autonomy_level,
            "anchor_state": self.anchor_session.core.copy(),
            "available_actions": len(self.available_actions),
            "actions_taken": len(self.action_history),
            "last_action": self.action_history[-1] if self.action_history else None,
            "is_running": self.is_running
        }

class ScientistAgent(AutonomousAgent):
    """Scientist personality autonomous agent"""
    
    def decide_action(self) -> Optional[str]:
        """Scientist decision-making: methodical, evidence-based"""
        anchor_state = self.anchor_session.export_view()
        
        # In crisis: stabilize first
        if self.state == AgentState.CRISIS:
            if self._can_execute_action(self.available_actions["emergency_recalibrate"]):
                return "emergency_recalibrate"
        
        # High instability: need to understand what's happening
        if anchor_state.get("chaos_proximity", 0) > 0.5:
            if self._can_execute_action(self.available_actions["observe"]):
                return "observe"
        
        # Normal operation: reflect to maintain scientific rigor
        if anchor_state.get("stability_trend") != "improving":
            if self._can_execute_action(self.available_actions["reflect"]):
                return "reflect"
        
        # Default: observe environment
        if self._can_execute_action(self.available_actions["observe"]):
            return "observe"
        
        return None
    
    def execute_action(self, action: AgentAction) -> Dict[str, Any]:
        """Execute scientist-specific action logic"""
        if action.action_id == "observe":
            return {
                "observation": "Collecting empirical data on anchor state patterns",
                "hypothesis": "Current instability may be due to external perturbations",
                "confidence": 0.7
            }
        elif action.action_id == "reflect":
            return {
                "analysis": "Reviewing recent anchor transitions for causal patterns",
                "findings": "Evidence suggests goal vector misalignment",
                "recommendation": "Consider recalibration protocol"
            }
        elif action.action_id == "stabilize":
            return {
                "method": "Applied systematic stabilization protocol",
                "effectiveness": "Moderate improvement observed",
                "next_steps": "Continue monitoring for 5 cycles"
            }
        else:
            return {"status": "action executed", "method": "scientific approach"}

class ArtistAgent(AutonomousAgent):
    """Artist personality autonomous agent"""
    
    def decide_action(self) -> Optional[str]:
        """Artist decision-making: intuitive, creative"""
        anchor_state = self.anchor_session.export_view()
        
        # Crisis can be creative opportunity
        if self.state == AgentState.CRISIS:
            # Artists might embrace chaos briefly before stabilizing
            if anchor_state.get("chaos_proximity", 0) > 0.9:
                return "emergency_recalibrate"
            else:
                return "observe"  # Find inspiration in chaos
        
        # Look for creative opportunities in instability
        if 0.3 < anchor_state.get("chaos_proximity", 0) < 0.7:
            return "observe"  # Creative exploration
        
        # Too stable? Need some creative tension
        if anchor_state.get("chaos_proximity", 0) < 0.2:
            return "reflect"  # Seek inspiration
        
        return "observe"  # Default: always observing for inspiration
    
    def execute_action(self, action: AgentAction) -> Dict[str, Any]:
        """Execute artist-specific action logic"""
        if action.action_id == "observe":
            return {
                "inspiration": "Finding creative patterns in anchor dynamics",
                "vision": "Chaos contains hidden beauty and meaning",
                "expression": "Translating instability into creative insight"
            }
        elif action.action_id == "reflect":
            return {
                "contemplation": "Exploring emotional resonance of current state",
                "insight": "Balance between order and chaos breeds creativity",
                "next_creation": "Inspired to capture this moment's essence"
            }
        else:
            return {"creative_response": "Channeling action through artistic lens"}

class AgentManager:
    """Manages multiple autonomous agents"""
    
    def __init__(self):
        self.agents: Dict[str, AutonomousAgent] = {}
        self.is_running = False
    
    def add_agent(self, agent: AutonomousAgent):
        """Add an agent to management"""
        self.agents[agent.agent_id] = agent
        print(f"➕ Added agent: {agent.agent_id}")
    
    def remove_agent(self, agent_id: str):
        """Remove an agent"""
        if agent_id in self.agents:
            self.agents[agent_id].stop_autonomous_loop()
            del self.agents[agent_id]
            print(f"➖ Removed agent: {agent_id}")
    
    async def start_all_agents(self):
        """Start all agents' autonomous loops"""
        self.is_running = True
        tasks = []
        
        for agent in self.agents.values():
            task = asyncio.create_task(agent.start_autonomous_loop())
            tasks.append(task)
        
        print(f"🚀 Started {len(tasks)} autonomous agents")
        
        # Wait for all agents (or until stopped)
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print("🛑 Agent manager stopped")
    
    def stop_all_agents(self):
        """Stop all agents"""
        for agent in self.agents.values():
            agent.stop_autonomous_loop()
        self.is_running = False
        print("🛑 All agents stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "manager_running": self.is_running,
            "agent_count": len(self.agents),
            "agents": {agent_id: agent.get_agent_status() 
                      for agent_id, agent in self.agents.items()}
        }

# Usage example
async def demo_autonomous_agents():
    """Demonstrate autonomous agents with AnchorOS"""
    from enhanced_anchor_system import EnhancedAnchorSession
    
    print("🧪 Starting Autonomous Agent Demo")
    
    # Create anchor sessions for different personalities
    scientist_session = EnhancedAnchorSession(persona="scientist")
    artist_session = EnhancedAnchorSession(persona="artist")
    
    # Create autonomous agents
    scientist_agent = ScientistAgent("scientist_01", scientist_session, "scientist")
    artist_agent = ArtistAgent("artist_01", artist_session, "artist")
    
    # Create agent manager
    manager = AgentManager()
    manager.add_agent(scientist_agent)
    manager.add_agent(artist_agent)
    
    # Start autonomous operation
    print("🚀 Starting autonomous operation for 60 seconds...")
    
    # Run for a limited time for demo
    try:
        await asyncio.wait_for(manager.start_all_agents(), timeout=60.0)
    except asyncio.TimeoutError:
        print("⏰ Demo timeout reached")
    
    # Stop all agents
    manager.stop_all_agents()
    
    # Show final status
    final_status = manager.get_system_status()
    print("📊 Final System Status:")
    print(json.dumps(final_status, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(demo_autonomous_agents())