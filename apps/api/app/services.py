from __future__ import annotations

import math
from collections import defaultdict

from .demo_data import ETF_HOLDINGS, SCENARIOS


def _normalize_sector(value: str) -> str:
    aliases = {
        "information technology": "Technology",
        "technology": "Technology",
        "consumer cyclical": "Consumer Discretionary",
        "consumer discretionary": "Consumer Discretionary",
        "consumer defensive": "Consumer Staples",
        "consumer staples": "Consumer Staples",
        "financial services": "Financials",
        "financials": "Financials",
        "communication services": "Communication Services",
        "healthcare": "Healthcare",
        "health care": "Healthcare",
        "fixed income": "Fixed Income",
        "other": "Other / unclassified",
    }
    return aliases.get(value.strip().lower(), value.strip() or "Other / unclassified")


def analyze_xray(holdings: list[dict], etf_profiles: dict[str, dict] | None = None) -> dict:
    total = sum(float(h["weight"]) for h in holdings)
    if not math.isclose(total, 1.0, abs_tol=1e-4):
        raise ValueError("Portfolio weights must sum to 100%.")
    issuer: dict[str, float] = defaultdict(float)
    sector: dict[str, float] = defaultdict(float)
    paths: dict[str, list[dict]] = defaultdict(list)
    security_sector: dict[str, str] = {}
    by_fund: dict[str, dict[str, float]] = {}
    live_sector: dict[str, float] = defaultdict(float)
    live_symbols: set[str] = set()
    fallback_symbols: set[str] = set()
    for h in holdings:
        ticker, weight = h["ticker"].upper(), float(h["weight"])
        profile = (etf_profiles or {}).get(ticker)
        if profile:
            components = [
                (str(row["ticker"]).upper(), float(row["weight"]) * 100, _normalize_sector(row.get("sector", "Other / unclassified")))
                for row in profile.get("holdings", [])
            ]
            live_symbols.add(ticker)
        else:
            components = ETF_HOLDINGS.get(ticker)
            if components is not None:
                fallback_symbols.add(ticker)
        if components is None:
            components = [(ticker, 100.0, "Unclassified")]
        fund_map: dict[str, float] = defaultdict(float)
        for symbol, constituent_pct, industry in components:
            industry = _normalize_sector(industry)
            effective = weight * constituent_pct / 100
            issuer[symbol] += effective
            sector[industry] += effective
            security_sector[symbol] = industry
            paths[symbol].append({"etf": ticker, "weight": effective})
            fund_map[symbol] += constituent_pct / 100
        profile_sectors = profile.get("sectors", []) if profile else []
        if profile_sectors:
            profile_sector_total = sum(float(row["weight"]) for row in profile_sectors)
            for row in profile_sectors:
                live_sector[_normalize_sector(row["sector"])] += weight * float(row["weight"])
            if profile_sector_total < 1.0:
                live_sector["Other / unclassified"] += weight * (1.0 - profile_sector_total)
        else:
            for symbol, fraction in fund_map.items():
                live_sector[security_sector[symbol]] += weight * fraction
        residual = max(0.0, 1.0 - sum(fund_map.values()))
        if residual:
            symbol = f"OTHER_{ticker}"
            issuer[symbol] += weight * residual
            security_sector[symbol] = "Other / unclassified"
            paths[symbol].append({"etf": ticker, "weight": weight * residual})
            fund_map[symbol] = residual
            if not profile_sectors:
                live_sector["Other / unclassified"] += weight * residual
        by_fund[ticker] = fund_map
    sector.update(live_sector)
    top = sorted(issuer.items(), key=lambda x: x[1], reverse=True)
    overlap = []
    funds = list(by_fund)
    for i, left in enumerate(funds):
        for right in funds[i + 1:]:
            shared = sum(min(a, by_fund[right].get(symbol, 0.0)) for symbol, a in by_fund[left].items())
            overlap.append({"left": left, "right": right, "shared_holdings_weight": shared})
    return {
        "total_weight": total,
        "effective_holdings": [{"ticker": k, "weight": v, "sector": security_sector[k], "sources": paths[k]} for k, v in top],
        "sector_exposure": [{"sector": k, "weight": v} for k, v in sorted(sector.items(), key=lambda x: x[1], reverse=True)],
        "top_holdings": [{"ticker": k, "weight": v} for k, v in top[:8]],
        "overlap_pairs": overlap,
        "technology_weight": sector.get("Technology", 0.0),
        "concentration_top5": sum(v for _, v in top[:5]),
        "source": (("Alpha Vantage ETF_PROFILE fund constituents and sector weights for " + ", ".join(sorted(live_symbols))) if live_symbols else "") + (("; RiskRoom synthetic demo constituents used for " + ", ".join(sorted(fallback_symbols))) if fallback_symbols else ("RiskRoom synthetic demo ETF holdings; illustrative snapshot dated 2026-09-01" if not live_symbols else "")) + "; portfolio weights remain the illustrative seeded weights",
    }


