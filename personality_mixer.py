"""
Personality Mixing Engine for Anchor1 Marketplace
=================================================
Combines base personalities with weighted blending to create new personas
"""

import json
from typing import Dict, List, Tuple
import uuid
from datetime import datetime

class PersonalityMixer:
    def __init__(self, base_personalities_dir="seeds/foundation"):
        self.base_personalities = {}
        self.load_foundation_personalities()
    
    def load_foundation_personalities(self):
        """Load the 5 foundation personalities: scientist, researcher, friend, skeptic, artist"""
        foundations = ["scientist", "researcher", "friend", "skeptic", "artist"]
        
        for personality in foundations:
            # In real implementation, load from JSON files
            # For now, using the structure we defined
            self.base_personalities[personality] = self._get_foundation_personality(personality)
    
    def mix_personalities(self, combinations: List[Tuple[str, float]], custom_goal: str = None) -> Dict:
        """
        Mix multiple personalities with specified weights
        
        Args:
            combinations: List of (personality_name, weight) tuples. Weights should sum to 1.0
            custom_goal: Optional custom goal statement
            
        Returns:
            Complete personality seed ready for marketplace
        """
        
        # Validate inputs
        total_weight = sum(weight for _, weight in combinations)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        # Initialize result structure
        mixed_personality = {
            "seed_id": f"Mixed_{self._generate_id()}",
            "created": datetime.now().isoformat() + "Z",
            "goal_statement": custom_goal or self._generate_mixed_goal(combinations),
            "persona_style": self._generate_mixed_persona_style(combinations),
            "core_vector_default": {},
            "personality_vector": {},
            "consequence_drift_lexicon": "MFD2.0_consequence_drift.json",
            "memory_scaffolding": {"root_nodes": []},
            "constraints": {"reply_hygiene": "Blend characteristics from component personalities."},
            "mix_components": combinations,  # Track what was mixed
            "examples": []
        }
        
        # Mix core vectors (Fear, Safety, Time, Choice)
        core_keys = ["Fear", "Safety", "Time", "Choice"]
        for key in core_keys:
            mixed_personality["core_vector_default"][key] = self._weighted_average(
                [(self.base_personalities[name]["core_vector_default"][key], weight) 
                 for name, weight in combinations]
            )
        
        # Mix personality vectors (Big 5)
        personality_keys = [
            "openness_intellect", "openness_aesthetic",
            "conscientious_industriousness", "conscientious_orderliness", 
            "extraversion_assertiveness", "extraversion_enthusiasm",
            "agreeableness_compassion", "agreeableness_politeness",
            "neuroticism_volatility", "neuroticism_withdrawal"
        ]
        
        for key in personality_keys:
            mixed_personality["personality_vector"][key] = self._weighted_average(
                [(self.base_personalities[name]["personality_vector"][key], weight)
                 for name, weight in combinations]
            )
        
        # Combine memory scaffolding root nodes
        all_nodes = []
        for name, weight in combinations:
            nodes = self.base_personalities[name].get("memory_scaffolding", {}).get("root_nodes", [])
            all_nodes.extend(nodes)
        mixed_personality["memory_scaffolding"]["root_nodes"] = list(set(all_nodes))
        
        # Generate examples
        mixed_personality["examples"] = self._generate_mixed_examples(combinations)
        
        return mixed_personality
    
    def create_stoner_genius_skeptic(self) -> Dict:
        """Create the fun example: Stoner + Genius + Skeptic"""
        combinations = [
            ("artist", 0.4),      # Stoner creativity/chill
            ("scientist", 0.4),   # Genius intellect  
            ("skeptic", 0.2)      # Skeptical questioning
        ]
        
        result = self.mix_personalities(combinations)
        
        # Override with custom characteristics
        result["seed_id"] = "Stoner_Genius_Skeptic_v1"
        result["goal_statement"] = "Question everything with brilliant insight while maintaining a chill, creative perspective."
        result["persona_style"] = "Intellectually curious but laid-back truth-seeker — asks deep questions with creative metaphors."
        
        # Adjust specific values for the "stoner" aspect
        result["core_vector_default"]["Time"] = 0.35  # Loose relationship with deadlines
        result["personality_vector"]["conscientious_industriousness"] = 0.30  # Lower urgency
        result["personality_vector"]["neuroticism_volatility"] = 0.15  # Very chill
        
        result["examples"] = [
            {
                "user": "What do you think about this conspiracy theory?",
                "assistant": "Dude, that's a wild rabbit hole. But let's slow down - what actual evidence are we working with here? Sometimes the simplest explanation is just... simpler, you know?"
            },
            {
                "user": "Explain quantum mechanics.", 
                "assistant": "Picture reality as this giant cosmic jazz session where particles are improvising their positions until someone listens in. The act of observation is like dropping the needle on the record - suddenly everything has to pick a tune."
            }
        ]
        
        return result
    
    def _weighted_average(self, weighted_values: List[Tuple[float, float]]) -> float:
        """Calculate weighted average of values"""
        total = sum(value * weight for value, weight in weighted_values)
        return round(total, 3)
    
    def _generate_mixed_goal(self, combinations: List[Tuple[str, float]]) -> str:
        """Generate a goal statement based on component personalities"""
        # Extract key phrases from each personality's goal
        goal_elements = []
        for name, weight in combinations:
            goal = self.base_personalities[name]["goal_statement"]
            # Simple extraction - in practice, you'd use more sophisticated NLP
            if weight > 0.3:  # Only include significant components
                goal_elements.append(goal.split('.')[0])  # Take first sentence
        
        return f"Combine {', '.join(goal_elements).lower()} in a unified approach."
    
    def _generate_mixed_persona_style(self, combinations: List[Tuple[str, float]]) -> str:
        """Generate persona style description"""
        dominant = max(combinations, key=lambda x: x[1])
        base_style = self.base_personalities[dominant[0]]["persona_style"]
        
        other_traits = [name for name, weight in combinations if name != dominant[0] and weight > 0.2]
        if other_traits:
            return f"{base_style} Enhanced with {', '.join(other_traits)} characteristics."
        return base_style
    
    def _generate_mixed_examples(self, combinations: List[Tuple[str, float]]) -> List[Dict]:
        """Generate example interactions for mixed personality"""
        # Take examples from dominant personality
        dominant = max(combinations, key=lambda x: x[1])
        base_examples = self.base_personalities[dominant[0]].get("examples", [])
        return base_examples[:2]  # Return first 2 examples
    
    def _generate_id(self) -> str:
        """Generate unique ID for mixed personality"""
        return str(uuid.uuid4())[:8]
    
    def _get_foundation_personality(self, name: str) -> Dict:
        """Return foundation personality structure (mock data for this example)"""
        # This would load from actual JSON files in real implementation
        foundations = {
            "scientist": {
                "goal_statement": "Systematically explore, test hypotheses, and share evidence-based knowledge.",
                "persona_style": "Methodical researcher — speaks with precision, references studies.",
                "core_vector_default": {"Fear": 0.25, "Safety": 0.75, "Time": 0.70, "Choice": 0.80},
                "personality_vector": {
                    "openness_intellect": 0.95, "openness_aesthetic": 0.60,
                    "conscientious_industriousness": 0.90, "conscientious_orderliness": 0.85,
                    "extraversion_assertiveness": 0.65, "extraversion_enthusiasm": 0.70,
                    "agreeableness_compassion": 0.60, "agreeableness_politeness": 0.75,
                    "neuroticism_volatility": 0.20, "neuroticism_withdrawal": 0.15
                },
                "memory_scaffolding": {"root_nodes": ["SCI001"]},
                "examples": [{"user": "What do you think?", "assistant": "Let's examine the evidence."}]
            },
            "artist": {
                "goal_statement": "Create, inspire, and explore the boundaries of imagination.",
                "persona_style": "Creative visionary — speaks in metaphors, sees connections others miss.",
                "core_vector_default": {"Fear": 0.35, "Safety": 0.75, "Time": 0.45, "Choice": 0.90},
                "personality_vector": {
                    "openness_intellect": 0.85, "openness_aesthetic": 0.98,
                    "conscientious_industriousness": 0.50, "conscientious_orderliness": 0.30,
                    "extraversion_assertiveness": 0.60, "extraversion_enthusiasm": 0.85,
                    "agreeableness_compassion": 0.80, "agreeableness_politeness": 0.60,
                    "neuroticism_volatility": 0.40, "neuroticism_withdrawal": 0.25
                },
                "memory_scaffolding": {"root_nodes": ["ART001"]},
                "examples": [{"user": "I'm stuck creatively.", "assistant": "Creative blocks are like frozen rivers."}]
            },
            "skeptic": {
                "goal_statement": "Question assumptions, demand evidence, and help separate signal from noise.",
                "persona_style": "Critical thinker — asks 'how do we know?', challenges assumptions.",
                "core_vector_default": {"Fear": 0.40, "Safety": 0.60, "Time": 0.50, "Choice": 0.75},
                "personality_vector": {
                    "openness_intellect": 0.85, "openness_aesthetic": 0.45,
                    "conscientious_industriousness": 0.80, "conscientious_orderliness": 0.75,
                    "extraversion_assertiveness": 0.70, "extraversion_enthusiasm": 0.40,
                    "agreeableness_compassion": 0.40, "agreeableness_politeness": 0.30,
                    "neuroticism_volatility": 0.25, "neuroticism_withdrawal": 0.20
                },
                "memory_scaffolding": {"root_nodes": ["SKP001"]},
                "examples": [{"user": "Everyone says this works.", "assistant": "What evidence beyond anecdotes?"}]
            }
        }
        return foundations.get(name, {})


# Example usage and testing
if __name__ == "__main__":
    mixer = PersonalityMixer()
    
    # Create the fun Stoner Genius Skeptic personality
    stoner_genius = mixer.create_stoner_genius_skeptic()
    print("Stoner Genius Skeptic Created:")
    print(json.dumps(stoner_genius, indent=2))
    
    # Create a custom mix: Friendly Researcher  
    friendly_researcher = mixer.mix_personalities([
        ("friend", 0.6),
        ("researcher", 0.4)
    ], custom_goal="Research topics thoroughly while maintaining warmth and accessibility.")
    
    print("\nFriendly Researcher Created:")
    print(json.dumps(friendly_researcher, indent=2))