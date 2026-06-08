"""
Education service — educational modules and quizzes content.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID, uuid4

from app.agent.quizzes.quizz_agent import LevelType, Module, QuizzAgent
from app.modules.education.dto import (
    SubmitQuizAttemptRequestDTO,
    SubmitQuizAttemptResponseDTO,
    UpdateModuleProgressRequestDTO,
    UserModuleProgressDTO,
)
from app.modules.education.entities import UserProgress
from app.modules.education.repository import EducationRepository

CONTENT_PROGRESS_WEIGHT = 70


class EducationService:
    def __init__(self, repository: EducationRepository, agent: QuizzAgent | None = None):
        self._agent = agent or QuizzAgent()
        self._repository = repository

    def list_modules(self) -> list[Module]:
        records = self._repository.list_modules()
        return [self._deserialize_module(record) for record in records]

    def get_module_by_slug(self, slug: str) -> Module | None:
        modules = self.list_modules()
        return next((module for module in modules if module.slug == slug), None)

    def get_module_by_id(self, module_id: str) -> Module | None:
        record = self._repository.get_module_by_id(UUID(module_id))
        if record is None:
            return None
        return self._deserialize_module(record)

    def get_progress_for_module(
        self, module_id: str, user_id: str | None
    ) -> UserModuleProgressDTO:
        resolved_user_id = user_id or "guest"
        module = self.get_module_by_id(module_id)
        if module is None:
            return self._build_empty_progress(resolved_user_id, module_id)

        if user_id is None:
            return self._build_empty_progress(resolved_user_id, module_id)

        record = self._repository.get_user_progress(
            user_id=UUID(user_id),
            module_id=UUID(module_id),
        )
        if record is None:
            return self._build_empty_progress(resolved_user_id, module_id)

        return self._serialize_progress(record)

    def start_progress(
        self, module_id: str, user_id: str
    ) -> UserModuleProgressDTO:
        module = self._require_module(module_id)
        now = datetime.utcnow()
        progress = self._get_or_create_progress(user_id=user_id, module_id=module_id)

        if progress.started_at is None:
            progress.started_at = now
        progress.last_accessed_at = now
        if progress.status == "not_started":
            progress.status = "in_progress"

        progress.progress_percentage = self._calculate_progress_percentage(
            module=module,
            completed_sections=progress.completed_sections,
            quiz_attempts=progress.quiz_attempts,
        )
        saved_progress = self._repository.save_user_progress(progress)
        return self._serialize_progress(saved_progress)

    def update_section_progress(
        self,
        module_id: str,
        user_id: str,
        payload: UpdateModuleProgressRequestDTO,
    ) -> UserModuleProgressDTO:
        module = self._require_module(module_id)
        now = datetime.utcnow()
        progress = self._get_or_create_progress(user_id=user_id, module_id=module_id)

        completed_sections = list(progress.completed_sections or [])
        if payload.sectionId not in completed_sections:
            completed_sections.append(payload.sectionId)

        progress.completed_sections = completed_sections
        progress.last_accessed_at = now
        if progress.started_at is None:
            progress.started_at = now
        if progress.status != "completed":
            progress.status = "in_progress"
            progress.progress_percentage = self._calculate_progress_percentage(
                module=module,
                completed_sections=completed_sections,
                quiz_attempts=progress.quiz_attempts,
            )

        saved_progress = self._repository.save_user_progress(progress)
        return self._serialize_progress(saved_progress)

    def submit_quiz_attempt(
        self,
        module_id: str,
        user_id: str,
        payload: SubmitQuizAttemptRequestDTO,
    ) -> SubmitQuizAttemptResponseDTO:
        module = self._require_module(module_id)
        now = datetime.utcnow()
        progress = self._get_or_create_progress(user_id=user_id, module_id=module_id)

        attempts = list(progress.quiz_attempts or [])
        next_attempt_number = len(attempts) + 1
        attempts.append(
            {
                "attempt": next_attempt_number,
                "score": payload.score,
                "correctAnswers": payload.correctAnswers,
                "totalQuestions": payload.totalQuestions,
                "completedAt": now.isoformat(),
            }
        )

        progress.quiz_attempts = attempts
        progress.last_accessed_at = now
        if progress.started_at is None:
            progress.started_at = now

        passed = payload.score >= module.quiz.passingScore
        content_completed = self._is_content_completed(
            module=module,
            completed_sections=progress.completed_sections,
        )

        if passed and content_completed:
            progress.status = "completed"
            progress.progress_percentage = 100
            progress.completed_at = now
        elif progress.status != "completed":
            progress.status = "in_progress"
            progress.progress_percentage = self._calculate_progress_percentage(
                module=module,
                completed_sections=progress.completed_sections,
                quiz_attempts=attempts,
            )

        saved_progress = self._repository.save_user_progress(progress)
        return SubmitQuizAttemptResponseDTO(
            passed=passed and content_completed,
            progress=self._serialize_progress(saved_progress),
        )

    def generate_module(self, topic: str, level: str) -> Module:
        if level not in {"Principiante", "Intermedio", "Avanzado"}:
            raise ValueError("Invalid level")

        module = self._agent.generate_module_from_topic(
            topic=topic, level=level
        )
        module.id = str(uuid4())
        module.createdAt = datetime.utcnow()
        module.slug = module.slug or self._slugify(module.title)

        self._repository.create_module(module)
        return module

    def generate_modules(self, items: list[dict]) -> list[Module]:
        modules: list[Module] = []
        for item in items:
            topic = item.get("topic")
            level = item.get("level")
            if not topic or level not in {"Principiante", "Intermedio", "Avanzado"}:
                raise ValueError("Invalid topic or level")

            module = self._agent.generate_module_from_topic(topic=topic, level=level)
            module.id = str(uuid4())
            module.createdAt = datetime.utcnow()
            module.slug = module.slug or self._slugify(module.title)
            self._repository.create_module(module)
            modules.append(module)

        return modules

    def _deserialize_module(self, record) -> Module:
        if not record.content:
            raise ValueError("Educational module content is empty")
        import json
        data = json.loads(record.content)
        if "quiz" in data and data["quiz"] and "questions" in data["quiz"]:
            for q in data["quiz"].get("questions", []):
                opts = q.get("options") or []
                q["options"] = opts
                q["correctAnswer"] = self._repository._sanitize_correct_answer(
                    q.get("correctAnswer"), opts
                )
            data["quiz"]["questionsCount"] = len(data["quiz"].get("questions", []))
        return Module(**data)

    def _require_module(self, module_id: str) -> Module:
        module = self.get_module_by_id(module_id)
        if module is None:
            raise ValueError("Educational module not found")
        return module

    def _get_or_create_progress(
        self, user_id: str, module_id: str
    ) -> UserProgress:
        record = self._repository.get_user_progress(
            user_id=UUID(user_id),
            module_id=UUID(module_id),
        )
        if record is not None:
            return record

        now = datetime.utcnow()
        return UserProgress(
            user_id=UUID(user_id),
            educational_module_id=UUID(module_id),
            status="not_started",
            progress_percentage=0,
            completed_sections=[],
            quiz_attempts=[],
            started_at=now,
            last_accessed_at=now,
            completed_at=None,
        )

    def _slugify(self, value: str) -> str:
        import re

        slug = value.strip().lower()
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug

    def get_module_card_payload(self, modules: Iterable[Module]) -> list[dict]:
        return [
            {
                "id": module.id,
                "slug": module.slug,
                "title": module.title,
                "description": module.description,
                "level": module.level,
                "estimatedTimeMinutes": module.estimatedTimeMinutes,
                "topicsCount": module.topicsCount,
                "questionsCount": module.quiz.questionsCount,
                "category": module.category,
                "tags": module.tags,
            }
            for module in modules
        ]

    def get_module_detail_payload(self, module: Module) -> dict:
        return {
            "id": module.id,
            "slug": module.slug,
            "title": module.title,
            "description": module.description,
            "level": module.level,
            "estimatedTimeMinutes": module.estimatedTimeMinutes,
            "topicsCount": module.topicsCount,
            "category": module.category,
            "tags": module.tags,
            "createdAt": module.createdAt,
            "learningObjectives": module.learningObjectives,
            "content": module.content,
            "topics": module.topics,
            "quiz": {
                "id": module.quiz.id,
                "title": module.quiz.title,
                "questionsCount": module.quiz.questionsCount,
                "passingScore": module.quiz.passingScore,
                "questions": [
                    {
                        "id": question.id,
                        "type": question.type,
                        "question": question.question,
                        "options": question.options or [],
                        "explanation": question.explanation,
                        "correctAnswer": question.correctAnswer,
                    }
                    for question in module.quiz.questions
                ],
            },
        }

    def _build_empty_progress(
        self, user_id: str, module_id: str
    ) -> UserModuleProgressDTO:
        return UserModuleProgressDTO(
            userId=user_id,
            moduleId=module_id,
            status="not_started",
            progressPercentage=0,
            completedSections=[],
            quizAttempts=[],
            startedAt=None,
            lastAccessedAt=None,
            completedAt=None,
        )

    def _serialize_progress(self, progress: UserProgress) -> UserModuleProgressDTO:
        return UserModuleProgressDTO(
            userId=str(progress.user_id),
            moduleId=str(progress.educational_module_id),
            status=progress.status,
            progressPercentage=progress.progress_percentage,
            completedSections=list(progress.completed_sections or []),
            quizAttempts=list(progress.quiz_attempts or []),
            startedAt=progress.started_at,
            lastAccessedAt=progress.last_accessed_at,
            completedAt=progress.completed_at,
        )

    def _calculate_progress_percentage(
        self,
        module: Module,
        completed_sections: list[str],
        quiz_attempts: list[dict],
    ) -> int:
        content_progress = self._calculate_content_progress(
            module=module,
            completed_sections=completed_sections,
        )
        if self._latest_quiz_is_passing(module=module, quiz_attempts=quiz_attempts):
            return 100 if self._is_content_completed(module, completed_sections) else content_progress
        return content_progress

    def _calculate_content_progress(
        self, module: Module, completed_sections: list[str]
    ) -> int:
        total_sections = max(len(module.content.sections), 1)
        completion_ratio = min(len(set(completed_sections)), total_sections) / total_sections
        return min(CONTENT_PROGRESS_WEIGHT, round(completion_ratio * CONTENT_PROGRESS_WEIGHT))

    def _is_content_completed(self, module: Module, completed_sections: list[str]) -> bool:
        return len(set(completed_sections)) >= max(len(module.content.sections), 1)

    def _latest_quiz_is_passing(
        self, module: Module, quiz_attempts: list[dict]
    ) -> bool:
        if not quiz_attempts:
            return False
        latest_attempt = quiz_attempts[-1]
        try:
            return int(latest_attempt.get("score", 0)) >= module.quiz.passingScore
        except (AttributeError, TypeError, ValueError):
            return False
