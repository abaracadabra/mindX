# core/belief_system.py
import time
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union, List, Tuple
import threading
import copy
from enum import Enum
import asyncio # For example usage

# from utils.logging_config import get_logger # If needed
# logger = get_logger(__name__)

class BeliefSource(Enum):
    """Enumerates the origin of a belief."""
    PERCEPTION = "perception"
    COMMUNICATION = "communication"
    INFERENCE = "inference"
    SELF_ANALYSIS = "self_analysis"
    EXTERNAL_INPUT = "external_input"
    DEFAULT = "default_value"
    LEARNED = "learned_experience"
    DERIVED = "derived"  # <<< --- ADDED THIS MEMBER
    # You can also add others if needed, e.g.:
    # HYPOTHESIS = "hypothesis"
    # PLAN_ACTION_EFFECT = "plan_action_effect"


class Belief:
    # ... (rest of Belief class from previous correct version)
    """Represents a single belief with metadata."""
    def __init__(self, value: Any, confidence: float = 1.0, source: BeliefSource = BeliefSource.DEFAULT, timestamp: Optional[float] = None):
        self.value = value
        self.confidence = max(0.0, min(1.0, confidence)) # Clamp between 0 and 1
        self.source = source
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.last_updated = self.timestamp

    def update(self, new_value: Any, new_confidence: float, new_source: BeliefSource):
        self.value = new_value
        self.confidence = max(0.0, min(1.0, new_confidence))
        self.source = new_source
        self.last_updated = time.time()

    def __repr__(self):
        return f"Belief(value={self.value!r}, confidence={self.confidence:.2f}, source={self.source.value}, updated={self.last_updated:.0f})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source.value,
            "timestamp": self.timestamp,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Belief':
        return cls(
            value=data["value"],
            confidence=data.get("confidence", 1.0),
            source=BeliefSource(data.get("source", BeliefSource.DEFAULT.value)), # Ensure string value matches enum member value
            timestamp=data.get("timestamp"), 
        )

class BeliefSystem:
    # ... (rest of BeliefSystem class from previous correct version, no changes needed here)
    _instance = None
    _lock = threading.Lock() 

    def __new__(cls, *args, **kwargs): 
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(BeliefSystem, cls).__new__(cls)
        return cls._instance

    def __init__(self, persistence_file_path: Optional[Union[str, Path]] = None, test_mode: bool = False):
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            if test_mode and hasattr(self, 'persistence_file_path') and self.persistence_file_path != persistence_file_path:
                 pass
            else:
                return
        
        self.beliefs: Dict[str, Belief] = {}
        self._lock = threading.Lock() 

        self.persistence_file_path: Optional[Path] = None
        if persistence_file_path:
            self.persistence_file_path = Path(persistence_file_path)
            self._load_beliefs() 
        
        self._initialized = True
        if test_mode:
            self._initialized = False


    async def update_belief(self, key: str, value: Any, confidence: float = 1.0, source: BeliefSource = BeliefSource.PERCEPTION, metadata: Optional[Dict] = None, ttl_seconds: Optional[float] = None):
        with self._lock:
            if key in self.beliefs:
                self.beliefs[key].update(value, confidence, source)
            else:
                self.beliefs[key] = Belief(value, confidence, source)
            self._save_beliefs_if_path()

    async def add_belief(self, key: str, value: Any, confidence: float = 1.0, source: BeliefSource = BeliefSource.PERCEPTION, metadata: Optional[Dict] = None, ttl_seconds: Optional[float] = None):
        await self.update_belief(key, value, confidence, source, metadata, ttl_seconds)

    async def get_belief(self, key: str) -> Optional[Belief]:
        with self._lock:
            belief = self.beliefs.get(key)
            return copy.deepcopy(belief) if belief else None

    async def get_belief_value(self, key: str, default: Any = None) -> Any:
        belief = await self.get_belief(key)
        return belief.value if belief else default

    async def remove_belief(self, key: str):
        with self._lock:
            if key in self.beliefs:
                del self.beliefs[key]
                self._save_beliefs_if_path()

    async def get_all_beliefs(self) -> Dict[str, Belief]:
        with self._lock:
            return copy.deepcopy(self.beliefs)

    async def query_beliefs(self, partial_key: str = "", min_confidence: float = 0.0, source: Optional[BeliefSource] = None) -> List[Tuple[str, Belief]]:
        results = []
        with self._lock:
            for key, belief in self.beliefs.items():
                if partial_key in key and belief.confidence >= min_confidence:
                    if source is None or belief.source == source:
                        results.append((key, copy.deepcopy(belief))) 
        return results


    def _save_beliefs_if_path(self):
        if self.persistence_file_path:
            self._save_beliefs()

    def _save_beliefs(self):
        if not self.persistence_file_path:
            return
        
        data_to_save = {key: belief.to_dict() for key, belief in self.beliefs.items()}
        try:
            self.persistence_file_path.parent.mkdir(parents=True, exist_ok=True)
            with self.persistence_file_path.open("w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2, default=str)
        except Exception as e:
            # print(f"ERROR: Failed to save beliefs to {self.persistence_file_path}: {e}")
            pass

    def _load_beliefs(self):
        if not self.persistence_file_path or not self.persistence_file_path.exists():
            return

        try:
            with self.persistence_file_path.open("r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            
            self.beliefs.clear()
            for key, belief_data in loaded_data.items():
                if isinstance(belief_data, dict):
                    self.beliefs[key] = Belief.from_dict(belief_data)
                else:
                    self.beliefs[key] = Belief(value=belief_data)
        except Exception as e:
            # print(f"ERROR: Failed to load beliefs from {self.persistence_file_path}: {e}")
            pass

    @classmethod
    def reset_singleton_for_testing(cls): # pragma: no cover
        with cls._lock:
            cls._instance = None

if __name__ == "__main__": # pragma: no cover
    test_file = Path("./test_beliefs.json")
    if test_file.exists():
        test_file.unlink()

    bs1 = BeliefSystem(persistence_file_path=test_file)
    async def run_tests():
        await bs1.update_belief("weather", "sunny", 0.9, BeliefSource.PERCEPTION)
        await bs1.update_belief("agent_mood", "happy", 0.7, BeliefSource.SELF_ANALYSIS)
        await bs1.update_belief("derived_fact", "earth_is_round", 0.99, BeliefSource.DERIVED) # Test new source
        
        belief_weather = await bs1.get_belief("weather")
        if belief_weather:
            print(f"Weather: {belief_weather.value}, Confidence: {belief_weather.confidence}, Source: {belief_weather.source.value}")

        derived_belief = await bs1.get_belief("derived_fact")
        if derived_belief:
            print(f"Derived Fact: {derived_belief.value}, Source: {derived_belief.source.value}")


        print(f"All beliefs before reload: {await bs1.get_all_beliefs()}")

        BeliefSystem.reset_singleton_for_testing()
        bs2 = BeliefSystem(persistence_file_path=test_file)
        print(f"All beliefs after reload from file: {await bs2.get_all_beliefs()}")
        mood_value = await bs2.get_belief_value("agent_mood")
        print(f"Mood after reload: {mood_value}")

        if test_file.exists():
            test_file.unlink()

    asyncio.run(run_tests())
