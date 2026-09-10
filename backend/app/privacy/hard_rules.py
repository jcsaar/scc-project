import re

from pydantic import Field

from app.domain.disclosures import PrecisionLevel, StrictFrozenModel


class DisclosureInspection(StrictFrozenModel):
    text: str = Field(min_length=1)
    category: str = "general"
    precision: PrecisionLevel = PrecisionLevel.BROAD_CATEGORY
    classification: str = "INTERNAL"
    is_raw_document: bool = False


class HardRuleResult(StrictFrozenModel):
    blocked: bool
    reason_code: str
    safe_reason: str


class HardRuleEngine:
    _patterns = (
        (
            "credential.private_key",
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ),
        ("credential.token", re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{20,}", re.IGNORECASE)),
        (
            "credential.password",
            re.compile(r"\bpassword\s*[:=]\s*[^\s'\"]{8,}", re.IGNORECASE),
        ),
        (
            "credential.api_key",
            re.compile(r"\bsk-(?:proj-|ant-api\d*-)?[A-Za-z0-9_-]{20,}"),
        ),
        (
            "credential.api_key",
            re.compile(
                r"\b(?:api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{20,}",
                re.IGNORECASE,
            ),
        ),
    )

    def inspect(self, candidate: DisclosureInspection) -> HardRuleResult:
        exact_customer_identity = (
            candidate.category == "identity.customer"
            and candidate.precision is PrecisionLevel.EXACT
        )
        if exact_customer_identity:
            return HardRuleResult(
                blocked=True,
                reason_code="identity.exact_customer",
                safe_reason="Exact protected customer identity cannot leave the local zone.",
            )
        if candidate.classification.upper() == "RESTRICTED" and candidate.is_raw_document:
            return HardRuleResult(
                blocked=True,
                reason_code="classification.raw_restricted_document",
                safe_reason="Raw restricted documents cannot leave the local zone.",
            )
        for reason_code, pattern in self._patterns:
            if pattern.search(candidate.text):
                return HardRuleResult(
                    blocked=True,
                    reason_code=reason_code,
                    safe_reason="Credential material cannot leave the local zone.",
                )
        return HardRuleResult(
            blocked=False,
            reason_code="hard_rules.clear",
            safe_reason="No deterministic hard-block rule matched.",
        )
