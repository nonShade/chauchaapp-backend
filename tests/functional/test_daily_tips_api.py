"""
Real functional test: daily tips generation.

POST /tips/generate -> background worker calls real NVIDIA API ->
poll task until completed -> GET /tips/all -> GET /tips/today
"""

import pytest
from tests.functional_real.conftest import poll_task

TIMEOUT = 20


class TestDailyTipsRealFlow:
    def test_generate_and_retrieve_tips(self, client):
        r = client.post("/tips/generate")
        assert r.status_code == 202
        task_id = r.json()["task_id"]

        task_data = poll_task(
            client, f"/tips/tasks/{task_id}", timeout_minutes=TIMEOUT
        )

        assert task_data["status"] == "completed"
        result = task_data.get("result")
        assert result is not None
        assert len(result.get("tips", [])) == 7

        r = client.get("/tips/all")
        assert r.status_code == 200
        data = r.json()
        assert data["total_count"] == 7
        assert len(data["tips"]) == 7
        for tip in data["tips"]:
            assert "title" in tip
            assert "text" in tip
            assert "category" in tip
            assert "day_of_week" in tip

        r = client.get("/tips/today")
        assert r.status_code == 200
        today = r.json()
        assert "title" in today
        assert "text" in today