def risk_metrics(effective_holdings: list[dict] | None = None) -> dict:
    if not effective_holdings:
        from .demo_data import PORTFOLIO
        effective_holdings = analyze_xray(PORTFOLIO)["effective_holdings"]
    sector_scale = {"Technology": 1.25, "Communication Services": 1.15, "Consumer Discretionary": 1.10, "Financials": 0.95, "Energy": 1.0, "Healthcare": 0.75, "Consumer Staples": 0.65, "Fixed Income": 0.40, "Other / unclassified": 0.9, "Unclassified": 0.9}
    returns = []
    market_returns = []
    for day in range(504):
        market = 0.00020 + 0.0038 * math.sin(day * 0.047)
        market_returns.append(market)
        portfolio_day = 0.0
        for holding in effective_holdings:
            ticker, sector = holding["ticker"], holding["sector"]
            phase = sum(ord(ch) for ch in ticker) * 0.017
            scale = sector_scale.get(sector, 0.9)
            asset_return = market + 0.0020 * scale * math.sin(day * 0.083 + (phase % 3.0)) + 0.0045 * scale * math.sin(day * (0.19 + (phase % 0.11)) + phase)
            portfolio_day += holding["weight"] * asset_return
        returns.append(portfolio_day)
    return _summarize_returns(returns, market_returns, "Synthetic deterministic security and sector returns; not a forecast", "DEMO MARKET")


def risk_metrics_from_prices(portfolio_holdings: list[dict], prices: list[dict], benchmark_ticker: str = "SPY") -> dict:
    """Compute portfolio history from aligned live closes for the held tickers."""
    series: dict[str, dict[str, float]] = defaultdict(dict)
    for row in prices:
        try:
            close = float(row["close"])
        except (KeyError, TypeError, ValueError):
            continue
        if close > 0:
            series[str(row["ticker"]).upper()][str(row["observed_at"])[:10]] = close
    tickers = [str(row["ticker"]).upper() for row in portfolio_holdings]
    missing = [ticker for ticker in [*tickers, benchmark_ticker] if ticker not in series]
    if missing:
        raise ValueError("Live price history is missing for: " + ", ".join(dict.fromkeys(missing)))
    dates = sorted(set.intersection(*(set(series[ticker]) for ticker in [*tickers, benchmark_ticker])))
    if len(dates) < 21:
        raise ValueError(f"Only {max(0, len(dates) - 1)} aligned daily observations were returned; at least 20 are required for live risk metrics.")
    portfolio_returns = []
    market_returns = []
    for previous, current in zip(dates, dates[1:]):
        portfolio_returns.append(sum(float(row["weight"]) * (series[str(row["ticker"]).upper()][current] / series[str(row["ticker"]).upper()][previous] - 1) for row in portfolio_holdings))
        market_returns.append(series[benchmark_ticker][current] / series[benchmark_ticker][previous] - 1)
    source = f"Alpha Vantage daily unadjusted closes for {', '.join(dict.fromkeys([*tickers, benchmark_ticker]))}; aligned observed sessions, excludes dividends"
    result = _summarize_returns(portfolio_returns, market_returns, source, benchmark_ticker)
    result["latest_observation"] = dates[-1]
    return result


def _summarize_returns(returns: list[float], market_returns: list[float], source: str, benchmark_ticker: str) -> dict:
    ordered = sorted(returns)
    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    vol = math.sqrt(variance * 252)
    tail = ordered[: max(1, math.ceil(n * 0.05))]
    wealth, peak, max_dd = 1.0, 1.0, 0.0
    max_dd_day, max_dd_peak = 0, 1.0
    max_dd_recovery = None
    for day, r in enumerate(returns):
        wealth *= 1 + r
        peak = max(peak, wealth)
        drawdown = wealth / peak - 1
        if drawdown < max_dd:
            max_dd = drawdown
            max_dd_day, max_dd_peak = day, peak
            max_dd_recovery = None
        elif max_dd < 0 and day > max_dd_day and wealth >= max_dd_peak and max_dd_recovery is None:
            max_dd_recovery = day - max_dd_day
    annual_growth = math.prod(1 + r for r in returns) ** (252 / n) - 1
    market_mean = sum(market_returns) / n
    market_var = sum((r - market_mean) ** 2 for r in market_returns) / (n - 1)
    covariance = sum((a - mean) * (b - market_mean) for a, b in zip(returns, market_returns)) / (n - 1)
    correlation = covariance / math.sqrt(variance * market_var) if variance > 0 and market_var > 0 else 0.0
    return {"annualized_return": annual_growth, "annualized_volatility": vol, "historical_var_95": -ordered[math.floor(n * 0.05)], "historical_cvar_95": -sum(tail) / len(tail), "max_drawdown": max_dd, "max_drawdown_recovery_days": max_dd_recovery, "correlation_to_demo_market": correlation, "correlation_to_benchmark": correlation, "benchmark_ticker": benchmark_ticker, "observations": n, "source": source}


