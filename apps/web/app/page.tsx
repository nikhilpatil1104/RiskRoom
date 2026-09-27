"use client";

import { type CSSProperties, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, ArrowUpRight, Atom, Check, CircleHelp, Download, ExternalLink, FileText, Fingerprint, Layers3, Radio, RefreshCw, RotateCcw, Swords, TriangleAlert } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DISCLAIMER = "RiskRoom is educational decision support. Data provenance and portfolio assumptions are shown in each section. Stress scenarios are hypothetical, not forecasts or financial advice. No trades are executed.";
const INITIAL_THESIS = "AI infrastructure spending will keep driving technology equities higher over the next two years. I am considering increasing my technology exposure.";
type Holding = { ticker: string; weight: number; sector?: string; sources?: { etf: string; weight: number }[] };
type Scenario = { id: string; name: string; description: string; portfolio_return: number; estimated_loss_per_10000: number; shocks?: Record<string, number> };
type Agent = { agent: string; claim: string; evidence: string[]; risk_level: string; confidence: number | null };
type MacroObservation = { series: string; label: string; value: number; unit: string; observed_at: string; source: string; source_url: string };
type MarketNews = { title: string; url: string; source: string; published_at: string; summary: string; sentiment: string; sentiment_score: number | string | null; ticker?: string };
type Tripwire = { id: string; issuer: string; issuer_name: string; title: string; assumption: string; indicator: string; threshold_pct: number; threshold_label: string; shocks: Record<string, number>; observation: { latest_value_billions: number; growth_pct: number; period_end: string; filed: string; prior_period_end: string } | null; simulation: { latest_value_billions: number; growth_pct: number; period_end: string; filed: string; prior_period_end: string } | null; source_status: "live" | "simulated"; source_name: string; source_url: string; filings_url: string; caveat: string };
type TripwirePack = { items: Tripwire[]; provider: string; live_enabled: boolean; status: string; note: string; scope: string; thesis?: string };
type Payload = {
  run_id: string;
  portfolio: { name: string; holdings: Holding[] };
  xray: { technology_weight: number; concentration_top5: number; top_holdings: Holding[]; effective_holdings: Holding[]; sector_exposure: { sector: string; weight: number }[]; overlap_pairs: { left: string; right: string; shared_holdings_weight: number }[]; source: string };
  risk: { annualized_return: number; annualized_volatility: number; historical_var_95: number; historical_cvar_95: number; max_drawdown: number; max_drawdown_recovery_days: number | null; correlation_to_demo_market: number; correlation_to_benchmark?: number; benchmark_ticker?: string; latest_observation?: string | null; observations: number; source: string };
  scenarios: Scenario[];
  committee: { agents: Agent[]; evidence_quality: string; unresolved_questions: string[]; supporting_arguments: string[]; opposing_arguments: string[]; thesis_links: { assumption: string; threat: string; scenario_id: string }[]; human_decision: string };
  report: { disclaimer: string };
  data_status: { market_data_mode: "live" | "simulated" | "synthetic_demo"; market_data_source: string; portfolio_weight_source: string; market_context?: { macro: { observations: MacroObservation[]; unavailable: string[]; status: string }; news: { items: MarketNews[]; status: string }; generated_at?: string } };
  ai_summary?: string | null;
  mode: string;
};

const palette = ["#ee6545", "#d0ed72", "#71aaa3", "#a395c6", "#d5a84f", "#7190ac"];
const agentMarks: Record<string, string> = { Bull: "↑", Bear: "↓", Macro: "◌", "Risk Officer": "⌁", "Red Team": "×" };
const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const dollars = (value: number) => `$${Math.round(Math.abs(value)).toLocaleString("en-US")}`;

async function requestTripwires(thesis: string, holdings: Holding[]): Promise<TripwirePack> {
  const response = await fetch(`${API}/api/thesis/tripwires`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ thesis, holdings }) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "Tripwire evidence could not be loaded.");
  return result as TripwirePack;
}

