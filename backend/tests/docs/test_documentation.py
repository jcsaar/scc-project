from pathlib import Path

ROOT = Path(__file__).parents[3]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_readme_documents_invariant_and_release_commands() -> None:
    content = read("README.md")
    assert "Cloud AI never directly accesses private corporate data" in content
    for command in ("make demo", "make test", "make build", "make verify-secrets", "make e2e"):
        assert command in content
    for heading in ("## Quick start", "## Demo modes", "## Security posture", "## Limitations"):
        assert heading in content


def test_handoff_documents_cover_required_security_topics() -> None:
    expected = {
        "docs/architecture.md": ("# Architecture", "ApprovedCloudPayload", "Exposure Ledger"),
        "docs/threat-model.md": ("# Threat model", "mosaic", "malicious"),
        "docs/security-boundaries.md": ("# Security boundaries", "credentials", "hard rules"),
        "docs/demo-walkthrough.md": ("# Demo walkthrough", "10–15 minutes", "Cloud Only"),
        "docs/limitations.md": ("# Limitations", "not a probability", "not production-ready"),
    }
    for path, phrases in expected.items():
        content = read(path)
        assert all(phrase.lower() in content.lower() for phrase in phrases), path
