import { useRef, useState } from "react";
import {
  ArrowUp,
  Check,
  ChevronDown,
  CircleStop,
  Copy,
  FileText,
  LockKeyhole,
  Plus,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  X,
} from "lucide-react";
import { resetDemo, streamWorkflow } from "./api";
import { ThinkingTrace } from "./components/ThinkingTrace";
import type { ProgressEvent, WorkflowResult } from "./types";
import "./styles.css";

const starterPrompt =
  "Review Project Aurora's transaction architecture and recommend a safe scale-out design.";

function PrivacyReceipt({ result, events, open, onToggle }: { result: WorkflowResult | null; events: ProgressEvent[]; open: boolean; onToggle: () => void }) {
  const decision = result?.broker_decision;
  const payloads = result?.outbound_payloads?.length
    ? result.outbound_payloads
    : result?.outbound_payload
      ? [result.outbound_payload]
      : [];
  const factCount = payloads.reduce(
    (count, payload) => count + payload.disclosures.reduce((sum, item) => sum + item.fact_keys.length, 0),
    0,
  );
  return (
    <aside className={`receipt ${open ? "receipt-open" : ""}`}>
      <div className="receipt-heading"><div><span className="kicker">Live privacy receipt</span><h2>Zero-trust border</h2></div><ShieldCheck size={20} /></div>
      <div className={`border-state ${decision?.decision === "deny" ? "blocked" : decision ? "cleared" : "idle"}`}><span className="state-dot" /><div><b>{decision ? (decision.decision === "deny" ? "Transmission blocked" : "Border checked") : "Border standing by"}</b><small>{events.at(-1)?.safe_summary ?? "Run a message to inspect its cloud boundary."}</small></div></div>
      <div className="receipt-stats"><div><span>Raw facts to cloud</span><b>0</b></div><div><span>Approved abstractions</span><b>{factCount || "—"}</b></div><div><span>Final risk</span><b>{result?.final_risk ?? "—"}<em>/100</em></b></div><div><span>Decision</span><b className={decision?.decision === "deny" ? "danger-text" : "accent-text"}>{decision?.decision?.toUpperCase() ?? "—"}</b></div></div>
      {result && <div className="receipt-checks"><p><Check size={14} /> Source context stayed local</p><p><Check size={14} /> Cloud received approved context</p><p><Check size={14} /> Response checked locally</p></div>}
      {result && payloads.length > 0 && <details className="payload-details" open={open} onToggle={onToggle}><summary>Approved payload <ChevronDown size={15} /></summary><pre>{JSON.stringify(payloads, null, 2)}</pre></details>}
      {!result && <div className="receipt-empty"><LockKeyhole size={18} /><p>Your private facts will be inspected here before anything can leave this device.</p></div>}
      <div className="receipt-footer"><TerminalSquare size={15} /><span>Technical trace is running in the integrated terminal</span></div>
    </aside>
  );
}

function ChatMessage({ role, children }: { role: "assistant" | "user"; children: React.ReactNode }) {
  return <article className={`chat-message ${role}`}><div className="avatar">{role === "assistant" ? <Sparkles size={16} /> : "J"}</div><div className="message-body"><span className="message-author">{role === "assistant" ? "TrustSplit AI" : "You"}</span>{children}</div></article>;
}