function escapeHTML(value: string): string {
  const entities: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  return value.replace(/[&<>"']/g, char => entities[char] ?? char);
}

export default function Home() {
  const [thesis, setThesis] = useState(INITIAL_THESIS);
  const [data, setData] = useState<Payload | null>(null);
  const [health, setHealth] = useState(false);
  const [activeSection, setActiveSection] = useState("thesis");
  const initialAnchorRestored = useRef(false);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [selectedSector, setSelectedSector] = useState("Technology");
  const [sectorShock, setSectorShock] = useState(30);
  const [lossLimit, setLossLimit] = useState(10);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [tripwirePack, setTripwirePack] = useState<TripwirePack | null>(null);
  const [tripwireControls, setTripwireControls] = useState<Record<string, { threshold: number; severity: number }>>({});
  const [selectedTripwireId, setSelectedTripwireId] = useState<string | null>(null);
  const [tripwireBusy, setTripwireBusy] = useState(true);
  const [tripwireError, setTripwireError] = useState("");

  useEffect(() => {
    let alive = true;
    Promise.all([fetch(`${API}/api/war-room/demo`), fetch(`${API}/api/health`)]).then(async ([demo, status]) => {
      if (!demo.ok) {
        const issue = await demo.json().catch(() => ({}));
        throw new Error(issue.detail || `API request failed (${demo.status}).`);
      }
      const result = await demo.json();
      if (!alive) return;
      setData(result);
      setHealth(status.ok);
      const firstSector = result.xray.sector_exposure?.[0]?.sector;
      if (firstSector) setSelectedSector(firstSector);
      void requestTripwires(INITIAL_THESIS, result.portfolio.holdings).then(pack => {
        if (!alive) return;
        installTripwires(pack);
        setTripwireBusy(false);
      }).catch(error => {
        if (!alive) return;
        setTripwireError(error instanceof Error ? error.message : "Tripwire evidence could not be loaded.");
        setTripwireBusy(false);
      });
    }).catch(error => { if (alive) { setErr(error instanceof Error ? error.message : "Portfolio data could not be loaded."); setTripwireBusy(false); } });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    const sectionIds = ["thesis", "xray", "tripwires", "fracture-lab", "scenarios", "risk", "committee"];
    const observer = new IntersectionObserver(entries => {
      const current = entries.filter(entry => entry.isIntersecting).sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (current) setActiveSection(current.target.id);
    }, { rootMargin: "-18% 0px -68% 0px", threshold: [0, 0.1, 0.25, 0.5] });
    sectionIds.forEach(id => {
      const section = document.getElementById(id);
      if (section) observer.observe(section);
    });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!data || tripwireBusy || initialAnchorRestored.current) return;
    initialAnchorRestored.current = true;
    const targetId = window.location.hash.slice(1);
    if (!targetId) return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [data, tripwireBusy]);


  const sectors = data?.xray.sector_exposure ?? [];
  const selectedExposure = sectors.find(item => item.sector === selectedSector)?.weight ?? 0;
  const largestSector = sectors.reduce((largest, item) => item.weight > largest.weight ? item : largest, { sector: selectedSector, weight: selectedExposure });
  const lossLimitLabel = Number.isInteger(lossLimit) ? String(lossLimit) : lossLimit.toFixed(1);
  const estimatedImpact = selectedExposure * sectorShock / 100;
  const fractureShock = selectedExposure > 0 ? lossLimit / (selectedExposure * 100) : Infinity;
  const fracturePossible = fractureShock <= 1;
  const exposedNames = useMemo(() => (data?.xray.effective_holdings ?? []).filter(item => item.sector === selectedSector).sort((a, b) => b.weight - a.weight), [data, selectedSector]);
  const orderedScenarios = useMemo(() => [...(data?.scenarios ?? [])].sort((a, b) => a.portfolio_return - b.portfolio_return), [data]);
  const maxScenarioLoss = Math.max(0.01, ...orderedScenarios.map(item => Math.abs(item.portfolio_return)));

  async function refreshTripwires() {
    if (!data) return;
    setTripwireBusy(true); setTripwireError("");
    try {
      const pack = await requestTripwires(thesis, data.portfolio.holdings);
      installTripwires(pack);
    } catch (error) { setTripwireError(error instanceof Error ? error.message : "Tripwire evidence could not be refreshed."); }
    finally { setTripwireBusy(false); }
  }

  function tripwireImpact(item: Tripwire): number {
    const baseSeverity = Math.max(...Object.values(item.shocks).map(value => Math.abs(value)), 0.01);
    const severity = (tripwireControls[item.id]?.severity ?? baseSeverity * 100) / 100;
    const scale = severity / baseSeverity;
    return (data?.xray.sector_exposure ?? []).reduce((total, exposure) => total + exposure.weight * (item.shocks[exposure.sector] ?? 0) * scale, 0);
  }

  function tripwireStatus(item: Tripwire): string {
    const scenarioGrowth = item.simulation?.growth_pct ?? item.observation?.growth_pct;
    if (scenarioGrowth === undefined || scenarioGrowth === null) return "SIGNAL NOT SCORED";
    const threshold = tripwireControls[item.id]?.threshold ?? item.threshold_pct;
    const result = scenarioGrowth <= threshold ? "CROSSING" : scenarioGrowth <= threshold + 5 ? "NEAR LINE" : "ABOVE LINE";
    return result;
  }

  function installTripwires(pack: TripwirePack) {
    setTripwirePack(pack);
    setTripwireControls(Object.fromEntries(pack.items.map(item => [item.id, { threshold: item.threshold_pct, severity: Math.max(...Object.values(item.shocks).map(value => Math.abs(value))) * 100 }])));
    setSelectedTripwireId(null);
  }

  function exportTripwireReceipt(item: Tripwire) {
    const controls = tripwireControls[item.id] ?? { threshold: item.threshold_pct, severity: 0 };
    const impact = tripwireImpact(item);
    const observation = item.observation;
    const scenario = item.simulation ?? item.observation;
    const html = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RiskRoom Tripwire Receipt</title><style>body{margin:0;padding:48px;background:#efeee8;color:#202a27;font:16px Arial,sans-serif}.receipt{max-width:760px;margin:auto;padding:42px;background:#f8f7f2;border-top:9px solid #d1ee73;box-shadow:8px 8px 0 #d9d9cf}.kicker{font:11px monospace;letter-spacing:1px;color:#737b73}.brand{display:flex;justify-content:space-between;border-bottom:1px solid #d9d9cf;padding-bottom:18px}.brand b{font-size:18px;letter-spacing:2px}.signal{margin:32px 0 8px;color:#e86548;font:12px monospace}.title{font-size:34px;line-height:1.1;letter-spacing:-1px;margin:8px 0 20px}.thesis{font-size:18px;line-height:1.6;color:#4a554d}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:24px 0}.cell{padding:17px;background:#e9e9e1}.cell small{display:block;margin-bottom:9px;color:#737b73;font:10px monospace}.cell strong{font-size:22px}.loss{color:#b94430}.source{margin-top:24px;padding-top:17px;border-top:1px solid #d9d9cf;font-size:12px;line-height:1.7}a{color:#365e53;overflow-wrap:anywhere}.caveat{color:#737b73;font-size:11px;line-height:1.6;margin-top:18px}@media print{body{padding:0;background:white}.receipt{box-shadow:none;max-width:none}}</style><main class="receipt"><div class="brand"><b>RISKROOM / TRIPWIRE RECEIPT</b><span class="kicker">THESIS FRACTURE LAB</span></div><div class="signal">${escapeHTML(item.issuer)} · ${escapeHTML(tripwireStatus(item))}</div><h1 class="title">${escapeHTML(item.title)}</h1><p class="thesis">${escapeHTML(thesis)}</p><p>${escapeHTML(item.assumption)}</p><div class="grid"><div class="cell"><small>MODELED SCENARIO CHANGE - THIS SUBMISSION</small><strong>${scenario ? `${scenario.growth_pct > 0 ? "+" : ""}${scenario.growth_pct.toFixed(2)}%` : "?"}</strong></div><div class="cell"><small>INVESTOR-SET TRIPWIRE</small><strong>${escapeHTML(item.threshold_label)} ${controls.threshold.toFixed(0)}%</strong></div><div class="cell"><small>MODELED SECTOR STRESS</small><strong>−${controls.severity.toFixed(0)}%</strong></div><div class="cell"><small>PORTFOLIO IMPACT · $10,000 NOTIONAL</small><strong class="loss">−${dollars(-impact * 10000)}</strong></div></div><div class="source"><b>Indicator:</b> ${escapeHTML(item.indicator)}<br><b>Evidence source:</b> ${item.observation ? `${escapeHTML(item.source_name)} reported ${item.observation.growth_pct > 0 ? "+" : ""}${item.observation.growth_pct.toFixed(2)}% YoY` : "No issuer figure retrieved"}${observation ? ` · period ${escapeHTML(observation.period_end)} · ${item.observation ? `filed ${escapeHTML(observation.filed)}` : "scenario period"}` : ""}<br><a href="${escapeHTML(item.source_url)}">Open company facts</a> · <a href="${escapeHTML(item.filings_url)}">Open filings</a></div><p class="caveat">${escapeHTML(item.caveat)} Sector shocks are editable scenario assumptions, not forecasts. ${escapeHTML(data?.data_status.portfolio_weight_source ?? "Portfolio weights are illustrative.")} ${escapeHTML(data?.data_status.market_data_mode === "live" ? data.risk.source : "Scenario return model")} This receipt is educational decision support, not financial advice.</p><div class="kicker">RISKROOM · RESEARCH SYSTEMS</div></main></html>`;
    const file = new Blob([html], { type: "text/html" });
    const link = document.createElement("a"); link.href = URL.createObjectURL(file); link.download = `riskroom-tripwire-${item.id}.html`; link.click(); URL.revokeObjectURL(link.href);
  }

  async function runSynthesis() {
    if (!data) return;
    setBusy(true); setErr("");
    try {
      const response = await fetch(`${API}/api/war-room/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ thesis, holdings: data.portfolio.holdings }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Committee analysis could not be generated.");
      setData(result);
      setTripwireBusy(true);
      setTripwireError("");
      try {
        const pack = await requestTripwires(thesis, result.portfolio.holdings);
        installTripwires(pack);
      } catch (error) {
        setTripwireError(error instanceof Error ? error.message : "Tripwire context could not be refreshed.");
      } finally {
        setTripwireBusy(false);
      }
      document.getElementById("fracture-lab")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) { setErr(error instanceof Error ? error.message : "Committee analysis could not be generated."); }
    finally { setBusy(false); }
  }

  function exportBrief() {
    if (!data) return;
    const lines = ["RISKROOM / DECISION BRIEF", `Run: ${data.run_id}`, `Thesis: ${thesis}`, "", "LOOK-THROUGH", ...data.xray.sector_exposure.map(item => `${item.sector}: ${percent(item.weight)}`), "", "REVERSE STRESS", `${selectedSector} shock: -${sectorShock}%`, `Estimated portfolio impact: -${percent(estimatedImpact)}`, `Loss threshold: ${lossLimitLabel}%`, `Sector shock at threshold: ${fracturePossible ? `${percent(fractureShock)}` : "Not reachable by this sector alone"}`, "", "COMMITTEE", ...data.committee.agents.map(item => `${item.agent}: ${item.claim}`), "", "SCENARIO SET", ...data.scenarios.map(item => `${item.name}: ${percent(item.portfolio_return)}`), "", DISCLAIMER];
    const file = new Blob([lines.join("\n")], { type: "text/plain" });
    const link = document.createElement("a"); link.href = URL.createObjectURL(file); link.download = `riskroom-${data.run_id.toLowerCase()}.txt`; link.click(); URL.revokeObjectURL(link.href);
  }

  return <div className="workspace">
    <aside className="rail">
      <a className="brand" href="#top" aria-label="RiskRoom home"><span className="brand-glyph"><span>R</span><i/></span><span>RISK<br/>ROOM</span></a>
      <div className="rail-label">FIELD NOTES <span>01-06</span></div>
      <nav className="rail-nav" aria-label="Brief sections">
        <a className={activeSection === "thesis" ? "selected" : ""} aria-current={activeSection === "thesis" ? "location" : undefined} href="#thesis"><span>01</span> The thesis</a>
        <a className={activeSection === "xray" ? "selected" : ""} aria-current={activeSection === "xray" ? "location" : undefined} href="#xray"><span>02</span> Exposure map</a>
        <a className={activeSection === "tripwires" ? "selected" : ""} aria-current={activeSection === "tripwires" ? "location" : undefined} href="#tripwires"><span>03</span> Thesis tripwires</a>
        <a className={activeSection === "fracture-lab" ? "selected" : ""} aria-current={activeSection === "fracture-lab" ? "location" : undefined} href="#fracture-lab"><span>04</span> Fracture lab</a>
        <a className={activeSection === "scenarios" ? "selected" : ""} aria-current={activeSection === "scenarios" ? "location" : undefined} href="#scenarios"><span>05</span> Stress library</a>
        <a className={activeSection === "risk" || activeSection === "committee" ? "selected" : ""} aria-current={activeSection === "risk" || activeSection === "committee" ? "location" : undefined} href="#committee"><span>06</span> The jury</a>
      </nav>
      <div className="rail-bottom"><div className={`live-indicator ${health ? "online" : ""}`}><i/>{!health ? "CONNECTING" : data?.data_status.market_data_mode === "live" ? "LIVE PRICE FEED" : "SCENARIO MODE"}</div><p>{data?.data_status.market_data_mode === "live" ? <>Alpha Vantage<br/>daily closes</> : <>Scenario inputs<br/>refreshed each review</>}</p><div className="edition">R/R <span>RESEARCH SYSTEMS<br/>VOL. 01 / 2026</span></div></div>
    </aside>


    <main className="page" id="top">
      <header className="masthead"><div className="crumb">RISKROOM <span>/</span> INVESTMENT DECISION LAB</div><div className="masthead-right"><span className="signal"><Radio size={13}/> {data?.data_status.market_data_mode === "live" ? "LIVE PRICES · CONTEXT SOURCED" : "SCENARIO ANALYSIS · SOURCED CONTEXT"}</span><button className="export-button" onClick={exportBrief} disabled={!data}><Download size={14}/> EXPORT BRIEF</button></div></header>
      {err && <div className="error-banner" role="alert">{err}</div>}

      <section className="opening" id="thesis">
        <div className="opening-copy"><div className="overline"><span className="overline-mark"/> FIELD STUDY 001 <span className="overline-divider"/> THE CONVICTION TEST</div><h1>A thesis is only<br/>as strong as its<br/><em>breaking point.</em></h1><p className="opening-deck">Map what you own beneath the ticker. Push one assumption until the portfolio gives way. Find out what the headline risk is hiding.</p><div className="opening-foot"><span>DESIGNED FOR SKEPTICISM</span><span>LIVE · DETERMINISTIC · AUDITABLE</span></div></div>
        <div className="thesis-card"><div className="thesis-top"><div><span className="section-index">01 / THE CLAIM</span><h2>Put your conviction on trial.</h2></div><Fingerprint size={19}/></div><label className="sr-only" htmlFor="thesis-input">Investment thesis</label><textarea id="thesis-input" value={thesis} onChange={event => setThesis(event.target.value)} maxLength={600} placeholder="What do you believe, and what are you considering doing?"/><div className="thesis-bottom"><span>{thesis.length} / 600 · Clear, falsifiable claims work best.</span><button className="text-action" onClick={runSynthesis} disabled={busy || !data}>{busy ? "READING THE CASE…" : <>SUBMIT TO JURY <ArrowRight size={14}/></>}</button></div><div className="thesis-suggestions"><span>NEED A STARTING POINT?</span><div className="thesis-suggestion-list">{[
          { label: "AI spending slows", thesis: "If hyperscalers cut AI infrastructure spending by 20%, my technology-heavy portfolio could fall more than I expect." },
          { label: "Hidden mega-cap overlap", thesis: "My ETF holdings may hide too much exposure to the same mega-cap technology companies." },
          { label: "Rates stay higher", thesis: "Higher interest rates could make my long-duration growth holdings vulnerable." },
          { label: "AI demand, weak returns", thesis: "Strong AI demand may not translate into durable earnings for the companies I own." },
          { label: "Recession risk", thesis: "A recession could expose how much risk is concentrated in my current portfolio." },
        ].map(item => <button key={item.label} type="button" title={item.thesis} onClick={() => { setThesis(item.thesis); document.getElementById("thesis-input")?.focus(); }}>{item.label}</button>)}</div></div><div className="thesis-rule"><span>CLAIM</span><i/><span>EXPOSURE</span><i/><span>FRACTURE</span></div></div>
      </section>

      <section className="signal-strip"><div className="signal-stamp"><span>THE PORTFOLIO<br/>UNDER REVIEW</span><Atom size={19}/></div><div className="holding-stamps">{(data?.portfolio.holdings ?? []).map(item => <span key={item.ticker}>{item.ticker}<small>{percent(item.weight, 0)}</small></span>)}</div><div className="signal-caption"><span className="signal-dot"/>{health ? data?.data_status.market_data_mode === "live" ? "DAILY PRICE FEED CONNECTED" : "SCENARIO CONTEXT UPDATED" : "WAITING FOR LOCAL API"}<small>{data ? `${data.data_status.market_data_mode === "live" ? data.data_status.market_data_source : "Scenario model"} · ${data.data_status.portfolio_weight_source.includes("Seeded") ? "Illustrative portfolio weights" : data.data_status.portfolio_weight_source}` : "Waiting for portfolio source"}</small></div></section>

      <section className="section-block" id="xray">
        <SectionHeading number="02" eyebrow="LOOK THROUGH THE LABEL" title="The portfolio has a second face." note="ETF wrappers dissolve into their underlying companies. The same few names can appear in multiple funds."/>
        {!data ? <Loading /> : <div className="xray-layout">
          <div className="sector-board"><div className="board-meta"><span>EXPOSURE FINGERPRINT</span><span>100% TOTAL WEIGHT</span></div>{sectors.map((item, index) => <button key={item.sector} className={`sector-line ${selectedSector === item.sector ? "is-selected" : ""}`} onClick={() => { setSelectedSector(item.sector); document.getElementById("fracture-lab")?.scrollIntoView({ behavior: "smooth", block: "center" }); }}><span className="sector-name"><b>{String(index + 1).padStart(2, "0")}</b>{item.sector}</span><span className="sector-track"><i style={{ width: `${Math.min(item.weight / Math.max(...sectors.map(row => row.weight), 0.01) * 100, 100)}%`, background: palette[index % palette.length] }}/></span><span className="sector-number">{percent(item.weight)}</span><ArrowRight className="sector-arrow" size={14}/></button>)}<div className="fingerprint-foot"><span>SELECT A SECTOR TO TEST ITS BREAKING POINT ↗</span><span>{sectors.length} MATERIAL EXPOSURES</span></div></div>
          <div className="exposure-note"><div className="note-top"><span>UNWRAPPED / TOP POSITIONS</span><Layers3 size={17}/></div><p className="note-lede">Concentration lives<br/>under the surface.</p><div className="security-list">{data.xray.top_holdings.slice(0, 6).map((holding, index) => <div className="security-row" key={holding.ticker}><span className="security-rank">0{index + 1}</span><strong>{holding.ticker}</strong><span className="security-sector">{data.xray.effective_holdings.find(item => item.ticker === holding.ticker)?.sector}</span><b>{percent(holding.weight)}</b></div>)}</div><div className="overlap-note"><div><span>TOP FIVE ISSUERS</span><strong>{percent(data.xray.concentration_top5)}</strong></div><div className="overlap-mini"><span>of the whole portfolio</span><span>{data.xray.overlap_pairs.length} fund pairs checked</span></div></div><p className="source-note">{data.xray.source}</p></div>
        </div>}
      </section>

      <section className="tripwire-section" id="tripwires">
        <div className="tripwire-heading"><div><span className="section-index">03 / FALSIFIABLE BY DESIGN</span><h2>What would make<br/>you <em>change your mind?</em></h2></div><div className="tripwire-heading-side"><p>SEC-reported issuer facts appear when available. Otherwise, explore a modeled scenario for each thesis signal and adjust its tripwire controls.</p><div className={`source-mode ${tripwirePack?.live_enabled ? "source-live" : ""}`}><i/>{tripwirePack?.live_enabled ? "SEC FACTS + SCENARIO MODEL" : "MODELED SCENARIOS · SEC LINKS RETAINED"}</div></div></div>
        <div className="tripwire-toolbar"><div><span className="tripwire-count">{tripwirePack?.items.length ?? 0} THESIS SIGNALS</span><span className="tripwire-scope">Issuer proxies update when you submit the thesis.</span></div><button className="refresh-source" onClick={refreshTripwires} disabled={tripwireBusy || !tripwirePack} title="Fetch available SEC facts or refresh the modeled scenario"><RefreshCw size={13}/>{tripwireBusy ? "UPDATING…" : tripwirePack?.live_enabled ? "REFRESH SEC / SCENARIO" : "REFRESH SCENARIO"}</button></div>
        {tripwireError && <div className="tripwire-error" role="status">{tripwireError}</div>}
        {tripwireBusy && !tripwirePack ? <Loading/> : <div className="tripwire-grid">{(tripwirePack?.items ?? []).map((item, index) => {
          const controls = tripwireControls[item.id] ?? { threshold: item.threshold_pct, severity: Math.max(...Object.values(item.shocks).map(value => Math.abs(value))) * 100 };
          const impact = tripwireImpact(item);
          const observation = item.observation;
          const scenario = item.simulation ?? item.observation;
          const status = tripwireStatus(item);
          const dominant = Object.entries(item.shocks).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0];
          return <article className={`tripwire-card ${selectedTripwireId === item.id ? "tripwire-selected" : ""}`} key={item.id}>
            <div className="tripwire-card-top"><span>TRIPWIRE / 0{index + 1}</span><span className={`tripwire-status ${status === "CROSSING" ? "status-hit" : status === "NEAR LINE" ? "status-watch" : status === "ABOVE LINE" ? "status-clear" : "status-simulated"}`}><i/>{status}</span></div>
            <div className="tripwire-issuer">{item.issuer} <span>· {item.issuer_name}</span></div><h3>{item.title}</h3><p className="tripwire-assumption">{item.assumption}</p>
            <div className="evidence-source"><div className="evidence-source-title"><span>{observation ? "SCENARIO ESTIMATE / SEC FIGURE BELOW" : "SCENARIO ESTIMATE / SEC SOURCE LINKED"}</span><a className="evidence-source-link" href={item.source_url || item.filings_url} target="_blank" rel="noreferrer" aria-label={`Open SEC company facts for ${item.issuer_name}`} title="Open SEC company facts"><ExternalLink size={13}/></a></div><p className="evidence-indicator">{item.indicator}</p><div className="evidence-reading"><strong className="reading-simulated">{scenario ? `${scenario.growth_pct > 0 ? "+" : ""}${scenario.growth_pct.toFixed(1)}%` : "PENDING"}</strong><span><b>THIS SUBMISSION · MODELED GROWTH</b>{observation ? <small>SEC reported: {observation.growth_pct > 0 ? "+" : ""}{observation.growth_pct.toFixed(1)}% YoY · ended {observation.period_end} · filed {observation.filed}</small> : <small>Issuer filing figure unavailable for this signal.</small>}</span></div><div className="evidence-links"><a href={item.source_url} target="_blank" rel="noreferrer">Company facts <ExternalLink size={11}/></a><a href={item.filings_url} target="_blank" rel="noreferrer">Filing history <ExternalLink size={11}/></a></div></div>
            <div className="tripwire-controls"><label><span>INVALIDATE IF GROWTH</span><b>{controls.threshold > 0 ? "+" : ""}{controls.threshold}%</b><input aria-label={`${item.issuer} invalidation threshold`} type="range" min="-50" max="50" step="1" value={controls.threshold} onChange={event => setTripwireControls(current => ({ ...current, [item.id]: { ...controls, threshold: Number(event.target.value) } }))}/></label><label><span>MODELED STRESS SEVERITY</span><b>−{controls.severity}%</b><input aria-label={`${item.issuer} stress severity`} type="range" min="5" max="60" step="1" value={controls.severity} onChange={event => setTripwireControls(current => ({ ...current, [item.id]: { ...controls, severity: Number(event.target.value) } }))}/></label></div>
            <div className="tripwire-consequence"><span>IF TRIGGERED · HYPOTHETICAL $10K</span><strong><b>−{percent(Math.abs(impact))}</b><i/>−{dollars(-impact * 10000)}</strong></div>
            <p className="tripwire-caveat">{item.caveat} Stress assumptions are editable and do not imply causality.</p>
            <div className="tripwire-actions"><button className="tripwire-test" onClick={() => { setSelectedTripwireId(item.id); if (dominant) setSelectedSector(dominant[0]); setSectorShock(controls.severity); setActiveScenario(null); document.getElementById("fracture-lab")?.scrollIntoView({ behavior: "smooth", block: "start" }); }}>TEST DOMINANT SECTOR <ArrowRight size={13}/></button><button className="receipt-button" onClick={() => exportTripwireReceipt(item)}><FileText size={13}/> EXPORT RECEIPT</button></div>
          </article>;
        })}</div>}
        <p className="tripwire-footnote"><CircleHelp size={13}/><span>These indicators are narrow issuer proxies. A revenue or CapEx change does not prove or disprove the whole thesis. Live values come from SEC company facts; each link opens the underlying public record.</span></p>
      </section>

      <section className="fracture-section" id="fracture-lab">
        <div className="fracture-header"><div><div className="section-index light-index">04 / REVERSE STRESS ENGINE</div><h2>Find the point<br/>where it <em>breaks.</em></h2><p>Set the loss you cannot accept. RiskRoom solves for the sector shock that reaches it, then shows which holdings carry the damage.</p></div><div className="fracture-orbit" aria-hidden="true"><div className="orbit-ring ring-a"/><div className="orbit-ring ring-b"/><div className="orbit-center"><span>RISK<br/>LIMIT</span><strong>{lossLimitLabel}%</strong></div><span className="orbit-label orbit-top">ASSUMPTION</span><span className="orbit-label orbit-side">PORTFOLIO</span></div></div>
        {!data ? <Loading light/> : <div className="fracture-grid">
          <div className="fracture-controls"><div className="control-block"><div className="control-label"><span>01 / CHOOSE A SECTOR</span><span>{percent(selectedExposure)} OF PORTFOLIO</span></div><div className="sector-picker">{sectors.map(item => <button key={item.sector} onClick={() => setSelectedSector(item.sector)} className={selectedSector === item.sector ? "active" : ""}>{item.sector}</button>)}</div></div>
            <div className="control-block range-block"><div className="control-label"><label htmlFor="shock-slider">02 / IMAGINE ITS DECLINE</label><b className="shock-value">−{sectorShock}%</b></div><input id="shock-slider" className="range-input" type="range" min="0" max="100" step="1" value={sectorShock} onChange={event => { setSectorShock(Number(event.target.value)); setActiveScenario(null); }} style={{ "--range-progress": `${sectorShock}%` } as CSSProperties}/><div className="range-captions"><span>NO SHOCK</span><span>−100% SECTOR RETURN</span></div></div>
            <div className="control-block range-block limit-block"><div className="control-label"><label htmlFor="limit-slider">03 / SET YOUR LOSS LIMIT</label><b className="limit-value">{lossLimitLabel}%</b></div><input id="limit-slider" className="range-input limit-range" type="range" min="0.1" max="25" step="0.1" value={lossLimit} onChange={event => setLossLimit(Number(event.target.value))} style={{ "--range-progress": `${(lossLimit - 0.1) / 24.9 * 100}%` } as CSSProperties}/><div className="range-captions"><span>0.1% OF PORTFOLIO</span><span>25% OF PORTFOLIO</span></div></div>
          </div>
          <div className="fracture-result"><div className="result-cap"><span>{fracturePossible ? "YOUR FRACTURE POINT" : "MAX LOSS FROM THIS SECTOR"}</span><span className="result-live"><i/> RE-CALCULATES LIVE</span></div>{fracturePossible ? <><div className="result-number">−{(fractureShock * 100).toFixed(1)}<small>%</small></div><p className="result-desc">A <b>{selectedSector}</b> drawdown of this size would reach your portfolio loss limit of <b>{lossLimitLabel}%</b>, assuming other sectors hold flat.</p></> : <><div className="result-number result-impossible">−{percent(selectedExposure)}</div><p className="result-desc">Even a total loss in <b>{selectedSector}</b> (currently {percent(selectedExposure)} of your portfolio) would stay below your {lossLimitLabel}% limit. Try a larger exposure or lower the limit.</p>{largestSector.sector !== selectedSector && <button className="fracture-suggestion" onClick={() => setSelectedSector(largestSector.sector)}>TEST LARGEST EXPOSURE · {largestSector.sector} ({percent(largestSector.weight)}) <ArrowRight size={12}/></button>}</>}<div className="impact-rule"><span>AT CURRENT SHOCK · −{sectorShock}%</span><strong>PORTFOLIO IMPACT <b>−{percent(estimatedImpact)}</b></strong></div><div className="impact-track"><i style={{ width: `${Math.min(estimatedImpact / (lossLimit / 100) * 100, 100)}%` }}/><span style={{ left: `${Math.min(estimatedImpact / (lossLimit / 100) * 100, 100)}%` }}/></div><div className="impact-foot"><span>0% LOSS</span><span>LIMIT {lossLimitLabel}%</span></div><div className="notional-box"><span>ON A HYPOTHETICAL $10,000 PORTFOLIO</span><strong>−{dollars(estimatedImpact * 10000)}</strong></div></div>
          <div className="fracture-underneath"><div className="underneath-cap"><span>WHERE THE SHOCK LANDS</span><span>{selectedSector.toUpperCase()} EXPOSURE</span></div><div className="underneath-list">{exposedNames.slice(0, 5).map((holding, index) => <div className="underneath-row" key={holding.ticker}><span className="underneath-index">{String(index + 1).padStart(2, "0")}</span><strong>{holding.ticker}</strong><span className="underneath-bar"><i style={{ width: `${Math.min(holding.weight / Math.max(selectedExposure, 0.001) * 100, 100)}%` }}/></span><span className="underneath-weight">{percent(holding.weight)}</span><span className="underneath-loss">−{dollars(holding.weight * sectorShock / 100 * 10000)}</span></div>)}{!exposedNames.length && <p className="empty-underneath">No mapped look-through names in this exposure.</p>}</div><div className="underneath-foot"><span>COMPANY EXPOSURE AS SHARE OF PORTFOLIO</span><span>EST. LOSS AT CURRENT SHOCK</span></div></div>
        </div>}
        <div className="method-note"><CircleHelp size={14}/><span><b>How to read this:</b> this is a one-factor reverse stress, not a forecast. We multiply each fund’s look-through sector weight by the shock you set. Other sectors are held flat; real markets do not move one variable at a time.</span></div>
      </section>

      <section className="section-block" id="scenarios">
        <SectionHeading number="05" eyebrow="FIVE WAYS THE STORY CAN TURN" title="Pressures already in the room." note="Select a stress to load its dominant sector into the fracture lab. All impacts use the same deterministic exposure arithmetic."/>
        {!data ? <Loading/> : <div className="scenario-grid">{orderedScenarios.map((scenario, index) => { const loss = Math.abs(scenario.portfolio_return); const sector = Object.entries(scenario.shocks ?? {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))[0]; const isActive = activeScenario === scenario.id; return <button className={`scenario-card ${isActive ? "scenario-active" : ""}`} key={scenario.id} onClick={() => { if (sector) { setSelectedSector(sector[0]); setSectorShock(Math.round(Math.abs(sector[1]) * 100)); setActiveScenario(scenario.id); document.getElementById("fracture-lab")?.scrollIntoView({ behavior: "smooth", block: "center" }); } }}><div className="scenario-meta"><span>SCENARIO / 0{index + 1}</span>{isActive ? <Check size={15}/> : <ArrowUpRight size={15}/>}</div><h3>{scenario.name}</h3><p>{scenario.description}</p><div className="scenario-bar"><i style={{ width: `${Math.max(3, loss / maxScenarioLoss * 100)}%` }}/></div><div className="scenario-impact"><strong>{scenario.portfolio_return < 0 ? "−" : "+"}{percent(loss)}</strong><span>{scenario.portfolio_return < 0 ? "PORTFOLIO LOSS" : "PORTFOLIO GAIN"}</span></div><div className="scenario-dollar">{scenario.portfolio_return < 0 ? "−" : "+"}{dollars(scenario.estimated_loss_per_10000)} <small>per $10k</small></div></button>; })}</div>}
        <p className="scenario-footnote"><TriangleAlert size={13}/> Shocks are constructed teaching scenarios. They do not represent market forecasts or probabilities.</p>
      </section>

      <section className="quant-section" id="risk">
        <div className="quant-intro"><span className="section-index">QUANTITATIVE RECORD / {data?.risk.observations ?? "—"} {data?.data_status.market_data_mode === "live" ? "OBSERVED" : "MODELED"} SESSIONS</span><h2>Numbers with<br/>their provenance.</h2><p>{data?.data_status.market_data_mode === "live" ? `Risk metrics use observed daily closes through ${data.risk.latest_observation ?? "the latest available session"}. Portfolio weights are illustrative.` : "A scenario return path is refreshed with each jury review. Risk metrics are model outputs based on that path."}</p><span className="quant-source">{data?.data_status.market_data_mode === "live" ? data.risk.source : "Scenario return model"}</span></div>
        {!data ? <Loading/> : <div className="quant-board"><Metric label="Annualized volatility" value={percent(data.risk.annualized_volatility)} context={data.data_status.market_data_mode === "live" ? "observed daily close returns" : "scenario return path"}/><Metric label="Historical VaR · 95%" value={percent(data.risk.historical_var_95)} context="empirical tail of this run's sample"/><Metric label="Historical CVaR · 95%" value={percent(data.risk.historical_cvar_95)} context="worst 5% of this run's sample"/><Metric label="Maximum drawdown" value={percent(data.risk.max_drawdown)} context={data.risk.max_drawdown_recovery_days === null ? "not recovered in this sample" : `recovery · ${data.risk.max_drawdown_recovery_days} sessions`}/><div className="quant-bottom"><span>ANNUALIZED RETURN <b>{percent(data.risk.annualized_return)}</b></span><span>{data.risk.benchmark_ticker ?? "MODELED BENCHMARK"} CORRELATION <b>{(data.risk.correlation_to_benchmark ?? data.risk.correlation_to_demo_market).toFixed(2)}</b></span><span>OBSERVATIONS <b>{data.risk.observations}</b></span></div></div>}
      </section>

      <section className="jury-section" id="committee">
        <SectionHeading number="06" eyebrow="ADVERSARIAL REVIEW / EXPLICIT ASSUMPTIONS" title="Five lenses. One fragile story." note="Each role applies a distinct challenge to portfolio exposures. Macro readings and headlines are retrieved evidence; shocks and committee arguments remain transparent rules, not analyst research."/>
        {!data ? <Loading/> : <><div className="market-evidence" aria-label="Market readings and thesis scenarios"><div className="market-evidence-head"><span>MARKET CONTEXT / SOURCE-LABELED</span><span>{data.data_status.market_context?.macro.status !== "live" || data.data_status.market_context?.news.status !== "live" ? "SCENARIO CONTEXT REFRESHED" : "LATEST PROVIDER OBSERVATIONS"}</span></div><div className="macro-reading-list">{(data.data_status.market_context?.macro.observations ?? []).map(item => <a className="macro-reading" href={item.source_url || undefined} target={item.source_url ? "_blank" : undefined} rel={item.source_url ? "noreferrer" : undefined} key={item.series}><span>{item.label.replace(/^Simulated /, "Scenario · ")}</span><strong>{item.value.toFixed(2)}{item.unit === "%" ? "%" : item.unit === "index" ? " index" : ""}</strong><small>{item.observed_at} · {item.source.includes("simulation") ? "Scenario estimate" : item.source}</small></a>)}{!data.data_status.market_context?.macro.observations.length && <p className="evidence-empty">No context readings available for this review.</p>}</div><div className="headline-list">{(data.data_status.market_context?.news.items ?? []).map((item, index) => <a className="headline-item" href={item.url || undefined} target={item.url ? "_blank" : undefined} rel={item.url ? "noreferrer" : undefined} key={`${item.url || item.title}-${index}`}><span>{item.ticker ? `${item.ticker} · ` : ""}{item.url ? item.source : "Scenario"} · {item.published_at || "this review"}</span><strong>{item.title.replace(/^Simulation: /, "Scenario: ")}</strong><small>{item.sentiment}{item.url ? " · open source" : " · modeled case"}</small></a>)}</div><p className="evidence-caveat">{data.data_status.market_context?.macro.status !== "live" || data.data_status.market_context?.news.status !== "live" ? "Modeled readings and headlines are scenario estimates. Provider observations link to their sources; scenario values are estimates, not market reports." : "Provider readings are context, not proof of causation. Stress shocks remain hypothetical."}</p></div><div className="jury-grid">{data.committee.agents.map((agent, index) => <article className={`juror juror-${index}`} key={agent.agent}><div className="juror-top"><span className="juror-mark">{agentMarks[agent.agent] ?? "·"}</span><span>VOICE / 0{index + 1}</span></div><h3>{agent.agent}</h3><p>{agent.claim}</p><div className="juror-evidence"><span>GROUNDING</span>{agent.evidence[0] ?? "No external evidence connected."}</div><div className="juror-risk"><span>RISK POSTURE</span><b>{agent.risk_level.toUpperCase()}</b></div></article>)}</div><div className="counterfactual"><div className="counterfactual-title"><Swords size={17}/><span>THE RED TEAM’S COUNTERFACTUAL</span></div><div className="counterfactual-body"><span>IF THIS THESIS IS WRONG, WHAT WOULD WE OBSERVE?</span><p>{data.committee.unresolved_questions[0]}</p><p>{data.committee.unresolved_questions[1]}</p></div></div></>}
      </section>

      <footer className="footer"><div className="footer-brand"><span className="brand-glyph small-glyph"><span>R</span><i/></span><span>RISKROOM <small>RESEARCH SYSTEMS / 2026</small></span></div><p>{DISCLAIMER}</p><button className="back-top" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>BACK TO OPENING <ArrowUpRight size={13}/></button></footer>
    </main>
  </div>;
}

function SectionHeading({ number, eyebrow, title, note }: { number: string; eyebrow: string; title: string; note: string }) {
  return <div className="section-heading"><div className="section-heading-main"><span className="section-index">{number} / {eyebrow}</span><h2>{title}</h2></div><p>{note}</p></div>;
}

function Loading({ light = false }: { light?: boolean }) { return <div className={`loading-block ${light ? "loading-light" : ""}`}><span className="loading-mark"><RotateCcw size={15}/></span><span>LOADING PORTFOLIO RECORD</span></div>; }

function Metric({ label, value, context }: { label: string; value: string; context: string }) { return <div className="quant-metric"><span>{label}</span><strong>{value}</strong><small>{context}</small></div>; }
