"""Evidence-linked thesis tripwires using public SEC company facts.

The signal proxies are deliberately narrow: issuer-reported facts are not a
complete measure of AI demand. All portfolio impact remains a user-editable
deterministic sector stress, not a forecast from the reported fact.
"""
from __future__ import annotations

import asyncio
import math
import os
import random
import time
from datetime import date

import httpx


_SEC_ISSUERS = {
    "MSFT": {"cik": "0000789019", "name": "Microsoft"},
    "NVDA": {"cik": "0001045810", "name": "NVIDIA"},
}
_FACT_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_SECONDS = 3600
_TIMEOUT_SECONDS = 7.0

_SIGNALS = [
    {
        "id": "msft-capex",
        "issuer": "MSFT",
        "title": "A hyperscaler pulls back on infrastructure spend",
        "assumption": "Microsoft's reported capital investment is a narrow proxy for one large infrastructure buyer; it does not represent industry-wide AI spending.",
        "indicator": "Microsoft quarterly property and equipment purchases",
        "concepts": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
        "threshold_pct": 0.0,
        "threshold_label": "YoY growth below",
        "shocks": {"Technology": -0.24, "Communication Services": -0.12},
        "caveat": "Quarterly XBRL values are compared with the nearest quarter ending about one year earlier. Filing amendments and fiscal calendars can affect comparability.",
    },
    {
        "id": "nvda-revenue",
        "issuer": "NVDA",
        "title": "The compute supplier's reported sales contract",
        "assumption": "NVIDIA total reported revenue is a narrow demand proxy; it is not an AI-only revenue measure and does not establish causation.",
        "indicator": "NVIDIA quarterly revenue",
        "concepts": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"],
        "threshold_pct": 0.0,
        "threshold_label": "YoY growth below",
        "shocks": {"Technology": -0.30},
        "caveat": "Reported company revenue is compared with the nearest quarter ending about one year earlier. Fiscal calendars and filing amendments can affect comparability.",
    },
    {
        "id": "msft-revenue",
        "issuer": "MSFT",
        "title": "Infrastructure spending fails to show up in sales",
        "assumption": "Microsoft total reported revenue is a limited monetization proxy; it does not isolate AI revenue or customer returns.",
        "indicator": "Microsoft quarterly revenue",
        "concepts": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"],
        "threshold_pct": 0.0,
        "threshold_label": "YoY growth below",
        "shocks": {"Technology": -0.20, "Communication Services": -0.10},
        "caveat": "Reported company revenue is compared with the nearest quarter ending about one year earlier. Fiscal calendars and filing amendments can affect comparability.",
    },
]


def _sec_user_agent() -> str:
    value = os.getenv("SEC_USER_AGENT", "").strip()
    if not value or "example.com" in value.lower() or "your-team" in value.lower():
        return ""
    return value


async def _company_facts(ticker: str, client: httpx.AsyncClient) -> dict | None:
    cached = _FACT_CACHE.get(ticker)
    if cached and time.monotonic() - cached[0] < _CACHE_SECONDS:
        return cached[1]
    issuer = _SEC_ISSUERS[ticker]
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{issuer['cik']}.json"
    try:
        response = await client.get(url)
        response.raise_for_status()
        facts = response.json()
        if not isinstance(facts, dict) or not isinstance(facts.get("facts"), dict):
            return None
        _FACT_CACHE[ticker] = (time.monotonic(), facts)
        return facts
    except (httpx.HTTPError, ValueError):
        return None


