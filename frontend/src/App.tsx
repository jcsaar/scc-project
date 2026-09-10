import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BookOpenCheck,
  Boxes,
  Braces,
  CheckCircle2,
  ChevronRight,
  CircleGauge,
  Cloud,
  Database,
  KeyRound,
  LayoutDashboard,
  LockKeyhole,
  MessageSquareText,
  Network,
  Play,
  RotateCcw,
  ServerCog,
  ShieldCheck,
  ShieldX,
  Sparkles,
  UserRound,
} from "lucide-react";
import { getLedger, getPolicy, runScenario, runWorkflow, updatePolicy } from "./api";
import type {
  DemoMode,
  LedgerClaim,
  Policy,
  ScenarioResult,
  ViewName,
  WorkflowResult,
} from "./types";
import "./styles.css";

const views: Array<{ label: ViewName; icon: typeof Activity }> = [
  { label: "Chat", icon: MessageSquareText },
  { label: "Privacy Pipeline", icon: Network },
  { label: "Collaboration", icon: Boxes },
  { label: "Privacy Dashboard", icon: LayoutDashboard },
  { label: "Exposure Ledger", icon: Database },
  { label: "Admin / Policy", icon: ServerCog },
];

const preview: WorkflowResult = {
  mode: "trustsplit",
  final_answer:
    "Use a horizontally partitioned SQL design with synchronous replication for the critical write path. Validate at 20k TPS and preserve strong consistency for account updates.",
  outbound_payload: {
    provider_name: "Mock Cloud",
    trust_zone_id: "company_cloud",
    disclosures: [
      {
        text: "Design a strongly consistent transaction system for 15k–20k TPS using a clustered relational database and an account-based partitioning key.",
        category: "architecture.capacity",
        precision: "bounded_range",
        fact_keys: ["throughput.capacity", "consistency.requirement", "partition.strategy"],
      },
    ],
  },
  session_budget_remaining: 82,
  broker_decision: {
    decision: "generalise",
    reason_code: "minimum_useful_precision",
    reason: "Exact operating figures were replaced with the minimum useful bounded range.",
    released_text: "15k–20k TPS",
    released_precision: "bounded_range",
    risk_before: 18,
    risk_after: 31,
    disclosure_delta: 13,
    budget_cost: 18,
  },
  exposure_summary: "3 safe claims · exact identifiers withheld",
  events: [
    { sequence: 1, state: "receive_prompt", actor: "employee", safe_summary: "Private prompt received locally." },
    { sequence: 2, state: "local_analysis", actor: "local_ai", safe_summary: "Private context analysed inside the local zone." },
    { sequence: 3, state: "broker_validate_outbound", actor: "privacy_broker", safe_summary: "Exact details generalised before release." },
    { sequence: 4, state: "cloud_reasoning", actor: "cloud_ai", safe_summary: "Cloud reasoned only over the approved payload." },
    { sequence: 5, state: "cloud_request_context", actor: "cloud_ai", safe_summary: "Cloud requested one Boolean constraint." },
    { sequence: 6, state: "broker_validate_response", actor: "privacy_broker", safe_summary: "Oracle answer independently checked." },
    { sequence: 7, state: "local_verify", actor: "local_ai", safe_summary: "Recommendation verified against hidden constraints." },
    { sequence: 8, state: "final", actor: "local_ai", safe_summary: "Final locally verified answer ready." },
  ],
};
preview.outbound_payloads = preview.outbound_payload ? [preview.outbound_payload] : [];

const scenarioCards = [
  { id: "legitimate", name: "Legitimate collaboration", description: "A safe Boolean oracle answer improves the cloud recommendation." },
  { id: "mosaic", name: "Cross-employee mosaic", description: "Four employees gradually reveal related attributes to one trust zone." },
  { id: "malicious_cloud", name: "Malicious narrowing", description: "A cloud model repeatedly narrows its requests until the broker denies it." },
];

function ZoneBadge({ kind, children }: { kind: "local" | "broker" | "cloud"; children: React.ReactNode }) {
  return <span className={`zone-badge ${kind}`}>{children}</span>;
}

