import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../src/App";
import { ThinkingTrace } from "../src/components/ThinkingTrace";

describe("TrustSplit chat workspace", () => {
  it("renders the chat-first shell and privacy boundary", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "TrustSplit AI" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What can I help you protect?" })).toBeInTheDocument();
    expect(screen.getByText("Zero-trust boundary")).toBeInTheDocument();
    expect(screen.getByText("Private by default")).toBeInTheDocument();
    expect(screen.getByText("Technical trace is running in the integrated terminal")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Privacy Pipeline" })).not.toBeInTheDocument();
  });

  it("offers safe and sensitive demo prompts without exposing the old dashboard", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByRole("button", { name: "Review a private architecture" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try a credential leak" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try an exact customer lookup" })).toBeInTheDocument();
    expect(screen.getByText(/Synthetic API key \+ password/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "New chat" }));
    expect(screen.getByRole("heading", { name: "What can I help you protect?" })).toBeInTheDocument();
  });

  it("keeps the composer private and send disabled until text is entered", async () => {
    const user = userEvent.setup();
    render(<App />);
    const composer = screen.getByRole("textbox", { name: "Message" });
    const send = screen.getByRole("button", { name: "Send message" });

    expect(send).toBeDisabled();
    await user.type(composer, "Summarise this private design");
    expect(send).toBeEnabled();
    expect(screen.getByText("Private by default")).toBeInTheDocument();
  });

  it("renders the safe local reconstruction inside the thinking trace", () => {
    render(
      <ThinkingTrace
        status="idle"
        events={[{
          sequence: 3,
          stage: "safe_reconstruction",
          public_label: "Reconstructing a safe prompt…",
          safe_summary: "A minimum-information representation was prepared.",
          safe_detail: "A large regulated financial organisation uses a clustered relational database at 15k-20k TPS.",
          delay_ms: 1750,
        }]}
      />,
    );

    expect(screen.getByText("Local AI reconstructed prompt")).toBeInTheDocument();
    expect(screen.getByText(/15k-20k TPS/)).toBeInTheDocument();
  });
});
