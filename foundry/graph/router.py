from __future__ import annotations

from foundry.graph.state import RouteDecision


TRADING_TERMS = {
    "backtest",
    "backtesting",
    "trading",
    "trade",
    "trader",
    "strategy",
    "slippage",
    "pnl",
    "risk",
}
CODING_TERMS = {"implement", "code", "fix", "add", "build", "cli", "test"}
INSPECT_TERMS = {"inspect", "phase report", "suggest", "diagnose", "review"}


def route_intent(raw_text: str) -> RouteDecision:
    lowered = raw_text.lower()
    selected = ["orchestra"]
    inspect_only = any(term in lowered for term in INSPECT_TERMS)

    if any(term in lowered for term in TRADING_TERMS):
        selected.extend(["trader", "architect"])
    elif any(term in lowered for term in CODING_TERMS):
        selected.extend(["architect", "builder"])
    else:
        selected.append("architect")

    if inspect_only:
        selected = [agent for agent in selected if agent != "builder"]
        if "architect" not in selected:
            selected.append("architect")
        selected.append("writer")
        reason = "Inspect-only request routed without Builder."
    else:
        selected.extend(["tester", "risk", "writer"])
        reason = "Implementation-shaped request routed through Builder, Tester, Risk, and Writer."

    deduped = list(dict.fromkeys(selected))
    return RouteDecision(selected_agents=deduped, inspect_only=inspect_only, reason=reason)
