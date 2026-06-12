"""
Real functional test: financial planning tips generation.

POST /v1/financial-planning/generate -> background worker calls NVIDIA API ->
poll task until completed -> GET /v1/financial-planning
"""

import pytest
from tests.functional_real.conftest import poll_task

TIMEOUT = 20


class TestFinancialPlanningRealFlow:
    def test_generate_and_retrieve_tips(self, client):
        r = client.post("/v1/financial-planning/generate")
        assert r.status_code == 202
        task_id = r.json()["task_id"]

        task_data = poll_task(
            client, f"/v1/financial-planning/tasks/{task_id}", timeout_minutes=TIMEOUT
        )

        assert task_data["status"] == "completed"
        result = task_data.get("result")
        assert result is not None
        assert result.get("totalCount", 0) >= 1

        r = client.get("/v1/financial-planning")
        assert r.status_code == 200
        data = r.json()
        tips = data.get("financialPlanningTips", [])
        assert len(tips) >= 1
        for tip in tips:
            assert "title" in tip
            assert "description" in tip
            assert "icon" in tip
            assert "category" in tip
            assert "keyPoints" in tip
            assert "actionItems" in tip
