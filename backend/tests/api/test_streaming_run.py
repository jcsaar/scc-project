import json

import httpx
import pytest

from app.main import create_app


def parse_sse(text: str) -> list[dict[str, object]]:
    records = []
    for frame in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in frame.splitlines())
        records.append({"type": lines["event"], "data": json.loads(lines["data"])})
    return records


@pytest.mark.anyio
async def test_run_stream_orders_progress_before_result() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/sessions",
            json={
                "employee_id": "alice",
                "mode": "trustsplit",
                "trust_zone_id": "company_cloud",
                "project_id": "project-aurora",
            },
        )
        response = await client.post(
            f"/api/sessions/{created.json()['id']}/run-stream",
            json={"prompt": "Review Project Aurora"},
        )

    records = parse_sse(response.text)
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [record["type"] for record in records[:-1]] == ["progress"] * 10
    assert records[-1]["type"] == "result"
    assert records[-1]["data"]["verification_status"] == "accepted"
