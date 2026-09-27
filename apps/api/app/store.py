"""Small local SQLite audit store used by the demo adapter."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _connect():
    path = Path(os.getenv("RISKROOM_SQLITE_PATH", "../../data/riskroom.sqlite"))
    if not path.is_absolute():
        path = (Path(__file__).resolve().parents[1] / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS committee_runs (run_id TEXT PRIMARY KEY, portfolio_id TEXT NOT NULL, thesis TEXT NOT NULL, status TEXT NOT NULL, input_json TEXT NOT NULL, output_json TEXT NOT NULL, created_at TEXT NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS agent_traces (run_id TEXT NOT NULL, agent TEXT NOT NULL, input_json TEXT NOT NULL, output_json TEXT NOT NULL, evidence_refs TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (run_id, agent))")
    connection.execute("CREATE TABLE IF NOT EXISTS scenario_runs (run_id TEXT PRIMARY KEY, portfolio_id TEXT NOT NULL, scenario_id TEXT NOT NULL, parameters_json TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL)")
    return connection


def save_committee(run_id: str, thesis: str, result: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as db:
        db.execute("INSERT OR REPLACE INTO committee_runs VALUES (?, ?, ?, ?, ?, ?, ?)", (run_id, "riskroom-demo", thesis, "completed", json.dumps({"thesis": thesis}), json.dumps(result), now))
        for agent in result["committee"]["agents"]:
            db.execute("INSERT OR REPLACE INTO agent_traces VALUES (?, ?, ?, ?, ?, ?, ?)", (run_id, agent["agent"], json.dumps({"thesis": thesis}), json.dumps(agent), json.dumps(agent.get("evidence", [])), "completed", now))


def save_scenario(run_id: str, portfolio_id: str, result: dict) -> None:
    with _connect() as db:
        db.execute("INSERT OR REPLACE INTO scenario_runs VALUES (?, ?, ?, ?, ?, ?)", (run_id, portfolio_id, result["id"], json.dumps(result.get("shocks", {})), json.dumps(result), datetime.now(timezone.utc).isoformat()))


def get_committee(run_id: str) -> dict | None:
    with _connect() as db:
        row = db.execute("SELECT output_json FROM committee_runs WHERE run_id = ?", (run_id,)).fetchone()
    return json.loads(row["output_json"]) if row else None
