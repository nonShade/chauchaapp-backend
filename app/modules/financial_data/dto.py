"""
Financial planning DTOs.
"""

from datetime import datetime

from pydantic import BaseModel


class FinancialPlanningResourceDTO(BaseModel):
    title: str
    url: str


class FinancialPlanningTipDTO(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    category: str
    keyPoints: list[str]
    actionItems: list[str]
    resources: list[FinancialPlanningResourceDTO]


class FinancialPlanningTipsResponseDTO(BaseModel):
    financialPlanningTips: list[FinancialPlanningTipDTO]


class FinancialPlanningTipsBatchResponseDTO(BaseModel):
    financialPlanningTips: list[FinancialPlanningTipDTO]
    totalCount: int
    generatedAt: datetime | None = None
