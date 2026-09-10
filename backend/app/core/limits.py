from dataclasses import dataclass, field

from app.domain.providers import CloudContextRequest


class UnsafeCloudRequest(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class CloudRequestLimits:
    max_question_chars: int = 2_000
    allowed_categories: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "architecture.partitioning",
                "architecture.consistency",
                "operations.latency",
                "operations.throughput",
            }
        )
    )


def validate_cloud_context_request(
    request: CloudContextRequest, limits: CloudRequestLimits
) -> CloudContextRequest:
    if len(request.question) > limits.max_question_chars:
        raise UnsafeCloudRequest("request.too_large")
    if request.category not in limits.allowed_categories:
        raise UnsafeCloudRequest("request.unsupported_category")
    return request
