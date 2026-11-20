"""Agent definition in the CrewAI style: explicit role, goal and backstory, one responsibility each."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    goal: str
    backstory: str


def clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
