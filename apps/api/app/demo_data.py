"""RiskRoom-owned, synthetic demo fixtures. Not live holdings or market data."""

ETF_HOLDINGS = {
    "VOO": [("MSFT", 9.5, "Technology"), ("NVDA", 8.0, "Technology"), ("AAPL", 7.0, "Technology"), ("AMZN", 4.0, "Consumer Discretionary"), ("META", 2.5, "Communication Services"), ("JPM", 1.4, "Financials"), ("XOM", 1.2, "Energy"), ("LLY", 1.2, "Healthcare"), ("AVGO", 3.0, "Technology"), ("COST", 0.9, "Consumer Staples"), ("ORCL", 1.5, "Technology"), ("CRM", 0.8, "Technology"), ("AMD", 0.8, "Technology")],
    "QQQ": [("MSFT", 9.5, "Technology"), ("NVDA", 9.0, "Technology"), ("AAPL", 8.5, "Technology"), ("AMZN", 5.0, "Consumer Discretionary"), ("META", 4.5, "Communication Services"), ("AVGO", 5.0, "Technology"), ("COST", 2.5, "Consumer Staples"), ("GOOGL", 5.0, "Communication Services"), ("TSLA", 2.5, "Consumer Discretionary"), ("NFLX", 2.0, "Communication Services"), ("AMD", 3.0, "Technology"), ("PLTR", 2.5, "Technology"), ("ORCL", 2.0, "Technology")],
    "VGT": [("MSFT", 19.0, "Technology"), ("NVDA", 17.0, "Technology"), ("AAPL", 15.0, "Technology"), ("AVGO", 4.0, "Technology"), ("ORCL", 2.0, "Technology"), ("CRM", 1.8, "Technology"), ("AMD", 1.8, "Technology"), ("CSCO", 1.7, "Technology"), ("ACN", 1.5, "Technology"), ("IBM", 1.5, "Technology"), ("PLTR", 2.0, "Technology"), ("NOW", 2.5, "Technology"), ("QCOM", 3.0, "Technology"), ("TXN", 2.0, "Technology"), ("INTC", 1.0, "Technology"), ("AMAT", 3.0, "Technology"), ("MU", 2.0, "Technology")],
    "VTI": [("MSFT", 8.0, "Technology"), ("NVDA", 7.0, "Technology"), ("AAPL", 6.5, "Technology"), ("AMZN", 3.3, "Consumer Discretionary"), ("META", 2.1, "Communication Services"), ("JPM", 1.2, "Financials"), ("XOM", 1.0, "Energy"), ("LLY", 1.0, "Healthcare"), ("AVGO", 2.0, "Technology"), ("COST", 0.8, "Consumer Staples"), ("ORCL", 1.2, "Technology"), ("CRM", 1.0, "Technology"), ("AMD", 0.9, "Technology"), ("CSCO", 1.0, "Technology"), ("TXN", 0.8, "Technology"), ("ACN", 1.3, "Technology")],
    "ARKK": [("TSLA", 9.0, "Consumer Discretionary"), ("COIN", 7.0, "Financials"), ("ROKU", 5.0, "Communication Services"), ("PLTR", 4.5, "Technology"), ("SHOP", 4.0, "Technology"), ("CRISPR", 3.5, "Healthcare"), ("RBLX", 3.0, "Communication Services"), ("HOOD", 2.8, "Financials"), ("PATH", 2.5, "Technology"), ("U", 2.2, "Technology"), ("ZM", 4.0, "Technology"), ("TWLO", 4.0, "Technology")],
    "TLT": [("UST20Y", 100.0, "Fixed Income")],
}

PORTFOLIO = [
    {"ticker": "VOO", "weight": 0.25},
    {"ticker": "QQQ", "weight": 0.20},
    {"ticker": "VGT", "weight": 0.15},
    {"ticker": "VTI", "weight": 0.20},
    {"ticker": "ARKK", "weight": 0.10},
    {"ticker": "TLT", "weight": 0.10},
]

SCENARIOS = [
    {"id": "ai-capex", "name": "AI capex -30%", "description": "Hyperscaler investment slows sharply", "shocks": {"Technology": -0.30, "Communication Services": -0.16}},
    {"id": "rates", "name": "Rates +200 bps", "description": "Long rates stay higher for longer", "shocks": {"Technology": -0.18, "Consumer Discretionary": -0.12, "Fixed Income": -0.14, "Financials": 0.02}},
    {"id": "recession", "name": "US recession", "description": "Broad earnings and demand contract", "shocks": {"Technology": -0.25, "Consumer Discretionary": -0.30, "Communication Services": -0.22, "Financials": -0.24, "Energy": -0.28, "Healthcare": -0.12, "Consumer Staples": -0.08, "Fixed Income": 0.08}},
    {"id": "tech-drawdown", "name": "Technology -25%", "description": "Technology sector reprices lower", "shocks": {"Technology": -0.25}},
    {"id": "inflation", "name": "Inflation shock", "description": "Input and funding costs rise", "shocks": {"Technology": -0.12, "Consumer Discretionary": -0.16, "Energy": 0.18, "Fixed Income": -0.10}},
]

# Synthetic daily returns for a labeled demo history; formulas are deterministic.
def daily_returns(days: int = 504) -> list[float]:
    import math
    return [0.00028 + 0.009 * math.sin(i * 0.31) + 0.004 * math.sin(i * 0.071 + 0.8) for i in range(days)]
