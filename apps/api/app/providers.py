"""Replaceable adapters for synthetic demo and configured live data sources."""
import os
import random
import secrets
import time
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Protocol

import httpx

from .demo_data import ETF_HOLDINGS, PORTFOLIO


class MarketDataProvider(Protocol):
    def prices(self, symbols: list[str], start: str, end: str) -> list[dict]: ...


class ETFDataProvider(Protocol):
    def holdings(self, ticker: str) -> list: ...


class MacroDataProvider(Protocol):
    def observations(self, series: str, start: str, end: str) -> list: ...


class PortfolioRepository(Protocol):
    def get(self, portfolio_id: str) -> dict: ...


class ScenarioRepository(Protocol):
    def save(self, record: dict) -> None: ...


class EvidenceRepository(Protocol):
    def search(self, query: str, limit: int = 10) -> list: ...


class LocalDataProvider:
    mode = "demo"

    def portfolio_snapshot(self, portfolio_id: str = "riskroom-demo") -> dict:
        return {"id": portfolio_id, "name": "AI Infrastructure Core", "holdings": deepcopy(PORTFOLIO)}

    def holdings(self, ticker: str) -> list:
        return [{"ticker": symbol, "weight": weight / 100, "sector": sector, "source": "RiskRoom synthetic demo fixture"} for symbol, weight, sector in deepcopy(ETF_HOLDINGS.get(ticker.upper(), []))]

    def prices(self, symbols: list[str], start: str, end: str) -> list[dict]:
        import math
        from datetime import date, timedelta
        start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
        result = []
        for symbol in symbols:
            price = 100.0
            for day in range(252):
                observed = date(2025, 1, 1) + timedelta(days=day)
                price *= 1 + 0.002 * math.sin(day * 0.13 + sum(map(ord, symbol)) * 0.01)
                if start_date <= observed <= end_date:
                    result.append({"ticker": symbol, "observed_at": observed.isoformat(), "close": price, "source": "RiskRoom synthetic demo fixture"})
        return result

    def observations(self, series: str, start: str, end: str) -> list:
        return []  # Demo data has no macro observation series.


class FreshSyntheticMarketProvider:
    """Generate a new clearly simulated market snapshot for each analysis run."""

    @staticmethod
    def prices(symbols: list[str], start: str, end: str) -> list[dict]:
        rng = random.Random(secrets.randbits(64))
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        dates = []
        current = first
        while current <= last:
            if current.weekday() < 5:
                dates.append(current.isoformat())
            current += timedelta(days=1)
        market_moves = [rng.gauss(0.00025, 0.0105) for _ in dates]
        rows = []
        for ticker in dict.fromkeys(symbol.upper() for symbol in symbols):
            close = rng.uniform(60, 420)
            beta = rng.uniform(0.75, 1.35)
            volatility = rng.uniform(0.007, 0.019)
            for day, observed_at in enumerate(dates):
                close *= max(0.85, 1 + beta * market_moves[day] + rng.gauss(0.00015, volatility))
                rows.append({"ticker": ticker, "observed_at": observed_at, "close": round(close, 4), "source": "Fresh RiskRoom simulated close path"})
        return rows

    @staticmethod
    def context(tickers: list[str]) -> dict:
        rng = random.SystemRandom()
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        readings = [
            ("SIMULATED_TREASURY_YIELD", "Simulated 10-year Treasury yield", rng.uniform(3.0, 5.5), "%"),
            ("SIMULATED_FEDERAL_FUNDS_RATE", "Simulated federal funds rate", rng.uniform(3.0, 5.5), "%"),
            ("SIMULATED_INFLATION", "Simulated inflation pressure", rng.uniform(1.5, 5.5), "%"),
        ]
        macro = [{"series": series, "label": label, "value": round(value, 2), "unit": unit, "observed_at": generated_at, "source": "RiskRoom simulation", "source_url": ""} for series, label, value, unit in readings]
        candidates = [ticker.upper() for ticker in tickers if ticker and not ticker.upper().startswith("OTHER_")] or ["TECH SECTOR"]
        headlines = [
            "Hypothetical demand cools as customers scrutinize infrastructure budgets",
            "Scenario: higher financing costs reset long-duration growth valuations",
            "Counterfactual: strong orders fail to convert into durable margins",
            "Simulation: supply constraints delay a broad technology spending cycle",
            "Hypothetical risk-off move tests crowded growth positioning",
            "Scenario: accelerating adoption broadens demand beyond current leaders",
        ]
        rng.shuffle(headlines)
        news = [{"title": headlines[index], "url": "", "source": "RiskRoom simulated scenario", "published_at": generated_at, "summary": "Illustrative scenario text; not a reported event.", "sentiment": rng.choice(["Bearish", "Neutral", "Bullish"]), "sentiment_score": None, "ticker": candidates[index % len(candidates)]} for index in range(3)]
        return {"macro": {"observations": macro, "unavailable": [], "status": "simulated"}, "news": {"items": news, "status": "simulated"}, "generated_at": generated_at}