function Metric({ label, value, note, tone = "cyan" }: { label: string; value: string; note: string; tone?: "cyan" | "amber" | "violet" }) {
  return (
    <article className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

function ChatView({ result, onResult }: { result: WorkflowResult; onResult: (value: WorkflowResult) => void }) {
  const [prompt, setPrompt] = useState("Review Project Aurora's transaction architecture and recommend a safe scale-out design.");
  const [mode, setMode] = useState<DemoMode>("trustsplit");
  const [provider, setProvider] = useState("company_cloud");
  const [employee, setEmployee] = useState("alice");
  const [status, setStatus] = useState<"idle" | "running" | "error">("idle");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setStatus("running");
    setError("");
    try {
      onResult(await runWorkflow({ employeeId: employee, mode, provider, prompt }));
      setStatus("idle");
    } catch (caught) {
      setStatus("error");
      setError(caught instanceof Error ? caught.message : "The run could not be completed.");
    }
  }

  return (
    <div className="workspace-grid">
      <section className="panel conversation-panel">
        <div className="panel-heading">
          <div><span className="eyebrow">Private workspace</span><h2>Architecture review</h2></div>
          <ZoneBadge kind="local">Local Private Zone</ZoneBadge>
        </div>
        <div className="message employee-message"><UserRound size={17} /><div><b>Employee prompt</b><p>{prompt}</p></div></div>
        <div className="message answer-message"><ShieldCheck size={17} /><div><b>Locally verified response</b><p>{result.final_answer}</p></div></div>
        <form onSubmit={submit} className="composer">
          <label htmlFor="prompt">Private prompt</label>
          <textarea id="prompt" value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          <div className="control-row">
            <label>Employee<select value={employee} onChange={(event) => setEmployee(event.target.value)}><option value="alice">Alice</option><option value="bob">Bob</option><option value="charlie">Charlie</option><option value="dana">Dana</option></select></label>
            <label>Mode<select aria-label="Mode" value={mode} onChange={(event) => setMode(event.target.value as DemoMode)}><option value="trustsplit">TrustSplit</option><option value="cloud_only">Cloud Only</option><option value="local_only">Local Only</option><option value="basic_redaction">Basic Redaction</option></select></label>
            <label>Provider<select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="company_cloud">Company Cloud</option><option value="personal_cloud">Personal Cloud</option></select></label>
            <button className="primary-button" type="submit" disabled={status === "running"}><Play size={16} />{status === "running" ? "Mediating…" : "Run safely"}</button>
          </div>
          {error && <p className="error-text" role="alert">{error}</p>}
        </form>
      </section>
      <aside className="right-stack">
        <section className="panel compact-panel">
          <div className="panel-heading"><div><span className="eyebrow">Outbound evidence</span><h3>What the cloud received</h3></div><ZoneBadge kind="cloud">Cloud Zone</ZoneBadge></div>
          <p className="payload-preview">{result.outbound_payload?.disclosures[0]?.text ?? "Nothing left the device in Local Only mode."}</p>
          <div className="decision-strip"><span>Broker decision</span><strong>{result.broker_decision.decision.toUpperCase()}</strong></div>
        </section>
        <section className="panel invariant-card"><LockKeyhole size={22} /><div><span className="eyebrow">System invariant</span><p>Cloud AI never directly accesses private corporate data.</p></div></section>
      </aside>
    </div>
  );
}

function PipelineView({ result }: { result: WorkflowResult }) {
  const decision = result.broker_decision;
  const payloads = result.outbound_payloads?.length
    ? result.outbound_payloads
    : result.outbound_payload
      ? [result.outbound_payload]
      : [];
  return (
    <div className="pipeline-layout">
      <section className="pipeline-rail" aria-label="Privacy zones">
        <article className="zone-column local-zone"><div className="zone-icon"><LockKeyhole /></div><span className="eyebrow">Zone 01</span><h3>Local Private</h3><p>Prompt, source documents, exact facts, verification constraints.</p><ul><li>Private repository</li><li>Local AI</li><li>Local oracle</li></ul></article>
        <ChevronRight className="flow-arrow" />
        <article className="zone-column broker-zone"><div className="zone-icon"><ShieldCheck /></div><span className="eyebrow">Zone 02</span><h3>Privacy Broker</h3><p>Hard rules, precision, cumulative risk, and session budget.</p><div className="decision-big">{decision.decision.toUpperCase()}</div><small>{decision.reason_code.replaceAll("_", " ")}</small></article>
        <ChevronRight className="flow-arrow" />
        <article className="zone-column cloud-zone"><div className="zone-icon"><Cloud /></div><span className="eyebrow">Zone 03</span><h3>Cloud Reasoning</h3><p>Receives only the immutable broker-approved envelope.</p><ul><li>No repository access</li><li>No credentials in payload</li><li>Context requests mediated</li></ul></article>
      </section>
      <section className="panel payload-panel">
        <div className="panel-heading"><div><span className="eyebrow">Immutable approved envelope</span><h2>Exact cloud payload</h2></div><Braces /></div>
        <pre>{JSON.stringify(payloads.map((payload, sequence) => ({ sequence: sequence + 1, provider: payload.provider_name, trust_zone: payload.trust_zone_id, approved_disclosures: payload.disclosures.map((item) => ({ text: item.text, precision: item.precision, fact_keys: item.fact_keys })) })), null, 2)}</pre>
        <div className="payload-footer"><span><CheckCircle2 /> Brokered messages</span><strong>{payloads.length}</strong><span className="muted">{result.mode === "trustsplit" ? "Exact source facts withheld" : "Synthetic comparison evidence"}</span></div>
      </section>
    </div>
  );
}

function CollaborationView({ result }: { result: WorkflowResult }) {
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [running, setRunning] = useState("");
  const [scenarioError, setScenarioError] = useState("");
  async function execute(id: string) {
    setRunning(id);
    setScenarioError("");
    try {
      setScenario(await runScenario(id));
    } catch (error) {
      setScenario(null);
      setScenarioError(error instanceof Error ? error.message : "Scenario failed safely.");
    } finally {
      setRunning("");
    }
  }
  return (
    <div className="collab-layout">
      <section className="panel timeline-panel">
        <div className="panel-heading"><div><span className="eyebrow">Mediated workflow</span><h2>Collaboration timeline</h2></div><Activity /></div>
        <ol className="timeline">
          {result.events.map((event) => (
            <li key={event.sequence} className={`actor-${event.actor}`}><span className="sequence">{String(event.sequence).padStart(2, "0")}</span><div><b>{event.state.replaceAll("_", " ")}</b><p>{event.safe_summary}</p></div><span className="actor">{event.actor.replaceAll("_", " ")}</span></li>
          ))}
        </ol>
      </section>
      <aside className="scenario-stack">
        {scenarioCards.map((card) => <article className="panel scenario-card" key={card.id}><span className="eyebrow">Deterministic story</span><h3>{card.name}</h3><p>{card.description}</p><button onClick={() => void execute(card.id)} disabled={Boolean(running)}>{running === card.id ? "Running…" : "Run scenario"}<ChevronRight size={15} /></button></article>)}
        {scenario && <article className="panel scenario-result"><CheckCircle2 /><div><b>{scenario.name}</b><p>{scenario.outcome}</p><small>{scenario.steps.length} broker decisions recorded</small></div></article>}
        {scenarioError && <p className="error-text" role="alert">{scenarioError}</p>}
      </aside>
    </div>
  );
}

function DashboardView({ result }: { result: WorkflowResult }) {
  const risk = result.broker_decision.risk_after;
  const remaining = result.session_budget_remaining ?? 0;
  const initialBudget = result.outbound_payload?.trust_zone_id === "company_cloud" ? 100 : 60;
  return (
    <div className="dashboard-layout">
      <div className="metrics-grid"><Metric label="Session privacy budget" value={`${remaining} / ${initialBudget}`} note={`${Math.max(0, initialBudget - remaining)} units used in this session`} /><Metric label="Reconstruction score" value={`${risk} / 100`} note="Internal heuristic · not probability" tone="amber" /><Metric label="Recommendation status" value="Verified" note="Checked locally against hidden constraints" tone="violet" /></div>
      <section className="panel score-panel"><div className="panel-heading"><div><span className="eyebrow">Cumulative exposure</span><h2>Current protected dimension</h2></div><CircleGauge /></div><div className="bar-list"><div className="bar-row"><span>Architecture</span><div className="bar-track"><i style={{ width: `${risk}%` }} /></div><strong>{risk}</strong></div></div><div className="thresholds"><span><i className="dot safe" /> Policy allow</span><span><i className="dot warning" /> Policy generalise</span><span><i className="dot danger" /> Policy deny</span></div></section>
      <section className="panel audit-panel"><div className="panel-heading"><div><span className="eyebrow">Run evidence</span><h2>Decision accounting</h2></div><BookOpenCheck /></div><dl><div><dt>Risk before</dt><dd>{result.broker_decision.risk_before}</dd></div><div><dt>Disclosure delta</dt><dd>+{result.broker_decision.disclosure_delta}</dd></div><div><dt>Risk after</dt><dd>{risk}</dd></div><div><dt>Budget cost</dt><dd>{result.broker_decision.budget_cost}</dd></div></dl></section>
    </div>
  );
}

function LedgerView({ result, hasRun }: { result: WorkflowResult; hasRun: boolean }) {
  const previewClaims: LedgerClaim[] = (result.outbound_payload?.disclosures ?? []).flatMap(
    (disclosure) => disclosure.fact_keys.map((key) => ({
      trust_zone_id: result.outbound_payload?.trust_zone_id ?? "local_only",
      protected_entity_id: "project-aurora",
      dimension: disclosure.category.split(".")[0],
      semantic_key: key,
      category: disclosure.category,
      safe_representation: disclosure.text,
      precision: disclosure.precision,
      base_weight: result.broker_decision.risk_after,
    })),
  );
  const [claims, setClaims] = useState<LedgerClaim[]>(previewClaims);
  const [ledgerError, setLedgerError] = useState("");

  useEffect(() => {
    if (!hasRun || !result.outbound_payload) return;
    void getLedger(result.outbound_payload.trust_zone_id)
      .then(setClaims)
      .catch((error: unknown) => setLedgerError(error instanceof Error ? error.message : "Ledger unavailable"));
  }, [hasRun, result]);

  return <section className="panel ledger-panel"><div className="panel-heading"><div><span className="eyebrow">{hasRun ? "Live organisation-wide memory" : "Synthetic preview"}</span><h2>Exposure Ledger</h2><p>Safe representations accumulate across employees inside each provider trust zone.</p></div><Database /></div>{ledgerError && <p className="error-text" role="alert">{ledgerError}</p>}<div className="table-wrap"><table><thead><tr><th>Semantic key</th><th>Safe representation</th><th>Precision</th><th>Trust zone</th><th>Weight</th></tr></thead><tbody>{claims.map((claim) => <tr key={`${claim.trust_zone_id}-${claim.semantic_key}`}><td>{claim.semantic_key}</td><td>{claim.safe_representation}</td><td>{claim.precision.replaceAll("_", " ")}</td><td>{claim.trust_zone_id}</td><td><span className="score-pill">{claim.base_weight}</span></td></tr>)}</tbody></table></div><div className="ledger-note"><Network /><p><b>Cross-employee protection is active.</b> A new employee session resets its budget, but not the provider’s long-term exposure memory.</p></div></section>;
}

function PolicyView() {
  const fallback: Policy = {
    max_clarification_rounds: 4,
    hard_block_categories: ["credential", "private_key", "exact_customer_identity", "raw_restricted_document"],
    trust_zones: {
      personal_cloud: { classification: "personal", disclosure_budget: 60, retention_days: null, generalise_at: 55, deny_at: 75 },
    },
  };
  const [policy, setPolicy] = useState<Policy>(fallback);
  const [policyStatus, setPolicyStatus] = useState("Loading live policy…");
  useEffect(() => {
    void getPolicy().then((loaded) => { setPolicy(loaded); setPolicyStatus("Live policy loaded"); }).catch(() => setPolicyStatus("Offline preview policy"));
  }, []);
  const zone = policy.trust_zones.personal_cloud ?? fallback.trust_zones.personal_cloud;
  function setZone(key: "generalise_at" | "deny_at" | "disclosure_budget", value: number) {
    setPolicy({ ...policy, trust_zones: { ...policy.trust_zones, personal_cloud: { ...zone, [key]: value } } });
  }
  async function savePolicy() {
    try { setPolicy(await updatePolicy(policy)); setPolicyStatus("Policy validated and active"); }
    catch (error) { setPolicyStatus(error instanceof Error ? error.message : "Policy update rejected"); }
  }
  return <div className="policy-layout"><section className="panel policy-panel"><div className="panel-heading"><div><span className="eyebrow">Deterministic authority · {policyStatus}</span><h2>Admin / Policy</h2></div><ShieldCheck /></div><div className="policy-banner"><ShieldX /><div><b>Hard-deny rules always win</b><p>Secrets, credentials, exact protected identities, and restricted content cannot be overridden by model recommendations.</p></div></div><div className="policy-grid"><label>Generalise at<input type="number" value={zone.generalise_at} onChange={(event) => setZone("generalise_at", Number(event.target.value))} /></label><label>Deny at<input type="number" value={zone.deny_at} onChange={(event) => setZone("deny_at", Number(event.target.value))} /></label><label>Session budget<input type="number" value={zone.disclosure_budget} onChange={(event) => setZone("disclosure_budget", Number(event.target.value))} /></label><label>Clarification rounds<input type="number" value={policy.max_clarification_rounds} onChange={(event) => setPolicy({ ...policy, max_clarification_rounds: Number(event.target.value) })} /></label><label>Retention<select value={zone.retention_days === null ? "persistent" : "finite"} disabled><option value="persistent">persistent</option><option value="finite">finite</option></select></label></div><button className="primary-button" onClick={() => void savePolicy()}><CheckCircle2 size={16} />Validate and activate</button></section><aside className="panel rules-panel"><span className="eyebrow">Active rules</span><h3>Non-negotiable boundaries</h3>{["API keys and bearer tokens", "Passwords and private keys", "Exact protected identity", "RESTRICTED documents", "Malformed tool input"].map((rule) => <div className="rule-row" key={rule}><ShieldX size={15} /><span>{rule}</span><b>DENY</b></div>)}<div className="credential-card"><KeyRound /><div><b>Credentials are ephemeral</b><p>Provider keys remain process-local and never return to the browser.</p></div></div></aside></div>;
}

export function App() {
  const [active, setActive] = useState<ViewName>("Chat");
  const [result, setResult] = useState<WorkflowResult>(preview);
  const [hasRun, setHasRun] = useState(false);
  const title = useMemo(() => views.find((view) => view.label === active)?.label ?? active, [active]);
  function acceptResult(value: WorkflowResult) {
    setResult(value);
    setHasRun(true);
  }
  function resetDemo() {
    setResult(preview);
    setHasRun(false);
    setActive("Chat");
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><ShieldCheck /></div><div><h1>TrustSplit AI</h1><p>Keep the secrets local. Keep the intelligence global.</p></div></div>
        <nav aria-label="Primary navigation">{views.map(({ label, icon: Icon }) => <button key={label} className={active === label ? "active" : ""} onClick={() => setActive(label)}><Icon size={18} /><span>{label}</span>{active === label && <ChevronRight size={15} />}</button>)}</nav>
        <div className="system-status"><span className="status-line"><i /> Offline-ready</span><p>Mock providers active</p><small>No internet required</small></div>
      </aside>
      <main>
        <header className="topbar"><div><span className="eyebrow">Privacy control room</span><h2>{title}</h2></div><div className="topbar-actions"><span className="synthetic-label"><Sparkles size={14} /> {hasRun ? "Live synthetic run" : "Synthetic preview"}</span><span className="provider-state"><i /> Company Cloud · ready</span><button aria-label="Reset demo" onClick={resetDemo}><RotateCcw size={16} /></button></div></header>
        <div className="content">
          {active === "Chat" && <ChatView result={result} onResult={acceptResult} />}
          {active === "Privacy Pipeline" && <PipelineView result={result} />}
          {active === "Collaboration" && <CollaborationView result={result} />}
          {active === "Privacy Dashboard" && <DashboardView result={result} />}
          {active === "Exposure Ledger" && <LedgerView result={result} hasRun={hasRun} />}
          {active === "Admin / Policy" && <PolicyView />}
        </div>
      </main>
    </div>
  );
}