export function App() {
  const [prompt, setPrompt] = useState("");
  const [userPrompt, setUserPrompt] = useState<string | null>(null);
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [status, setStatus] = useState<"idle" | "running" | "complete" | "error">("idle");
  const [error, setError] = useState("");
  const [receiptOpen, setReceiptOpen] = useState(false);
  const [history, setHistory] = useState<string[]>(["Architecture review"]);
  const abortRef = useRef<AbortController | null>(null);

  async function submit(value = prompt) {
    const text = value.trim();
    if (!text || status === "running") return;
    setPrompt(""); setUserPrompt(text); setResult(null); setEvents([]); setReceiptOpen(false); setError(""); setStatus("running");
    setHistory((items) => [text.slice(0, 36), ...items.filter((item) => item !== "Architecture review")].slice(0, 4));
    abortRef.current = new AbortController();
    try {
      await streamWorkflow(
        { employeeId: "alice", mode: "trustsplit", provider: "company_cloud", prompt: text },
        { onProgress: (event) => setEvents((items) => [...items, event]), onResult: (value) => setResult(value) },
        abortRef.current.signal,
      );
      setStatus("complete");
    } catch (caught) {
      if ((caught as Error).name !== "AbortError") { setStatus("error"); setError(caught instanceof Error ? caught.message : "The workflow could not be completed."); } else setStatus("idle");
    } finally { abortRef.current = null; }
  }

  function newChat() { setPrompt(""); setUserPrompt(null); setResult(null); setEvents([]); setStatus("idle"); setError(""); }
  async function reset() {
    if (!window.confirm("Reset the synthetic conversation and privacy ledger?")) return;
    try { await resetDemo(); newChat(); setHistory(["Architecture review"]); } catch (caught) { setError(caught instanceof Error ? caught.message : "Reset failed safely."); setStatus("error"); }
  }

  const thinkingStatus = status === "error" ? "error" : status === "running" ? "running" : "idle";
  return (
    <div className="chat-app">
      <aside className="chat-sidebar">
        <div className="brand-lockup"><div className="brand-icon"><ShieldCheck size={20} /></div><div><b>TrustSplit</b><span>Private intelligence</span></div></div>
        <button className="new-chat" onClick={newChat}><Plus size={17} />New chat</button>
        <div className="sidebar-section"><span className="kicker">Recent</span>{history.map((item, index) => <button className={`history-item ${index === 0 ? "selected" : ""}`} key={`${item}-${index}`} onClick={newChat}><FileText size={15} /><span>{item}</span></button>)}</div>
        <div className="sidebar-spacer" />
        <div className="boundary-card"><div className="boundary-card-title"><LockKeyhole size={15} /><span>Zero-trust boundary</span></div><p>Private source facts are transformed locally before cloud reasoning.</p><div className="boundary-row"><span className="local-dot" />Local private zone <b>active</b></div><div className="boundary-row"><span className="cloud-dot" />Cloud reasoning <b>mediated</b></div></div>
        <div className="sidebar-footer"><span className="online-dot" />Offline demo · deterministic responses</div>
      </aside>
      <main className="chat-main">
        <header className="chat-header"><div><span className="kicker">Local-first workspace</span><h1>TrustSplit AI</h1></div><div className="header-actions"><span className="live-pill"><span className="online-dot" />Local border active</span><button aria-label="Reset demo" onClick={() => void reset()}><RotateCcw size={16} /></button></div></header>
        <div className="chat-scroll"><div className="conversation">
          {!userPrompt && <section className="welcome"><div className="welcome-mark"><ShieldCheck size={25} /></div><h2>What can I help you protect?</h2><p>Ask a question with sensitive context. I’ll reconstruct a safe prompt locally, pass only approved context to Cloud AI, and verify the answer before returning it.</p><div className="suggestions"><button onClick={() => void submit(starterPrompt)}>Review a private architecture <ArrowUp size={14} /></button><button onClick={() => void submit("Show me the blocked secret handling path.")}>Try a blocked request <ArrowUp size={14} /></button></div></section>}
          {userPrompt && <ChatMessage role="user"><p>{userPrompt}</p></ChatMessage>}
          {userPrompt && <ThinkingTrace events={events} status={thinkingStatus} />}
          {result && <ChatMessage role="assistant"><p>{result.final_answer}</p><div className="answer-meta"><span><Check size={14} /> {result.verification_status === "accepted" ? "Locally verified" : "Kept local"}</span><button onClick={() => navigator.clipboard?.writeText(result.final_answer)}><Copy size={13} /> Copy</button></div></ChatMessage>}
          {error && <div className="inline-error"><X size={15} />{error}</div>}
        </div></div>
        <form className="composer-new" onSubmit={(event) => { event.preventDefault(); void submit(); }}><textarea aria-label="Message" value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Message TrustSplit AI…" disabled={status === "running"} rows={1} /><div className="composer-bottom"><span><LockKeyhole size={13} /> Private by default</span><div>{status === "running" ? <button type="button" className="stop-button" onClick={() => abortRef.current?.abort()}><CircleStop size={15} /> Stop</button> : <button className="send-button" type="submit" disabled={!prompt.trim()} aria-label="Send message"><ArrowUp size={17} /></button>}</div></div></form>
        <p className="disclaimer">TrustSplit is a deterministic hackathon prototype. Responses are simulated; privacy mediation is functional.</p>
      </main>
      <PrivacyReceipt result={result} events={events} open={receiptOpen} onToggle={() => setReceiptOpen((value) => !value)} />
    </div>
  );
}
