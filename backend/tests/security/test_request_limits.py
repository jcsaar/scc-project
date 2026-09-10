import pytest

from app.core.limits import CloudRequestLimits, UnsafeCloudRequest, validate_cloud_context_request
from app.domain.disclosures import PrecisionLevel
from app.domain.providers import CloudContextRequest


def context_request(question: str, category: str) -> CloudContextRequest:
    return CloudContextRequest(
        question=question,
        purpose="Evaluate an architecture option",
        category=category,
        requested_precision=PrecisionLevel.BOOLEAN,
    )


def test_oversized_cloud_question_is_rejected() -> None:
    limits = CloudRequestLimits(max_question_chars=20)

    with pytest.raises(UnsafeCloudRequest, match="request.too_large"):
        validate_cloud_context_request(
            context_request("x" * 21, "architecture.partitioning"), limits
        )


def test_unsupported_cloud_category_is_rejected() -> None:
    limits = CloudRequestLimits(allowed_categories=frozenset({"architecture.partitioning"}))

    with pytest.raises(UnsafeCloudRequest, match="request.unsupported_category"):
        validate_cloud_context_request(
            context_request("What is the password?", "credential.password"), limits
        )


def test_allowed_cloud_request_is_returned_unchanged() -> None:
    request = context_request("Does a partitioning key exist?", "architecture.partitioning")

    assert validate_cloud_context_request(request, CloudRequestLimits()) is request
