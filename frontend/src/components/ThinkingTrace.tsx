import { Check, LoaderCircle } from "lucide-react";
import type { ProgressEvent } from "../types";

export function ThinkingTrace({ events, status }: { events: ProgressEvent[]; status: "idle" | "running" | "error" }) {
  if (status === "idle" && events.length === 0) return null;
  const active = events.at(-1)?.sequence;
  return (
    <section className="thinking-trace" aria-label="Privacy workflow status">
      <div className="thinking-heading"><LoaderCircle size={15} className={status === "running" ? "spin" : ""} /><span>{status === "running" ? "TrustSplit is working" : "TrustSplit completed"}</span></div>
      <ol>
        {events.map((event) => {
          const complete = status !== "running" || event.sequence !== active;
          return <li key={event.sequence} aria-label={`${event.public_label} ${complete ? "complete" : "in progress"}`} className={complete ? "complete" : "active"}>{complete ? <Check size={14} /> : <LoaderCircle size={14} className="spin" />}<div><b>{event.public_label}</b><small>{event.safe_summary}</small>{event.safe_detail && <div className="safe-reconstruction"><span>Local AI reconstructed prompt</span><code>{event.safe_detail}</code></div>}</div></li>;
        })}
      </ol>
    </section>
  );
}
