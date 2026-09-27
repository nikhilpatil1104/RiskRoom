import math

from fastapi.testclient import TestClient

from app.demo_data import PORTFOLIO
from app.main import app
from app.providers import LocalDataProvider
from app.services import analyze_xray, risk_metrics, run_scenarios


def test_lookthrough_conserves_portfolio_weight_and_finds_overlap():
    xray = analyze_xray(PORTFOLIO)
    assert math.isclose(sum(row["weight"] for row in xray["effective_holdings"]), 1.0, abs_tol=1e-10)
    assert xray["technology_weight"] > 0.35
    assert any(pair["left"] == "VOO" and pair["right"] == "QQQ" and pair["shared_holdings_weight"] > 0 for pair in xray["overlap_pairs"])


def test_portfolio_weights_must_sum_to_one():
    try:
        analyze_xray([{"ticker": "VOO", "weight": 0.5}])
        assert False, "Should reject under-allocated portfolio"
    except ValueError as exc:
        assert "sum to 100%" in str(exc)


def test_scenario_impact_is_deterministic_weighted_sector_sum():
    xray = analyze_xray(PORTFOLIO)
    results = run_scenarios(xray)
    ai = next(row for row in results if row["id"] == "ai-capex")
    expected = sum(row["weight"] * {"Technology": -0.30, "Communication Services": -0.16}.get(row["sector"], 0) for row in xray["effective_holdings"])
    assert math.isclose(ai["portfolio_return"], expected, abs_tol=1e-12)
    assert ai == next(row for row in run_scenarios(xray) if row["id"] == "ai-capex")


def test_demo_risk_metrics_are_reproducible_and_finite():
    a, b = risk_metrics(), risk_metrics()
    assert a == b
    assert a["observations"] == 504
    assert all(math.isfinite(a[key]) for key in ("annualized_return", "annualized_volatility", "historical_var_95", "historical_cvar_95", "max_drawdown", "correlation_to_demo_market"))
    assert a["historical_cvar_95"] >= a["historical_var_95"] > 0


def test_war_room_api_returns_five_roles_and_scenario_calculations():
    client = TestClient(app)
    response = client.post("/api/war-room/start", json={"thesis": "AI infrastructure spending remains durable over two years."})
    assert response.status_code == 200
    body = response.json()
    assert {agent["agent"] for agent in body["committee"]["agents"]} == {"Bull", "Bear", "Macro", "Risk Officer", "Red Team"}
    assert len(body["scenarios"]) >= 4
    assert body["mode"] == "DETERMINISTIC DEMO"
    assert "does not provide financial advice" in body["report"]["disclaimer"]
    stored = client.get(f"/api/committee/{body['run_id']}")
    assert stored.status_code == 200
    assert len(stored.json()["committee"]["agents"]) == 5


def test_xray_api_rejects_invalid_weights():
    client = TestClient(app)
    response = client.post("/api/xray/analyze", json={"thesis": "A sufficiently long investor thesis.", "holdings": [{"ticker": "VOO", "weight": 0.5}]})
    assert response.status_code == 422


def test_custom_scenario_shocks_are_validated_and_calculated():
    client = TestClient(app)
    payload = {"scenario_id": "custom-test", "name": "Custom tech shock", "shocks": {"Technology": -0.25}}
    response = client.post("/api/scenarios/run", json=payload)
    assert response.status_code == 200
    assert response.json()["portfolio_return"] < 0
    bad = {"scenario_id": "custom-bad", "shocks": {"Technology": -2}}
    assert client.post("/api/scenarios/run", json=bad).status_code == 422


def test_report_endpoint_returns_decision_support_sections():
    client = TestClient(app)
    response = client.post("/api/reports/generate", json={"thesis": "AI infrastructure demand supports technology shares."})
    assert response.status_code == 200
    report = response.json()
    assert "red_team_findings" in report
    assert "scenario_analysis" in report
    assert "human_decision_checklist" in report


def test_local_provider_returns_labeled_repeatable_data():
    provider = LocalDataProvider()
    holdings = provider.holdings("VOO")
    prices_a = provider.prices(["VOO"], "2025-01-01", "2025-12-31")
    prices_b = provider.prices(["VOO"], "2025-01-01", "2025-12-31")
    assert holdings and holdings[0]["source"].startswith("RiskRoom synthetic")
    assert prices_a == prices_b
    assert prices_a[0]["close"] > 0
