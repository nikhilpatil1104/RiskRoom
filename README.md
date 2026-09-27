# RiskRoom

**Find the hidden risks. Challenge the thesis. Stress-test the future.**

RiskRoom is an educational and research-oriented investment decision room. It connects an investor's thesis to ETF look-through exposure, structured adversarial arguments, deterministic stress calculations, and a human decision checklist. It does not provide financial advice, guarantee outcomes, or execute trades.

## Current build

The separate `riskroom/` project contains a native Next.js frontend and FastAPI backend. It works without market-data keys or databases. With `ALPHA_VANTAGE_API_KEY` configured, the X-Ray and historical risk panels can use live ETF profiles and daily closes; if a symbol is rejected or a feed is limited, a fresh simulated price path keeps the jury submission working. Portfolio weights remain illustrative. Macro readings and ticker-filtered headlines are fetched where possible; missing context is generated as clearly labeled simulation. If `GEMINI_API_KEY` is configured, Gemini writes a thesis synthesis, parses structured scenario inputs, and creates hypothetical market headlines when real headlines are unavailable. It does not fetch current facts or calculate market data. The Thesis Tripwire panel links to Microsoft and NVIDIA SEC facts and filings when available; it produces changing simulated signals as a fallback. Five committee roles remain transparent rules, not live AI analysts.

The first end-to-end path is implemented: portfolio → X-Ray/overlap → committee → scenario impacts → report. Demo committee and scenario runs are stored in a local SQLite audit database. The Snowflake adapter has query methods and a matching schema contract; the TigerData adapter can persist committee/scenario runs. Those production adapters are not yet selected by the API workflow. Retrieved evidence for committee arguments and factor/geographic datasets remain follow-on work.

## Requirements

- Python 3.10 or newer
- Node.js 18.18 or newer and npm
- No Docker required
- API keys/databases are optional for demo mode

## Run locally

Terminal 1, from `riskroom/apps/api`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Optional: copy ../../.env.example to .env and add provider credentials
python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2, from `riskroom/apps/web`:

```powershell
npm install
npm run dev
```

Open <http://localhost:3000>. The API health check is at <http://localhost:8000/api/health> and interactive API docs are at <http://localhost:8000/docs>.

For non-PowerShell shells, activate the virtual environment with the platform's usual `source .venv/bin/activate` command. To use another API origin, copy `.env.example` to `.env.local` inside `apps/web` and set `NEXT_PUBLIC_API_URL` before starting Next.js. The API allows local development from port 3000 by default. Set `RISKROOM_ALLOWED_ORIGINS` to a comma-separated list of exact HTTPS frontend origins before production deployment.

## Demo workflow

1. Start both local services.
2. Use the seeded **AI Infrastructure Core** portfolio (VOO, QQQ, VGT, VTI, ARKK, TLT).
3. Enter the thesis: “I believe AI infrastructure spending will continue driving technology equities higher over the next two years. I am considering increasing my technology exposure.”
4. The deterministic briefing and seeded tripwires load on page open; edit the thesis and submit it to refresh the committee.
5. Review issuer signals, edit each invalidation threshold and hypothetical sector shock, then export a Tripwire Receipt.
6. Follow the exposure map and scenario library into the reverse stress lab to inspect the modeled portfolio impact.

Live prices are used when the vendor returns a usable series for every held ticker and SPY. Otherwise, the app generates new synthetic close paths, macro readings, and issuer signals per jury submission; the UI identifies these as simulated and they must not be treated as actual market or company data. Portfolio weights are still illustrative. Sector shock outputs are weighted sums of ETF sector exposure and editable scenario shocks. VaR/CVaR are empirical estimates from the selected sample, not forecasts. The $10,000 loss display is a hypothetical scale conversion.

## Optional providers

Copy `.env.example` to an API-local `.env` or set environment variables in the API process. Never put server keys in a `NEXT_PUBLIC_*` variable. Create an API key in [Google AI Studio](https://aistudio.google.com/apikey) and set `GEMINI_API_KEY`; the default model is `gemini-3.8-flash`, and `GEMINI_MODEL` can select another model available to your API project. The backend uses Google's official [Google GenAI Python SDK](https://ai.google.dev/gemini-api/docs/libraries).

To turn on the market panels, get a key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key), put it in `apps/api/.env`, and restart the FastAPI process:

