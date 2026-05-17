from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.education.entities import EducationalModule, UserProgress


class EducationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_modules(self) -> list[EducationalModule]:
        return self.db.query(EducationalModule).order_by(
            EducationalModule.created_at.desc()
        ).all()

    def get_module_by_id(self, module_id: UUID) -> EducationalModule | None:
        return self.db.query(EducationalModule).filter(
            EducationalModule.educational_module_id == module_id
        ).first()

    def get_user_progress(
        self, user_id: UUID, module_id: UUID
    ) -> UserProgress | None:
        return self.db.query(UserProgress).filter(
            UserProgress.user_id == user_id,
            UserProgress.educational_module_id == module_id,
        ).first()

    def create_module(self, module) -> EducationalModule:
        record = EducationalModule(
            educational_module_id=UUID(module.id),
            title=module.title,
            description=module.description,
            content=module.json(),
            duration=module.estimatedTimeMinutes,
            difficulty=module.level,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def save_user_progress(self, progress: UserProgress) -> UserProgress:
        existing = self.get_user_progress(
            user_id=progress.user_id,
            module_id=progress.educational_module_id,
        )

        if existing is None:
            self.db.add(progress)
            self.db.commit()
            self.db.refresh(progress)
            return progress

        existing.status = progress.status
        existing.progress_percentage = progress.progress_percentage
        existing.completed_sections = progress.completed_sections
        existing.quiz_attempts = progress.quiz_attempts
        existing.started_at = progress.started_at
        existing.last_accessed_at = progress.last_accessed_at
        existing.completed_at = progress.completed_at
        self.db.commit()
        self.db.refresh(existing)
        return existing
