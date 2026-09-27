# RiskRoom source repository audit

Audit date: 2026-09-26. The four repositories remain unchanged and are treated as source material. Conclusions below come from their checked-in code, manifests, READMEs, tests, notebook, and license files.

## Executive summary

| Repository | What it contains | License found | RiskRoom decision |
|---|---|---|---|
| [AI-Portfolio-Intelligence-System](https://github.com/pavelkoya/AI-Portfolio-Intelligence-System) | Python portfolio analytics pipeline with Streamlit, SQLite, quant models, and a three-role LLM committee | MIT; copyright notice names Danya Banksy (2026) | Best reference for familiar risk metrics and data validation. Do not import its broker-linked pipeline or recommendation/rebalance flow. No source copied for the initial RiskRoom build. |
| [PortfolioOverlap](https://github.com/IV1T3/PortfolioOverlap) | Python CLI for ETF holdings resolution and weighted overlap, with issuer scrapers and local ARK holdings | No LICENSE/COPYING/NOTICE file found; README does not grant a reuse license | Valuable conceptual reference for holdings decomposition. Do not copy code or bundled holdings until licensing and data redistribution rights are clarified. Implement a clean, local demo holdings provider. |
| [quorum-investment-committee](https://github.com/sidnov6/quorum-investment-committee) | FastAPI + Next.js multi-agent committee, grounded tools, audit transcript, paper portfolio, and backtest | No LICENSE/COPYING/NOTICE file found; README does not grant a reuse license | Strongest architecture reference for structured agent orchestration, evidence grounding, deterministic fallbacks, and streaming. Do not copy code. Reimplement to match thesis-first scope and avoid its allocation/trading-like outputs. |
| [Stress-Testing-a-Markowitz-Portfolio](https://github.com/Lukirby/Stress-Testing-a-Markowitz-Portfolio) | Research notebook predicting NVDA/SPY covariance and variance with an LSTM and comparing Gaussian/ARMA/GARCH VaR/ES | No LICENSE/COPYING/NOTICE file found; README says academic/educational use only | Research reference only. Do not reuse notebook/code/data. Build a simpler transparent scenario engine and validate formulas independently. |

The missing licenses for three repositories are a blocker to copying their implementation. This audit therefore recommends no code reuse at project start. The MIT repository can be reused if needed, but any reused portion must retain its copyright and license notice; a fresh implementation avoids unnecessary legal and architectural coupling.

## Repository details

### AI-Portfolio-Intelligence-System

- **Stack and architecture:** Python 3.9+ per README. A command-line orchestration pipeline in `main.py` coordinates data ingestion, deterministic quant modules, AI committee, persistence, PDF report, and Streamlit dashboard. Dependencies include pandas/NumPy/SciPy, yfinance, Robinhood client, PyPortfolioOpt, scikit-learn, SQLAlchemy, Anthropic, Transformers/Torch, Streamlit, Plotly, ReportLab-related output support, and dotenv.
- **Entry points and interfaces:** `python main.py` runs the pipeline; `reporting/dashboard.py` and `reporting/pages/import_portfolio.py` are Streamlit entry points. No REST API. Inputs include broker data and CSV/screenshot import paths.
- **Data models and storage:** SQLAlchemy-backed SQLite (`data/database.py`) stores portfolio snapshots, prices, and analysis runs. Data is represented mainly as pandas DataFrames and dictionaries. `data/data_loader.py`, `csv_importer.py`, `screenshot_importer.py`, `analyst_fetcher.py`, and `validator.py` handle acquisition/cleaning.
- **Portfolio/ETF logic:** Portfolio optimizer and risk analysis operate on tickers/market values; the repository does not provide ETF constituent decomposition or effective look-through exposure. Broker ingestion is Robinhood-oriented.
- **Quantitative logic:** `quant/risk.py` calculates portfolio/per-security metrics including return-based risk, VaR/CVaR, drawdown, beta and Sharpe/Sortino. `quant/portfolio.py` and `hrp_engine.py` cover portfolio optimization/HRP. `garch_engine.py`, `regime_engine.py`, `trend_engine.py`, `technical.py`, `backtest_engine.py`, and `post_rebalance_engine.py` add forecasting, regime, technical indicators, backtesting, and validation. Claims should be rechecked against method assumptions before adoption; models are coupled to this pipeline's data shape.
- **AI and reports:** `ai/committee.py`, `committee_inputs.py`, and `prompts.py` implement Bull/Bear/CRO (risk officer) discussion via provider/model selection. It is not the five-agent thesis/red-team workflow. It has structured inputs but is designed around position analysis and rebalancing. `reporting/pdf_generator.py` and Streamlit dashboard provide reporting/visualization.
- **Configuration/dependencies:** Configuration in `config/settings.py`, broker mappings in `config/broker_maps.py`, pinned `requirements.txt`; README describes environment keys. No `.env.example` in the checked-in file list.
- **Tests:** `tests/test_quant.py` and `tests/test_data_loader.py`; useful regression coverage, not comprehensive application/API coverage.
- **License:** MIT (`LICENSE`, copyright Danya Banksy, 2026). Retain the full notice for any substantial copied portion.
- **Strengths:** Broad set of conventional risk measures; explicit quant/data/AI module boundaries; validation and tests; an existing visual report.
- **Weaknesses and compatibility:** Broker-centric ingestion, synchronous monolith, Streamlit UX, many pinned/heavy dependencies, no ETF look-through, Anthropic-first integration, and rebalancing recommendations conflict with RiskRoom's explicit no-trade decision-support boundary. Not compatible as a foundation.
- **Reuse decision:** Use as a reference for candidate risk metrics only. If a later direct code reuse is justified, isolate a small MIT-licensed quant function, retain its copyright/license, and add deterministic tests before integration. Do not import full pipeline or optimizer.

### PortfolioOverlap

- **Stack and architecture:** Python CLI in `portfoliooverlap/main.py`, custom primitives (`ETF`, `Holding`, `ISIN`, `Ticker`), JSON/YAML local data, and issuer/API adapters. Dependencies include requests/cloudscraper, pyexcel, Alpha Vantage, OpenFIGI-related modules, YAML, dotenv, and tqdm (see `requirements.txt` and Pipfile).
- **Entry points/interfaces:** Run `python portfoliooverlap/main.py`; configure a YAML portfolio by ISIN and API key in `.env`. There is no web API or dashboard.
- **Data models/storage:** Holdings are Python objects; ETF composition, ticker/ISIN and company mappings are JSON/YAML. No database. Holdings snapshots are scraped/downloaded from ARK, iShares, or Lyxor-specific URLs and cached locally.
- **ETF and overlap logic:** Resolves known ETFs into constituents and aggregates constituent portfolio percentages. `calculate_overlapping_percentage` compares common ISIN holdings using the minimum of portfolio and ETF weights and normalizes by combined weight. This is a pairwise similarity score, not the effective weighted issuer exposure needed by RiskRoom. Its look-through path sets parent ETF exposure to zero and adds constituent weights, but leaves quantities/prices unresolved and explicitly does not recursively expand nested ETFs. Data is limited to configured issuers/ETFs, matching relies on external symbol/name mapping.
- **Quant/risk/AI/visualization:** No scenario engine, VaR/CVaR, committee, LLM, REST API, or dashboard. Output is formatted terminal text.
- **Configuration/dependencies/tests:** `settings.json`, `portfolio.yml`, `etf_list.yml`, requirements and Pipfile lock. No tests found. Several live scrapers and Alpha Vantage API calls make reproducibility and current issuer formats dependencies.
- **License:** No LICENSE/COPYING/NOTICE file found. README contains no permission to reuse. Bundled holdings are third-party financial data whose redistribution terms are also unspecified.
- **Strengths:** ETF decomposition is the closest domain reference; ISIN-oriented entity handling; holdings snapshots illustrate provider separation.
- **Weaknesses and compatibility:** Narrow ETF coverage; brittle issuer-specific parsing; external APIs; incomplete price/value semantics after decomposition; recursive ETF holdings are not supported; stale-data timestamp provenance is not surfaced in the CLI; no test suite/license.
- **Reuse decision:** Do not copy code or bundled ETF snapshots. Reimplement weighted look-through and overlap around explicit market-value weights, stable security identifiers, source/as-of metadata, and local clearly labeled demo data. Seek permission/license and data redistribution terms before importing any source material.

### quorum-investment-committee

- **Stack and architecture:** Python FastAPI backend (`backend/app/main.py`) and Next.js 14/React/TypeScript/Tailwind frontend. Backend separates `quorum/tools`, `committee`, `models`, `backtest`, `store`, and paper-portfolio logic. SQLite or PostgreSQL/psycopg persistence is supported. Frontend includes overview, convene, debate, risk, memo, portfolio, and backtest pages with Recharts.
- **Entry points and APIs:** FastAPI exposes health, universe, committee run, SSE committee stream, backtest, portfolio, daily job, and assistant endpoints. Frontend `npm run dev`; backend uvicorn. Deploy config targets Render; scheduled workflows are present.
- **Data models and evidence:** Pydantic schemas model mandate, evidence briefs, arguments, macro/risk view, decision, critique, transcript turns, status, and audit entries. Tool adapters fetch prices, SEC fundamentals, news, FRED macro, and snapshots. `grounding.py` validates quantitative claims against supplied evidence; output includes timestamps and tool/model audit data.
- **Committee/AI:** Five roles (research, bull, bear, macro, risk officer) orchestrated through debate, followed by portfolio manager synthesis and a critic, with capped rounds and risk veto. LLM router supports provider fallbacks and deterministic behavior. Strong architectural precedent, though its candidate screening and portfolio-weight decision are not the thesis-to-risk workflow. README states zero-key mode still fetches public data; that is not a fully offline deterministic demo.
- **Portfolio/quant:** Includes deterministic factor scoring, price/risk tools and point-in-time paper portfolio/backtest logic. Useful schema/orchestration concepts. It does not implement ETF look-through. Risk results are tied to its market-data routines and portfolio composition.
- **Visualization/config/tests/license:** Several polished Next.js pages, SSE debate UX, chart components and frontend utility components. Python requirements use broad minimum versions. Backend `.env.example` exists; frontend also contains `.env.development.local` (do not inspect or copy values). README has detailed setup/limits. No test files were found in the tracked file inventory. No license file found.
- **Strengths:** Best system design reference for typed committee output, live progress/transcript, evidence grounding/auditability, provider routing, and a modern frontend.
- **Weaknesses and compatibility:** No license grant; no tests found; public data makes its no-keys mode non-deterministic/offline-dependent; broader daily/paper portfolio product and candidate allocation are unnecessary; existing API and UI model different workflows.
- **Reuse decision:** Recreate those patterns without copying source: define RiskRoom-owned Pydantic schemas, structured agent roles and evidence records, deterministic demo mode, and trace IDs. Do not use its recommendations, paper portfolio, or any potential trading extensions.

### Stress-Testing-a-Markowitz-Portfolio

- **Stack and architecture:** Research Jupyter notebook with Python, pandas/NumPy, PyTorch, scikit-learn, pmdarima, `arch`, SciPy, yfinance, and Matplotlib. `requirements.txt` is a large notebook environment lock-style list with duplicate blocks and platform/GPU-specific packages.
- **Entry point/data:** One 2.5 MB notebook is the implementation. It downloads adjusted market history for SPY and NVDA from 2010 through May 2025; checked-in CSV files include price and train/test artifacts. README directs users to execute notebook cells in order. There is no reusable package/API, app, or storage layer.
- **Models/calculations:** Creates lagged returns and rolling covariance/variance targets, splits training through 2022, validation 2023, test 2024 onward, then trains an LSTM to forecast covariance and each asset's variance. It derives two-asset minimum-variance weights, simulates a portfolio, and estimates VaR/expected shortfall under Gaussian and skew-t distributions; the notebook also compares ARMA/GARCH alternatives and reports breach rates. The model is a specific NVDA/SPY pair research experiment, not a general Markowitz/scenario engine. Some outputs and conclusions are tied to an old date window and rely on downloaded historical data; results are not directly transferable to a current demo portfolio.
- **AI/UI/database/config/tests:** No LLM, web API, persistent database, product dashboard, or automated test suite. Charts are notebook plots. Reproducibility seeds NumPy and Torch, but environment/data downloads and large notebook outputs remain dependencies.
- **License:** No LICENSE/COPYING/NOTICE file found. README's “academic and educational purposes” statement is not an open-source reuse license. CSV data provenance/redistribution permission is unclear.
- **Strengths:** Explicit train/validation/test framing, VaR breach-rate evaluation, covariance-driven portfolio variance, and comparison of model families.
- **Weaknesses and compatibility:** Narrow two-asset universe, heavy training/runtime stack, research notebook rather than production code, stale period, and no license. Its predictions are not a substitute for deterministic user-defined stress shocks.
- **Reuse decision:** No code or CSV reuse. Use only as background for risk metric definitions and backtest caution. RiskRoom should use simple deterministic shocks with clearly stated assumptions and historical-return VaR/CVaR where local data supports it.

## Capability selection

| Capability | Foundation | Reason |
|---|---|---|
| Application architecture | New RiskRoom project | None of the source apps matches the integrated thesis → X-Ray → adversarial committee → stress workflow. |
| ETF decomposition and effective exposure | New, tested module informed conceptually by PortfolioOverlap | Closest source has no license, limited coverage, and incomplete market-value semantics. |
| Risk metrics | New deterministic module; use standard definitions and compare with AI-Portfolio-Intelligence-System and notebook references | Existing calculation modules are coupled to other systems; stress notebook is narrow and unlicensed. |
| Scenario stress engine | New deterministic module | Neither source has the generalized sector/issuer shock interface RiskRoom needs. |
| Agent orchestration/evidence trace | New structured orchestration informed conceptually by quorum | Best architecture reference, but no license and a different mandate. |
| User interface | New Next.js application | Only Quorum uses the target stack, but its components have no license and its workflows do not align. |
| Data/persistence providers | New interfaces and local seeded implementation; production Snowflake/TigerData adapters added behind those interfaces | Existing providers do not satisfy the target and demo reliability requirements. |

## Recommended RiskRoom architecture

Keep the target as a separate `riskroom/` app with one Next.js frontend and one FastAPI backend. Within the backend, use a small set of modules: Pydantic domain schemas; provider interfaces; portfolio/X-Ray service; deterministic risk/scenario service; committee service with typed claims and evidence references; report service; and adapters for seeded local data, OpenAI, Snowflake, and TigerData. Keep route handlers thin. Local deterministic demo fixtures must be the default and must not call the network.

The calculation boundary should be one-way: data and explicit assumptions feed deterministic exposure/risk/scenario calculations; LLMs may parse a thesis or scenario into validated structured inputs and explain already-computed results. Every numerical result shown to a model should be passed in as a cited value; generated numerical metrics must never be trusted or persisted as calculation output. Committee and scenario records need run IDs, timestamps, evidence/data provenance, assumptions, status and model/provider metadata. Reports and decision screens should show factual data, model outputs, AI interpretation, uncertainty, and human decision prompts as separate fields.

Use seeded ETF holdings/return series with stable deterministic values and visible as-of dates for the judging demo. Start with native local development (Python/FastAPI + Next.js), SQLite or file-backed local persistence, and environment-selected adapters. Add Snowflake and TigerData implementations without making their credentials required. Add optional OpenAI language synthesis and scenario parsing; keep quantitative calculations deterministic. Do not add trading, order placement, or buy/sell recommendations.

## Attribution and license follow-up

Before copying from any source, verify its license with the owner or add a license grant. For MIT-derived code, include the original copyright and MIT text in RiskRoom's third-party notices and preserve notices in source files where appropriate. Do not redistribute the ETF snapshots or notebook CSVs until their data source and redistribution terms are verified. Full source URLs and current decisions are recorded in `docs/THIRD_PARTY_NOTICES.md`.