```env
ALPHA_VANTAGE_API_KEY=your_key_here
SEC_USER_AGENT=RiskRoom/0.1 (you@your-domain.com)
```

- **Gemini:** `GEMINI_API_KEY` and optionally `GEMINI_MODEL`. Used for structured scenario input, narrative synthesis, and fresh hypothetical market headlines when live headlines are absent. Gemini is not a live market-data feed.
- **Alpha Vantage market data and evidence:** Get an API key from [Alpha Vantage](https://www.alphavantage.co/support/#api-key) and set `ALPHA_VANTAGE_API_KEY` in the API's `.env`. The API calls `ETF_PROFILE`, `TIME_SERIES_DAILY`, `TREASURY_YIELD`, `FEDERAL_FUNDS_RATE`, `CPI`, and `NEWS_SENTIMENT` where supported. When price or context endpoints reject a request, this run uses fresh generated simulation values and labels them as simulated. Alpha Vantage's default compact daily series returns up to 100 observations; this app uses unadjusted close prices, so dividends are excluded. See the [official API documentation](https://www.alphavantage.co/documentation/).
- **SEC EDGAR:** The SEC data API requires no API key ([official documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)); set `SEC_USER_AGENT` to identify your project and provide a real team contact email, for example `RiskRoom/0.1 (you@your-domain.com)`. The backend fetches issuer company facts with a short timeout and caches successful responses for one hour. When no filing value is returned, the panel supplies a changing, clearly labeled simulated tripwire reading and keeps the SEC links available.
- **Snowflake:** set account, user, password, database, schema, and warehouse. The adapter includes parameterized queries for historical prices, latest ETF holdings, macro observations, and text evidence search, but it is not wired into the normal API analysis routes. Apply `infrastructure/snowflake/001_initial.sql` to create its table contract.
- **TigerData:** set `TIGERDATA_DATABASE_URL`; the adapter can store committee and scenario runs. Apply `infrastructure/tigerdata/001_initial.sql` before connecting. The current API still records demo runs in its local SQLite audit store.

The seeded allocation VOO, QQQ, VGT, VTI, ARKK, and TLT remains illustrative until you provide actual tickers and weights or connect a brokerage through a user-authorized service such as [Plaid Investments](https://plaid.com/docs/investments/). Simulated readings and AI-generated headlines change by submission but are not live facts. Committee arguments and stress shocks remain transparent assumptions. SEC tripwires currently cover only Microsoft and NVIDIA. For additional macro history and revision-aware series, [FRED's observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) is an alternative requiring its own API key. Actual holdings, broader company coverage, longer dividend-adjusted price histories, and stress-event probabilities remain future data integrations.

Install both database adapter dependencies with `python -m pip install -r requirements-optional.txt` from `apps/api`.

## Architecture

```text
apps/web             Next.js, React, TypeScript, Tailwind, Recharts
apps/api/app         FastAPI routes, Pydantic schemas, demo/live services, optional AI calls
apps/api/app/demo_data.py
                     RiskRoom-owned synthetic ETF and return fixtures
apps/api/app/services.py
                     Deterministic look-through, overlap, risk and scenario math
apps/api/app/providers.py
                     Local, Alpha Vantage, Snowflake and TigerData adapter boundaries
apps/api/app/tripwires.py
                     Cached SEC issuer facts and explicitly labeled evidence fallbacks
infrastructure/      Provider schema notes and deployment assets
docs/                Repository audit and third-party notices
```

The critical boundary is `deterministic inputs ? quantitative services ? computed metrics ? optional Gemini explanation ? human decision`. SEC company facts are linked as evidence for editable issuer tripwires; they do not calculate portfolio returns. LLM output is never used as calculated return, VaR, CVaR, drawdown, or scenario impact. Gemini scenario output is constrained to the supported sector schema and decimal shock range before it is accepted.

## Data contracts and APIs

Pydantic domain records are in `apps/api/app/schemas.py`. Routes include `GET /api/health`, `GET /api/portfolios/demo`, `POST /api/portfolios`, `GET /api/portfolios/{id}`, `POST /api/xray/analyze`, `POST /api/thesis/analyze`, `POST /api/thesis/tripwires`, `POST /api/committee/run`, `GET /api/committee/{run_id}`, `GET /api/scenarios`, `POST /api/scenarios/generate`, `POST /api/scenarios/run`, `GET /api/risk/demo`, `POST /api/war-room/start`, `POST /api/reports/generate`.

## Testing

From `riskroom/apps/api`:

```powershell
python -m pytest
```

The tests cover exposure aggregation, overlap, scenario calculations, risk metrics, request validation, and the end-to-end War Room API path.

## Free Firebase + Render deployment

The free setup serves the statically exported Next.js frontend from Firebase Hosting on the Spark plan and runs FastAPI as a separate free Render web service. The frontend calls the API directly, so configure the API URL at build time and allow the Firebase origins through API CORS.

1. Push this repository to GitHub and create a Render Blueprint from it. Render reads `render.yaml` and creates the `riskroom-api` service. Set `RISKROOM_ALLOWED_ORIGINS` to both Firebase origins, for example `https://YOUR_PROJECT_ID.web.app,https://YOUR_PROJECT_ID.firebaseapp.com`. `GEMINI_API_KEY`, `ALPHA_VANTAGE_API_KEY`, and `SEC_USER_AGENT` are optional; add them in Render's environment settings if available.
2. Wait for the API service to deploy and copy its HTTPS URL from Render.
3. Install the Firebase CLI with `npm install -g firebase-tools`, authenticate with `firebase login`, and select the Firebase project with `firebase use --add`.
4. Build and deploy the frontend from the repository root in PowerShell:

   ```powershell
   cd apps/web
   $env:NEXT_PUBLIC_API_URL = "https://YOUR_RENDER_API.onrender.com"
   npm ci
   npm run build
   cd ../..
   firebase deploy --only hosting
   ```

   `next.config.mjs` writes the static export to `apps/web/out`, which `firebase.json` deploys.

Free-tier tradeoffs: Render spins the API down after 15 minutes without requests, so its first request after idle can take about a minute. Its filesystem is temporary, so the local SQLite audit history resets when the service restarts. Firebase Hosting includes 10 GB of storage and 10 GB/month of transfer on the no-cost plan; exceeding the transfer allowance can temporarily disable Hosting on Spark. Render also applies workspace-level free instance-hour and bandwidth limits.

For a custom domain, add its exact HTTPS origin to `RISKROOM_ALLOWED_ORIGINS` in Render and redeploy the frontend if the API URL changes.

## DigitalOcean deployment

For the hackathon scale, create two DigitalOcean App Platform services from the `riskroom` directory:

1. API web service: source directory `/apps/api`, build command `python -m pip install -r requirements.txt`, run command `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set the required server-side environment variables in App Platform. Configure CORS for the deployed frontend origin before exposing the API publicly.
2. Web service: source directory `/apps/web`, build command `npm ci && npm run build`, run command `npm start`. Set `NEXT_PUBLIC_API_URL` to the API's HTTPS origin at build time.
3. Add health checks at `/api/health`. Keep demo mode available if optional API credentials are absent.

DigitalOcean may require a monorepo build context rather than a service root; if so, use the project root as context and prefix each command with its app directory. Do not deploy the development CORS configuration as-is. No container is required by the local workflow.

## GoDaddy custom domain

Use the domain's DNS manager to add the record values shown by DigitalOcean for the frontend custom domain (typically a CNAME for `www` and an apex A/ALIAS record where supported). Add the domain in App Platform, wait for DNS validation and managed TLS issuance, then set the web service's `NEXT_PUBLIC_API_URL` to the API HTTPS domain and configure the API allowed origins to the exact frontend HTTPS origin. Avoid wildcard CORS in production.

## Source audit, notices, and disclaimer

See [`docs/repository-audit.md`](docs/repository-audit.md) and [`docs/THIRD_PARTY_NOTICES.md`](docs/THIRD_PARTY_NOTICES.md). The source repositories remain untouched. No code or data was copied from them because three have no license file and the data rights for the ETF snapshots/notebook CSVs are unclear.

> RiskRoom is an educational and research-oriented decision-support system. It does not provide financial advice, guarantee investment outcomes, or execute trades autonomously.
