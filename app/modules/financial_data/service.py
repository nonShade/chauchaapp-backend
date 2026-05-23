"""
Financial planning service.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.financial_agent.financial_agent import (
    FinancialPlanningAgent,
    FinancialPlanningTip,
    financial_planning_agent,
)
from app.modules.financial_data.entities import FinancialPlanningTip as TipEntity
from app.modules.financial_data.repository import FinancialPlanningRepository


class FinancialPlanningService:
    def __init__(
        self,
        db: Session,
        agent: FinancialPlanningAgent | None = None,
        repository: FinancialPlanningRepository | None = None,
    ) -> None:
        self._db = db
        self._agent = agent or financial_planning_agent
        self._repository = repository or FinancialPlanningRepository(db)

    def generate_and_save_tips(self) -> list[FinancialPlanningTip]:
        tips = self._agent.get_financial_planning_tips()
        now = datetime.utcnow()

        self._repository.deactivate_all()

        tip_entities = [
            TipEntity(
                title=tip.title,
                description=tip.description,
                icon=tip.icon,
                category=tip.category,
                key_points=tip.keyPoints,
                action_items=tip.actionItems,
                resources=[resource.model_dump() for resource in tip.resources],
                generated_at=now,
                is_active=True,
            )
            for tip in tips
        ]
        created = self._repository.create_batch(tip_entities)
        self._db.commit()
        return tips

    def get_active_tips(self) -> list[FinancialPlanningTip]:
        records = self._repository.get_all_active()
        return [self._to_tip_model(record) for record in records]

    def get_latest_generation_date(self) -> datetime | None:
        return self._repository.get_latest_generation_date()

    def _to_tip_model(self, record: TipEntity) -> FinancialPlanningTip:
        resources = record.resources or []
        return FinancialPlanningTip(
            id=str(record.planning_tip_id),
            title=record.title,
            description=record.description,
            icon=record.icon,
            category=record.category,
            keyPoints=list(record.key_points or []),
            actionItems=list(record.action_items or []),
            resources=resources,
        )
