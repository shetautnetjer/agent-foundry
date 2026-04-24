from foundry.graph.router import route_intent


def test_router_sends_trading_tasks_to_trader_and_architect():
    route = route_intent("Build a safer backtesting research workflow")

    assert "trader" in route.selected_agents
    assert "architect" in route.selected_agents


def test_router_sends_coding_tasks_to_architect_and_builder():
    route = route_intent("Implement a CLI command and add tests")

    assert "architect" in route.selected_agents
    assert "builder" in route.selected_agents


def test_router_keeps_inspection_mock_safe():
    route = route_intent("Inspect repo and suggest next safe build step")

    assert route.inspect_only is True
    assert "builder" not in route.selected_agents