class AlphaVantageDataProvider:
    """Live daily closes and ETF look-through data from Alpha Vantage."""

    _BASE_URL = "https://www.alphavantage.co/query"
    _cache: dict[tuple[str, str, tuple[tuple[str, str], ...]], tuple[float, dict]] = {}
    _PROFILE_CACHE_SECONDS = 24 * 60 * 60
    _PRICE_CACHE_SECONDS = 15 * 60
    _CONTEXT_CACHE_SECONDS = 6 * 60 * 60
    _NEWS_CACHE_SECONDS = 30 * 60

    def configured(self) -> bool:
        return bool(os.getenv("ALPHA_VANTAGE_API_KEY", "").strip())

    def _request(self, function: str, symbol: str | None = None, params: dict | None = None, ttl: int | None = None) -> dict:
        if not self.configured():
            raise RuntimeError("ALPHA_VANTAGE_API_KEY is not configured.")
        request_params = {str(k): str(v) for k, v in (params or {}).items()}
        if symbol:
            request_params["symbol"] = symbol.upper()
        cache_key = tuple(sorted(request_params.items()))
        key = (function, symbol.upper() if symbol else "", cache_key)
        cache_ttl = ttl or (self._PROFILE_CACHE_SECONDS if function == "ETF_PROFILE" else self._PRICE_CACHE_SECONDS)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < cache_ttl:
            return cached[1]
        try:
            response = httpx.get(
                self._BASE_URL,
                params={"function": function, **request_params, "apikey": os.environ["ALPHA_VANTAGE_API_KEY"]},
                timeout=12.0,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Alpha Vantage request failed for {symbol.upper() if symbol else function} (network or HTTP error).") from exc
        except ValueError as exc:
            raise RuntimeError(f"Alpha Vantage returned invalid JSON for {symbol.upper() if symbol else function}.") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"Alpha Vantage returned an invalid response for {symbol.upper() if symbol else function}.")
        vendor_error = payload.get("Error Message") or payload.get("Information") or payload.get("Note")
        if vendor_error:
            # Do not echo request URLs or vendor response text: either may contain sensitive details.
            raise RuntimeError(f"Alpha Vantage did not return data for {symbol.upper() if symbol else function} (provider limit, access, or symbol issue).")
        self._cache[key] = (time.monotonic(), payload)
        return payload

    def economic_snapshot(self) -> dict:
        """Fetch a small, cached set of observed macro series; failures stay isolated."""
        definitions = [
            ("TREASURY_YIELD", {"interval": "daily", "maturity": "10year"}, "US Treasury 10-year yield", "%"),
            ("FEDERAL_FUNDS_RATE", {"interval": "monthly"}, "US federal funds rate", "%"),
            ("CPI", {"interval": "monthly"}, "US CPI", "index"),
        ]
        observations = []
        unavailable = []
        for function, params, label, unit in definitions:
            try:
                payload = self._request(function, params=params, ttl=self._CONTEXT_CACHE_SECONDS)
                rows = payload.get("data") or []
                valid_rows = [item for item in rows if isinstance(item, dict) and item.get("date") and item.get("value") not in (None, ".")]
                row = max(valid_rows, key=lambda item: item["date"]) if valid_rows else None
                if row is None:
                    unavailable.append(label)
                    continue
                observations.append({"series": function, "label": label, "value": float(row["value"]), "unit": unit, "observed_at": row["date"], "source": "Alpha Vantage", "source_url": "https://www.alphavantage.co/documentation/"})
            except (RuntimeError, TypeError, ValueError):
                unavailable.append(label)
        return {"observations": observations, "unavailable": unavailable, "status": "live" if observations else "unavailable"}

    def market_news(self, tickers: list[str], limit: int = 5) -> dict:
        tickers = list(dict.fromkeys(ticker.upper() for ticker in tickers if ticker))[:3]
        if not tickers:
            return {"items": [], "status": "unavailable"}
        try:
            payload = self._request("NEWS_SENTIMENT", params={"tickers": ",".join(tickers), "limit": str(min(max(limit, 1), 10)), "sort": "LATEST"}, ttl=self._NEWS_CACHE_SECONDS)
        except RuntimeError:
            return {"items": [], "status": "unavailable"}
        items = []
        for entry in payload.get("feed", []):
            if not isinstance(entry, dict) or not entry.get("title") or not entry.get("url"):
                continue
            items.append({"title": str(entry["title"]), "url": str(entry["url"]), "source": str(entry.get("source") or "Alpha Vantage news feed"), "published_at": str(entry.get("time_published") or ""), "summary": str(entry.get("summary") or ""), "sentiment": str(entry.get("overall_sentiment_label") or "Unscored"), "sentiment_score": entry.get("overall_sentiment_score")})
            if len(items) >= limit:
                break
        return {"items": items, "status": "live" if items else "unavailable"}

    @staticmethod
    def _weight(value) -> float | None:
        if value is None:
            return None
        if isinstance(value, str):
            raw = value.strip().replace(",", "")
            is_percent = raw.endswith("%")
            raw = raw.rstrip("% ")
            try:
                number = float(raw)
            except ValueError:
                return None
            return number / 100 if is_percent or number > 1 else number
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number / 100 if number > 1 else number

    @classmethod
    def _find_rows(cls, value, kind: str) -> list[dict]:
        """Find vendor arrays without assuming one response nesting level."""
        if isinstance(value, dict):
            for name, child in value.items():
                normalized = name.lower().replace(" ", "_")
                is_target = (kind == "holding" and normalized in {"holdings", "constituents", "portfolio_holdings"}) or (kind == "sector" and normalized in {"sectors", "sector_weights", "sector_allocations"})
                if is_target and isinstance(child, list):
                    return [row for row in child if isinstance(row, dict)]
            for child in value.values():
                rows = cls._find_rows(child, kind)
                if rows:
                    return rows
        elif isinstance(value, list):
            for child in value:
                rows = cls._find_rows(child, kind)
                if rows:
                    return rows
        return []

    def _profile(self, ticker: str) -> dict:
        return self._request("ETF_PROFILE", ticker)

    def holdings(self, ticker: str) -> list[dict]:
        payload = self._profile(ticker)
        rows = self._find_rows(payload, "holding")
        result = []
        for row in rows:
            symbol = row.get("symbol") or row.get("ticker") or row.get("asset")
            weight = next((self._weight(row.get(key)) for key in ("weight", "allocation", "portfolio_weight", "holding_weight") if row.get(key) is not None), None)
            if not symbol or weight is None or weight <= 0:
                continue
            sector = row.get("sector") or row.get("sector_name") or row.get("industry")
            result.append({"ticker": str(symbol).upper(), "weight": weight, "sector": sector or "Other / unclassified"})
        if not result:
            raise RuntimeError(f"Alpha Vantage returned no usable constituent weights for {ticker.upper()}; confirm ETF_PROFILE access for this symbol.")
        return result

    def sector_allocations(self, ticker: str) -> list[dict]:
        payload = self._profile(ticker)
        rows = self._find_rows(payload, "sector")
        result = []
        for row in rows:
            name = row.get("sector") or row.get("name") or row.get("asset_type")
            weight = next((self._weight(row.get(key)) for key in ("weight", "allocation", "portfolio_weight") if row.get(key) is not None), None)
            if name and weight is not None and weight > 0:
                result.append({"sector": str(name), "weight": weight})
        return result

    def prices(self, symbols: list[str], start: str, end: str) -> list[dict]:
        result: list[dict] = []
        for symbol in dict.fromkeys(item.upper() for item in symbols):
            payload = self._request("TIME_SERIES_DAILY", symbol)
            daily = next((value for key, value in payload.items() if key.startswith("Time Series (Daily)")), None)
            if not isinstance(daily, dict):
                raise RuntimeError(f"Alpha Vantage returned no daily price history for {symbol}.")
            for observed_at, values in daily.items():
                if start <= observed_at <= end and isinstance(values, dict) and values.get("4. close") is not None:
                    result.append({"ticker": symbol, "observed_at": observed_at, "close": float(values["4. close"]), "source": "Alpha Vantage TIME_SERIES_DAILY · unadjusted close"})
        return sorted(result, key=lambda row: (row["ticker"], row["observed_at"]))


