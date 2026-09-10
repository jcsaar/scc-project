import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../src/App";

describe("TrustSplit dashboard", () => {
  it("renders the operator shell and all six views", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "TrustSplit AI" })).toBeInTheDocument();
    expect(screen.getByText("Keep the secrets local. Keep the intelligence global.")).toBeInTheDocument();
    for (const label of ["Chat", "Privacy Pipeline", "Collaboration", "Privacy Dashboard", "Exposure Ledger", "Admin / Policy"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
  });

  it("renders the exact cloud payload and broker decision", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Privacy Pipeline" }));
    expect(screen.getByText("15k–20k TPS")).toBeInTheDocument();
    expect(screen.getByText("GENERALISE")).toBeInTheDocument();
    expect(screen.queryByText("18,274")).not.toBeInTheDocument();
  });

  it("shows budget, risk, ledger, metrics, and policy state", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Privacy Dashboard" }));
    expect(screen.getByText("42 / 60")).toBeInTheDocument();
    expect(screen.getByText("Reconstruction score")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Exposure Ledger" }));
    expect(screen.getByText("throughput.capacity")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Admin / Policy" }));
    expect(screen.getByText("Hard-deny rules always win")).toBeInTheDocument();
  });
});