def run_scenarios(xray: dict) -> list[dict]:
    impacts = []
    for scenario in SCENARIOS:
        loss = sum(row["weight"] * scenario["shocks"].get(row["sector"], 0.0) for row in xray["sector_exposure"])
        affected = [{"ticker": row["ticker"], "sector": row["sector"], "effective_weight": row["weight"], "shock": scenario["shocks"][row["sector"]], "portfolio_contribution": row["weight"] * scenario["shocks"][row["sector"]]} for row in xray["effective_holdings"] if row["sector"] in scenario["shocks"]]
        impacts.append({**scenario, "portfolio_return": loss, "estimated_pnl_pct": loss * 100, "estimated_loss_per_10000": -loss * 10000, "affected_sectors": list(scenario["shocks"]), "affected_securities": affected, "method": "sum of effective security exposure × deterministic sector shock"})
    return impacts


def committee(thesis: str, xray: dict, economic_observations: list[dict] | None = None, market_news: list[dict] | None = None) -> dict:
    high_tech = xray["technology_weight"] >= 0.35
    assumptions = [
        "Hyperscaler capital spending converts into durable revenue and earnings.",
        "Current valuation multiples remain supportable as growth compounds.",
        "The portfolio's overlapping funds do not create more concentration than intended.",
    ]
    macro_evidence = [
        "{}: {} = {}{} (period {}).".format("Simulated reading" if item.get("source") == "RiskRoom simulation" else "Observed " + item.get("source", "provider") + " data", item["label"], item["value"], item["unit"], item["observed_at"])
        for item in (economic_observations or [])
    ]
    if not macro_evidence:
        macro_evidence = ["No external macro series was attached to this run; the +200 bps rate shock is a hypothetical assumption."]
    red_team_evidence = [
        "{}: {} ({}, {}).".format("Hypothetical scenario" if "scenario" in item.get("source", "").lower() or item.get("url") == "" else "Retrieved headline", item["title"], item["source"], item["published_at"] or "date unavailable")
        for item in (market_news or [])[:2]
    ] or ["No market headlines were attached to this run."]
    return {
        "mode": "deterministic_demo",
        "status": "Completed using deterministic rules; live context is attached when available.",
        "thesis": thesis,
        "agents": [
            {"agent": "Bull", "claim": "The thesis could benefit if infrastructure investment drives sustained earnings growth across the value chain.", "evidence": ["Portfolio look-through shows technology exposure of {:.1f}%".format(xray["technology_weight"] * 100)], "assumptions": [assumptions[0]], "risk_level": "Moderate", "confidence": None},
            {"agent": "Bear", "claim": "Investment can outrun monetization; a spending slowdown could compress growth expectations and valuation multiples together.", "evidence": ["Scenario model includes a deterministic AI capex slowdown shock."], "assumptions": [assumptions[0], assumptions[1]], "risk_level": "High", "confidence": None},
            {"agent": "Macro", "claim": "Higher discount rates can pressure long-duration growth assets while raising bond duration risk.", "evidence": macro_evidence, "assumptions": ["Financing costs and discount rates remain material to valuations. The +200 bps stress remains hypothetical."], "risk_level": "Moderate", "confidence": None},
            {"agent": "Risk Officer", "claim": "Look-through concentration is more informative than the number of ETF tickers held.", "evidence": ["Five largest underlying exposures sum to {:.1f}% of portfolio value.".format(xray["concentration_top5"] * 100)], "assumptions": [assumptions[2]], "risk_level": "High" if high_tech else "Moderate", "confidence": None},
            {"agent": "Red Team", "claim": "What observable evidence would falsify the link between AI capex growth and durable shareholder returns?", "evidence": red_team_evidence, "assumptions": assumptions, "risk_level": "High", "confidence": None},
        ],
        "supporting_arguments": ["Investment may broaden beyond a small set of chip suppliers if adoption creates measurable productivity gains."],
        "opposing_arguments": ["Capital intensity, customer concentration, supply constraints, and valuation can break the spending-to-equity-return chain."],
        "unresolved_questions": ["What measurable capex, utilization, and return-on-investment data would change the thesis?", "How much incremental technology risk is acceptable given current look-through exposure?"],
        "thesis_links": [
            {"assumption": assumptions[0], "threat": "AI infrastructure spending slows before customers realize durable returns.", "scenario_id": "ai-capex"},
            {"assumption": assumptions[1], "threat": "Discount rates or recession pressure long-duration growth valuations.", "scenario_id": "rates"},
            {"assumption": assumptions[2], "threat": "Shared mega-cap positions amplify a sector drawdown.", "scenario_id": "tech-drawdown"},
        ],
        "evidence_quality": "Limited: deterministic committee rules; latest macro readings and headlines are context, not evidence of causation.",
        "human_decision": "No buy/sell recommendation. Review assumptions, data freshness, and risk capacity before making any decision.",
    }