class SnowflakeDataProvider:
    def configured(self) -> bool:
        return all(os.getenv(key) for key in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE"))

    def connect(self):
        if not self.configured():
            raise RuntimeError("Snowflake credentials are not configured.")
        import snowflake.connector
        return snowflake.connector.connect(account=os.environ["SNOWFLAKE_ACCOUNT"], user=os.environ["SNOWFLAKE_USER"], password=os.environ["SNOWFLAKE_PASSWORD"], database=os.environ["SNOWFLAKE_DATABASE"], schema=os.environ["SNOWFLAKE_SCHEMA"], warehouse=os.environ["SNOWFLAKE_WAREHOUSE"])

    def prices(self, symbols: list[str], start: str, end: str) -> list[dict]:
        if not symbols:
            return []
        placeholders = ", ".join(["%s"] * len(symbols))
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute(f"SELECT ticker, observed_at, close_price FROM HISTORICAL_MARKET_PRICES WHERE ticker IN ({placeholders}) AND observed_at >= %s AND observed_at <= %s ORDER BY observed_at", [*symbols, start, end])
            return [{"ticker": row[0], "observed_at": row[1], "close": row[2]} for row in cursor.fetchall()]
        finally:
            connection.close()

    def holdings(self, ticker: str) -> list[dict]:
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT security_ticker, weight, sector, country, as_of FROM ETF_HOLDINGS WHERE etf_ticker = %s QUALIFY as_of = MAX(as_of) OVER (PARTITION BY etf_ticker)", (ticker.upper(),))
            return [{"ticker": row[0], "weight": row[1], "sector": row[2], "country": row[3], "as_of": row[4]} for row in cursor.fetchall()]
        finally:
            connection.close()

    def observations(self, series: str, start: str, end: str) -> list[dict]:
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT series_id, observed_at, value, source FROM MACRO_OBSERVATIONS WHERE series_id = %s AND observed_at >= %s AND observed_at <= %s ORDER BY observed_at", (series, start, end))
            return [{"series": row[0], "observed_at": row[1], "value": row[2], "source": row[3]} for row in cursor.fetchall()]
        finally:
            connection.close()

    def search_evidence(self, query: str, limit: int = 10) -> list[dict]:
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT evidence_id, title, excerpt, source, observed_at FROM MARKET_EVIDENCE WHERE LOWER(title || ' ' || excerpt) LIKE %s ORDER BY observed_at DESC LIMIT %s", (f"%{query.lower()}%", min(max(limit, 1), 50)))
            return [{"id": row[0], "title": row[1], "excerpt": row[2], "source": row[3], "observed_at": row[4]} for row in cursor.fetchall()]
        finally:
            connection.close()


class TigerDataProvider:
    def configured(self) -> bool:
        return bool(os.getenv("TIGERDATA_DATABASE_URL"))

    def engine(self):
        if not self.configured():
            raise RuntimeError("TigerData credentials are not configured.")
        from sqlalchemy import create_engine
        return create_engine(os.environ["TIGERDATA_DATABASE_URL"], pool_pre_ping=True)

    def save_committee_run(self, run_id: str, portfolio_id: str, thesis: str, trace: dict) -> None:
        import json
        from sqlalchemy import text
        with self.engine().begin() as connection:
            connection.execute(text("INSERT INTO portfolios (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING"), {"id": portfolio_id, "name": portfolio_id})
            connection.execute(text("INSERT INTO committee_runs (run_id, portfolio_id, thesis, status, trace) VALUES (:id, :portfolio, :thesis, :status, CAST(:trace AS JSONB)) ON CONFLICT (run_id) DO UPDATE SET trace = EXCLUDED.trace"), {"id": run_id, "portfolio": portfolio_id, "thesis": thesis, "status": "completed", "trace": json.dumps(trace)})

    def save_scenario_run(self, run_id: str, portfolio_id: str, scenario_id: str, parameters: dict, result: dict) -> None:
        import json
        from sqlalchemy import text
        with self.engine().begin() as connection:
            connection.execute(text("INSERT INTO portfolios (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING"), {"id": portfolio_id, "name": portfolio_id})
            connection.execute(text("INSERT INTO scenario_runs (run_id, portfolio_id, scenario_id, parameters, result) VALUES (:id, :portfolio, :scenario, CAST(:parameters AS JSONB), CAST(:result AS JSONB)) ON CONFLICT (run_id) DO UPDATE SET result = EXCLUDED.result"), {"id": run_id, "portfolio": portfolio_id, "scenario": scenario_id, "parameters": json.dumps(parameters), "result": json.dumps(result)})


class GeminiProvider:
    def configured(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY", "").strip())
