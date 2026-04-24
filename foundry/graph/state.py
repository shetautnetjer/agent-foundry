from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    selected_agents: list[str]
    inspect_only: bool
    reason: str
