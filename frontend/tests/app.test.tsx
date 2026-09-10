import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../src/App";

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
});
