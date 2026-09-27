import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

from .demo_data import ETF_HOLDINGS, PORTFOLIO, SCENARIOS
from .llm import generate_simulated_headlines, parse_scenario, synthesize
from .providers import AlphaVantageDataProvider, FreshSyntheticMarketProvider, GeminiProvider, SnowflakeDataProvider, TigerDataProvider
from .schemas import ScenarioRequest, ThesisRequest, WarRoomRequest
from .services import analyze_xray, committee, risk_metrics_from_prices, run_scenarios
from .tripwires import build_tripwires
from . import store

app = FastAPI(title="RiskRoom API", version="0.1.0", description="Educational investment decision support. No trade execution.")
allowed_origins = [value.strip() for value in os.getenv("RISKROOM_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if value.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _holding_dicts(values):
    return [value.model_dump() if hasattr(value, "model_dump") else value for value in values]


def _market_analysis(holdings: list[dict]) -> tuple[dict, dict, dict]:
    """Use live feeds where they work and generate fresh labeled simulation data for gaps."""
    provider = AlphaVantageDataProvider()
    if not provider.configured():
        xray = analyze_xray(holdings)
        end = date.today()
        start = end - timedelta(days=370)
        tickers = [str(holding["ticker"]).upper() for holding in holdings]
        prices = FreshSyntheticMarketProvider.prices([*tickers, "SPY"], start.isoformat(), end.isoformat())
        risk = risk_metrics_from_prices(holdings, prices, "SPY")
        risk["source"] = "Fresh simulated daily return paths generated for this submission; not observed market history"
        context = FreshSyntheticMarketProvider.context([row["ticker"] for row in xray["top_holdings"][:3]])
        return xray, risk, {"market_data_mode": "simulated", "market_data_source": "Fresh synthetic price paths generated for this submission", "portfolio_weight_source": "Seeded illustrative demo weights", "market_context": context}

    try:
        profiles = {}
        for holding in holdings:
            ticker = str(holding["ticker"]).upper()
            if ticker in ETF_HOLDINGS:
                try:
                    profiles[ticker] = {"holdings": provider.holdings(ticker), "sectors": provider.sector_allocations(ticker)}
                except RuntimeError:
                    # Keep prices and other successful feeds usable if ETF_PROFILE access is unavailable.
                    pass
        xray = analyze_xray(holdings, profiles)
        tickers = [str(holding["ticker"]).upper() for holding in holdings]
        end = date.today()
        start = end - timedelta(days=370)
        try:
            prices = provider.prices([*tickers, "SPY"], start.isoformat(), end.isoformat())
            risk = risk_metrics_from_prices(holdings, prices, "SPY")
            market_mode = "live"
            price_source = "Alpha Vantage daily closes"
        except (RuntimeError, ValueError):
            prices = FreshSyntheticMarketProvider.prices([*tickers, "SPY"], start.isoformat(), end.isoformat())
            risk = risk_metrics_from_prices(holdings, prices, "SPY")
            risk["source"] = "Fresh simulated daily return paths generated for this submission; not observed market history"
            market_mode = "simulated"
            price_source = "Fresh simulated price paths (the provider did not return a usable series for every held ticker)"
        macro = provider.economic_snapshot()
        news_tickers = [row["ticker"] for row in xray["top_holdings"] if not row["ticker"].startswith("OTHER_")][:3]
        news = provider.market_news(news_tickers)
        generated_context = FreshSyntheticMarketProvider.context(news_tickers)
        live_macro_series = {row["series"] for row in macro["observations"]}
        simulation_series = {
            "SIMULATED_TREASURY_YIELD": ("TREASURY_YIELD", "US Treasury 10-year yield"),
            "SIMULATED_FEDERAL_FUNDS_RATE": ("FEDERAL_FUNDS_RATE", "US federal funds rate"),
            "SIMULATED_INFLATION": ("CPI", "US inflation pressure"),
        }
        simulated_macro_added = False
        for reading in generated_context["macro"]["observations"]:
            provider_series, provider_label = simulation_series[reading["series"]]
            if provider_series not in live_macro_series:
                reading["series"] = provider_series
                reading["label"] = provider_label if provider_series == "CPI" else "Simulated " + provider_label
                macro["observations"].append(reading)
                simulated_macro_added = True
        macro["unavailable"] = []
        macro["status"] = "mixed" if simulated_macro_added and live_macro_series else "simulated" if simulated_macro_added else "live"
        if not news["items"]:
            news = generated_context["news"]
        macro_source = "Alpha Vantage + simulated context" if macro["status"] == "mixed" else "Alpha Vantage macro readings" if macro["status"] == "live" else "simulated macro context"
        news_source = "Alpha Vantage headlines" if news["status"] == "live" else "simulated thesis scenarios"
        return xray, risk, {"market_data_mode": market_mode, "market_data_source": f"{price_source}; {macro_source}; {news_source}", "portfolio_weight_source": "Seeded illustrative demo weights", "market_context": {"macro": macro, "news": news, "generated_at": generated_context["generated_at"]}}
    except (RuntimeError, ValueError, KeyError, TypeError):
        # Preserve the submission path even when a provider returns an unexpected payload.
        xray = analyze_xray(holdings)
        end = date.today()
        start = end - timedelta(days=370)
        tickers = [str(holding["ticker"]).upper() for holding in holdings]
        prices = FreshSyntheticMarketProvider.prices([*tickers, "SPY"], start.isoformat(), end.isoformat())
        risk = risk_metrics_from_prices(holdings, prices, "SPY")
        risk["source"] = "Fresh simulated daily return paths generated for this submission; not observed market history"
        context = FreshSyntheticMarketProvider.context([row["ticker"] for row in xray["top_holdings"][:3]])
        return xray, risk, {"market_data_mode": "simulated", "market_data_source": "Fresh simulated prices, macro context, and thesis scenarios generated for this submission", "portfolio_weight_source": "Seeded illustrative demo weights", "market_context": context}


@app.get("/api/health")
def health():
    market_live = AlphaVantageDataProvider().configured()
    return {"status": "ok", "mode": "live market data" if market_live else "demo", "providers": {"market_data": "Alpha Vantage" if market_live else "local synthetic demo", "gemini": GeminiProvider().configured(), "snowflake": SnowflakeDataProvider().configured(), "tigerdata": TigerDataProvider().configured()}, "trading_enabled": False}


@app.get("/api/portfolios/demo")
def demo_portfolio():
    xray, risk, data_status = _market_analysis(_holding_dicts(PORTFOLIO))
    return {"id": "riskroom-demo", "name": "AI Infrastructure Core", "holdings": PORTFOLIO, "xray": xray, "risk": risk, "data_status": data_status, "data_mode": data_status["market_data_mode"]}


@app.get("/api/war-room/demo")
def demo_war_room():
    """Return the full seeded analysis immediately, without an LLM call or stored run."""
    holdings = _holding_dicts(PORTFOLIO)
    xray, risks, data_status = _market_analysis(holdings)
    scenario_rows = run_scenarios(xray)
    seed_thesis = "AI infrastructure spending will keep driving technology equities higher over the next two years."
    return {
        "run_id": "DEMO-SEEDED",
        "portfolio": {"name": "AI Infrastructure Core", "holdings": holdings},
        "xray": xray,
        "committee": committee(seed_thesis, xray, data_status["market_context"]["macro"]["observations"], data_status["market_context"]["news"]["items"]),
        "risk": risks,
        "scenarios": scenario_rows,
        "ai_summary": None,
        "mode": "DETERMINISTIC DEMO",
        "data_status": data_status,
        "report": {"title": "Investment Committee Briefing", "thesis": seed_thesis, "disclaimer": "RiskRoom is an educational and research-oriented decision-support system. It does not provide financial advice, guarantee investment outcomes, or execute trades autonomously."},
        "progress": ["Portfolio X-Ray complete", "Committee arguments generated from labeled demo rules", "Scenario impacts calculated from effective exposures", "Seeded demo ready; no Gemini call made"],
    }


@app.post("/api/thesis/tripwires")
async def thesis_tripwires(req: WarRoomRequest):
    """Build editable issuer tripwires; SEC values are optional and source-labeled."""
    try:
        analyze_xray(_holding_dicts(req.holdings or PORTFOLIO))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = await build_tripwires()
    result["thesis"] = req.thesis
    thesis_text = req.thesis.lower()
    if any(word in thesis_text for word in ("ai", "technology", "tech", "capex", "cloud", "semiconductor", "chip", "infrastructure")):
        result["scope"] = "Curated large-cap technology issuer proxies for this AI/infrastructure thesis; they are not a complete industry signal."
    else:
        result["scope"] = "The available SEC signals cover large-cap technology issuers and may not match this thesis. Treat them as examples until you choose relevant evidence."
    return result


@app.post("/api/xray/analyze")
def xray_analyze(req: WarRoomRequest):
    try:
        holdings = _holding_dicts(req.holdings or PORTFOLIO)
        xray, _, data_status = _market_analysis(holdings)
        return {**xray, "data_status": data_status}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/portfolios")
def create_portfolio(req: WarRoomRequest):
    holdings = _holding_dicts(req.holdings or PORTFOLIO)
    try:
        analyze_xray(holdings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": "local-demo", "name": "Investor Portfolio", "holdings": holdings}


@app.get("/api/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    if portfolio_id not in {"demo", "riskroom-demo", "local-demo"}:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    return {"id": portfolio_id, "name": "AI Infrastructure Core", "holdings": PORTFOLIO}


@app.post("/api/thesis/analyze")
def thesis_analyze(req: WarRoomRequest):
    return committee_run(req)


@app.post("/api/committee/run")
def committee_run(req: WarRoomRequest):
    holdings = _holding_dicts(req.holdings or PORTFOLIO)
    try:
        xray, _, data_status = _market_analysis(holdings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    context = data_status["market_context"]
    result = committee(req.thesis, xray, context["macro"]["observations"], context["news"]["items"])
    store.save_committee("demo-committee-single", req.thesis, {"committee": result})
    return result


@app.get("/api/committee/{run_id}")
def committee_get(run_id: str):
    result = store.get_committee(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Committee run not found.")
    return result


@app.get("/api/scenarios")
def scenarios():
    return {"items": SCENARIOS}


@app.post("/api/scenarios/generate")
async def scenario_generate(req: ThesisRequest):
    try:
        generated = await parse_scenario(req.thesis)
    except Exception:
        generated = None
    if generated is None:
        text = req.thesis.lower()
        if "rate" in text or "interest" in text:
            shocks = {"Technology": -0.18, "Fixed Income": -0.14}
            name = "Rates shock (demo mapping)"
        elif "recession" in text:
            shocks = {"Technology": -0.25, "Consumer Discretionary": -0.30, "Financials": -0.24, "Healthcare": -0.12, "Fixed Income": 0.08}
            name = "Recession (demo mapping)"
        elif "tech" in text or "ai" in text or "capex" in text:
            shocks = {"Technology": -0.25, "Communication Services": -0.16}
            name = "Technology shock (demo mapping)"
        else:
            shocks = {}
            name = "Custom scenario (insufficient parameters)"
        return {"id": "custom-demo", "name": name, "description": req.thesis, "shocks": shocks, "assumptions": ["Rule-based fallback; provide explicit sector shocks for a quantitative run."], "mode": "deterministic_demo"}
    if not isinstance(generated, dict) or not isinstance(generated.get("shocks"), dict):
        return {"id": "custom-demo", "name": "Custom scenario (invalid model output)", "description": req.thesis, "shocks": {}, "assumptions": ["Gemini returned an invalid scenario; no shocks were applied."], "mode": "deterministic_demo"}
    return {**generated, "id": "custom-gemini", "mode": "gemini_structured_input"}


@app.post("/api/scenarios/run")
def scenario_run(req: ScenarioRequest):
    try:
        holdings = _holding_dicts(req.holdings or PORTFOLIO)
        xray, _, _ = _market_analysis(holdings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rows = run_scenarios(xray)
    row = next((item for item in rows if item["id"] == req.scenario_id), None)
    if row is None and req.shocks:
        allowed = {"Technology", "Communication Services", "Consumer Discretionary", "Financials", "Energy", "Healthcare", "Consumer Staples", "Fixed Income", "Other / unclassified"}
        if set(req.shocks) - allowed or any(not isinstance(value, (int, float)) or not -1 <= value <= 1 for value in req.shocks.values()):
            raise HTTPException(status_code=422, detail="Scenario shocks must use supported sector names and decimal returns between -1 and 1.")
        impact = sum(item["weight"] * req.shocks.get(item["sector"], 0.0) for item in xray["sector_exposure"])
        row = {"id": req.scenario_id, "name": req.name or "Custom scenario", "description": req.description or "User-defined sector shocks", "shocks": req.shocks, "portfolio_return": impact, "estimated_pnl_pct": impact * 100, "estimated_loss_per_10000": -impact * 10000, "method": "sum of effective security exposure × validated deterministic sector shock"}
    if row is None:
        raise HTTPException(status_code=404, detail="Scenario not found. Provide validated custom sector shocks to execute a generated scenario.")
    import uuid
    store.save_scenario(f"scenario-{uuid.uuid4().hex[:10]}", "riskroom-demo", row)
    return row


@app.get("/api/risk/demo")
def risk_demo():
    _, risk, data_status = _market_analysis(_holding_dicts(PORTFOLIO))
    return {**risk, "data_status": data_status}


@app.post("/api/war-room/start")
async def start_war_room(req: WarRoomRequest):
    holdings = _holding_dicts(req.holdings or PORTFOLIO)
    try:
        xray, risks, data_status = await asyncio.to_thread(_market_analysis, holdings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    import uuid
    scenario_rows = run_scenarios(xray)
    market_context = data_status["market_context"]
    tasks = [synthesize(req.thesis, risks, scenario_rows)]
    wants_generated_headlines = market_context["news"]["status"] == "simulated"
    if wants_generated_headlines:
        tasks.append(generate_simulated_headlines(req.thesis, [row["ticker"] for row in xray["top_holdings"][:3]]))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ai_summary = results[0] if isinstance(results[0], str) else None
    if wants_generated_headlines and len(results) > 1 and isinstance(results[1], list) and results[1]:
        market_context["news"]["items"] = results[1]
        market_context["news"]["source"] = "Gemini-generated hypothetical scenarios"
    result = {"run_id": f"demo-{uuid.uuid4().hex[:10]}", "portfolio": {"name": "AI Infrastructure Core", "holdings": holdings}, "xray": xray, "committee": committee(req.thesis, xray, market_context["macro"]["observations"], market_context["news"]["items"]), "risk": risks, "scenarios": scenario_rows, "ai_summary": ai_summary, "mode": "GEMINI SYNTHESIS" if ai_summary else "FRESH SIMULATION" if data_status["market_data_mode"] == "simulated" else "DETERMINISTIC RULES", "data_status": data_status, "report": {"title": "Investment Committee Briefing", "thesis": req.thesis, "disclaimer": "RiskRoom is an educational and research-oriented decision-support system. It does not provide financial advice, guarantee investment outcomes, or execute trades autonomously."}, "progress": ["Portfolio X-Ray complete", "Committee arguments generated from labeled rules and source-tagged context", "Scenario impacts calculated from effective exposures", "Gemini synthesis complete" if ai_summary else "Freshly generated market simulation attached" if data_status["market_data_mode"] == "simulated" else "Analysis complete"]}
    store.save_committee(result["run_id"], req.thesis, result)
    for scenario in scenario_rows:
        store.save_scenario(f"{result['run_id']}-{scenario['id']}", "riskroom-demo", scenario)
    return result


@app.post("/api/reports/generate")
async def report_generate(req: WarRoomRequest):
    result = await start_war_room(req)
    result["report"].update({
        "executive_summary": "The portfolio has {:.1f}% technology exposure after ETF look-through. Exposure provenance: {}. Seeded portfolio weights are illustrative; scenario results are deterministic demonstrations, not forecasts.".format(result["xray"]["technology_weight"] * 100, result["xray"]["source"]),
        "investor_thesis": req.thesis,
        "portfolio_xray": result["xray"],
        "hidden_exposures": result["xray"]["top_holdings"],
        "bull_case": next(agent for agent in result["committee"]["agents"] if agent["agent"] == "Bull"),
        "bear_case": next(agent for agent in result["committee"]["agents"] if agent["agent"] == "Bear"),
        "macro_analysis": next(agent for agent in result["committee"]["agents"] if agent["agent"] == "Macro"),
        "risk_officer_analysis": next(agent for agent in result["committee"]["agents"] if agent["agent"] == "Risk Officer"),
        "red_team_findings": next(agent for agent in result["committee"]["agents"] if agent["agent"] == "Red Team"),
        "key_assumptions": result["committee"]["agents"][-1]["assumptions"],
        "scenario_analysis": result["scenarios"],
        "quantitative_risk": result["risk"],
        "evidence_quality": result["committee"]["evidence_quality"],
        "unresolved_questions": result["committee"]["unresolved_questions"],
        "human_decision_checklist": result["committee"]["unresolved_questions"],
    })
    return result["report"]
