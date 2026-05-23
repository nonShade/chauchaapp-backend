from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.financial_data.entities import FinancialPlanningTip


class FinancialPlanningRepository:
    def __init__(self, db: Session):
        self._db = db

    def create_batch(
        self, tips: list[FinancialPlanningTip]
    ) -> list[FinancialPlanningTip]:
        self._db.add_all(tips)
        self._db.flush()
        return tips

    def deactivate_all(self) -> int:
        result = self._db.query(FinancialPlanningTip).filter(
            FinancialPlanningTip.is_active == True
        ).update({FinancialPlanningTip.is_active: False})
        self._db.flush()
        return result

    def get_all_active(self) -> list[FinancialPlanningTip]:
        return (
            self._db.query(FinancialPlanningTip)
            .filter(FinancialPlanningTip.is_active == True)
            .order_by(FinancialPlanningTip.generated_at.desc())
            .all()
        )

    def get_latest_generation_date(self) -> datetime | None:
        result = (
            self._db.query(FinancialPlanningTip.generated_at)
            .filter(FinancialPlanningTip.is_active == True)
            .order_by(FinancialPlanningTip.generated_at.desc())
            .first()
        )
        return result[0] if result else None
