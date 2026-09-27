-- Optional TigerData / TimescaleDB operational schema. Apply only when enabling persistence.
CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    time TIMESTAMPTZ NOT NULL,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    holding_ticker TEXT NOT NULL,
    weight DOUBLE PRECISION NOT NULL,
    market_value DOUBLE PRECISION,
    PRIMARY KEY (time, portfolio_id, holding_ticker)
);
CREATE TABLE IF NOT EXISTS risk_metrics (
    time TIMESTAMPTZ NOT NULL,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    method TEXT NOT NULL,
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (time, portfolio_id, metric_name)
);
CREATE TABLE IF NOT EXISTS committee_runs (
    run_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    thesis TEXT NOT NULL,
    status TEXT NOT NULL,
    trace JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS scenario_runs (
    run_id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    scenario_id TEXT NOT NULL,
    parameters JSONB NOT NULL,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS agent_decision_traces (
    time TIMESTAMPTZ NOT NULL,
    run_id TEXT NOT NULL REFERENCES committee_runs(run_id),
    agent TEXT NOT NULL,
    input JSONB NOT NULL,
    output JSONB NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    latency_ms INTEGER,
    status TEXT NOT NULL,
    PRIMARY KEY (time, run_id, agent)
);
-- Enable hypertables after installing TimescaleDB in the target database:
-- SELECT create_hypertable('portfolio_snapshots', 'time', if_not_exists => TRUE);
-- SELECT create_hypertable('risk_metrics', 'time', if_not_exists => TRUE);
-- SELECT create_hypertable('agent_decision_traces', 'time', if_not_exists => TRUE);
