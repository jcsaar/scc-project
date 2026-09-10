import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ThinkingTrace } from "../src/components/ThinkingTrace";

describe("ThinkingTrace", () => {
  it("shows completed and active operational stages without private facts", () => {
    render(
      <ThinkingTrace
        status="running"
        events={[
          {
            sequence: 1,
            stage: "sensitive_scan",
            public_label: "Scanning for sensitive information…",
            safe_summary: "Protected entities remain local.",
            delay_ms: 1200,
          },
          {
            sequence: 2,
            stage: "safe_reconstruction",
            public_label: "Reconstructing a safe prompt…",
            safe_summary: "A minimum-information representation was prepared.",
            delay_ms: 1400,
          },
        ]}
      />,
    );

    expect(screen.getByText("Scanning for sensitive information…")).toBeInTheDocument();
    expect(screen.getByText("Reconstructing a safe prompt…")).toBeInTheDocument();
    expect(screen.queryByText(/18,274|Northstar|Oracle RAC/)).not.toBeInTheDocument();
  });
});
