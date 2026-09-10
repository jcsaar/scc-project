import io
import logging

from app.core.logging import SecretRedactionFilter


def test_logging_filter_redacts_secrets_in_nested_structures() -> None:
    api_key = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"
    password = "CorrectHorseBatteryStaple"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SecretRedactionFilter())
    logger = logging.getLogger("trustsplit.security-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info({"headers": {"authorization": f"Bearer {api_key}"}, "password": password})

    output = stream.getvalue()
    assert api_key not in output
    assert password not in output
    assert "[REDACTED]" in output


def test_logging_filter_redacts_secrets_in_plain_messages() -> None:
    secret = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456"
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SecretRedactionFilter())
    logger = logging.getLogger("trustsplit.message-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.error("Provider rejected %s", secret)

    assert secret not in stream.getvalue()
    assert "[REDACTED]" in stream.getvalue()