def _quarterly_records(facts: dict, concepts: list[str]) -> list[dict]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    selected = None
    for concept in concepts:
        definition = us_gaap.get(concept)
        if not isinstance(definition, dict):
            continue
        usd_facts = definition.get("units", {}).get("USD", [])
        records = []
        for item in usd_facts:
            if item.get("form") not in {"10-Q", "10-K"} or not item.get("start") or not item.get("end"):
                continue
            try:
                duration = (date.fromisoformat(item["end"]) - date.fromisoformat(item["start"])).days + 1
                value = abs(float(item["val"]))
            except (TypeError, ValueError):
                continue
            # Use three-month values only. Cash-flow facts often also include
            # six- and nine-month cumulative values for the same fiscal year.
            if 65 <= duration <= 120 and value > 0 and math.isfinite(value):
                records.append({"start": item["start"], "end": item["end"], "filed": item.get("filed", ""), "value": value})
        if records:
            selected = records
            break
    if not selected:
        return []

    # Keep the latest filed version for each reporting period, then find the
    # closest period ending roughly a year before the latest observation.
    by_end: dict[str, dict] = {}
    for record in selected:
        current = by_end.get(record["end"])
        if current is None or record["filed"] > current["filed"]:
            by_end[record["end"]] = record
    return sorted(by_end.values(), key=lambda item: item["end"])


def _latest_yoy(facts: dict | None, concepts: list[str]) -> dict | None:
    if facts is None:
        return None
    for concept in concepts:
        records = _quarterly_records(facts, [concept])
        if len(records) < 2:
            continue
        latest = records[-1]
        latest_date = date.fromisoformat(latest["end"])
        prior_candidates = []
        for record in records[:-1]:
            days = (latest_date - date.fromisoformat(record["end"])).days
            if 330 <= days <= 400:
                prior_candidates.append((abs(days - 365), record))
        if not prior_candidates:
            continue
        prior = min(prior_candidates, key=lambda item: item[0])[1]
        return {
            "latest_value_billions": round(latest["value"] / 1_000_000_000, 2),
            "growth_pct": round((latest["value"] / prior["value"] - 1) * 100, 2),
            "period_end": latest["end"],
            "filed": latest["filed"],
            "prior_period_end": prior["end"],
        }
    return None


async def build_tripwires() -> dict:
    """Fetch two issuer fact sets at most; fall back to source-linked tripwires."""
    user_agent = _sec_user_agent()
    facts_by_ticker: dict[str, dict | None] = {ticker: None for ticker in _SEC_ISSUERS}
    if user_agent:
        headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, headers=headers, follow_redirects=True) as client:
            fetched = await asyncio.gather(*(_company_facts(ticker, client) for ticker in _SEC_ISSUERS))
        facts_by_ticker = dict(zip(_SEC_ISSUERS, fetched))

    items = []
    for signal in _SIGNALS:
        ticker = signal["issuer"]
        issuer = _SEC_ISSUERS[ticker]
        observation = _latest_yoy(facts_by_ticker[ticker], signal["concepts"])
        rng = random.SystemRandom()
        scenario_base = observation["growth_pct"] if observation else rng.uniform(-24, 38)
        simulation = {
            "latest_value_billions": observation["latest_value_billions"] if observation else round(rng.uniform(8, 70), 2),
            "growth_pct": round(scenario_base + rng.uniform(-18, 12), 2),
            "period_end": date.today().isoformat(),
            "filed": "SCENARIO",
            "prior_period_end": "SCENARIO",
        }
        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{issuer['cik']}.json"
        items.append({
            "id": signal["id"],
            "issuer": ticker,
            "issuer_name": issuer["name"],
            "title": signal["title"],
            "assumption": signal["assumption"],
            "indicator": signal["indicator"],
            "threshold_pct": signal["threshold_pct"],
            "threshold_label": signal["threshold_label"],
            "shocks": signal["shocks"],
            "observation": observation,
            "simulation": simulation,
            "source_status": "live" if observation else "simulated",
            "source_name": "SEC EDGAR Company Facts",
            "source_url": facts_url,
            "filings_url": f"https://www.sec.gov/edgar/browse/?CIK={int(issuer['cik'])}&owner=exclude",
            "caveat": signal["caveat"],
        })
    return {
        "items": items,
        "provider": "SEC EDGAR Company Facts",
        "live_enabled": bool(user_agent),
        "status": "live" if user_agent and any(item["observation"] for item in items) else "simulated",
        "note": "SEC facts are shown as reported when retrieved; a fresh modeled growth scenario is provided separately for each run.",
    }
