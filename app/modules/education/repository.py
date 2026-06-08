from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.education.entities import EducationalModule, UserProgress
from app.modules.quizzes.entities import AnswerOption, Question, Quiz


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

    def _sanitize_correct_answer(self, correct_answer, options):
        if isinstance(correct_answer, list):
            correct_answer = correct_answer[0] if correct_answer else 0
        if isinstance(correct_answer, str):
            lower = correct_answer.strip().lower()
            if lower in ("verdadero", "true"):
                correct_answer = 0
            elif lower in ("falso", "false"):
                correct_answer = 1
            elif options:
                try:
                    correct_answer = options.index(correct_answer)
                except ValueError:
                    for i, opt in enumerate(options):
                        if lower in str(opt).strip().lower():
                            correct_answer = i
                            break
                    else:
                        correct_answer = 0
            else:
                correct_answer = 0
        if not isinstance(correct_answer, int):
            correct_answer = 0
        if options:
            correct_answer = max(0, min(correct_answer, len(options) - 1))
        return correct_answer

    def create_module(self, module) -> EducationalModule:
        quiz_data = module.quiz
        questions = quiz_data.questions if quiz_data else []

        sanitized_questions = []
        for q in questions:
            opts = q.options or []
            correct = self._sanitize_correct_answer(q.correctAnswer, opts)
            q.correctAnswer = correct
            sanitized_questions.append({
                "id": q.id,
                "type": q.type,
                "question": q.question,
                "options": opts,
                "explanation": q.explanation,
                "correctAnswer": correct,
            })

        if quiz_data:
            quiz_data.questionsCount = len(sanitized_questions)
            for i, q in enumerate(quiz_data.questions):
                q.correctAnswer = sanitized_questions[i]["correctAnswer"]

        record = EducationalModule(
            educational_module_id=UUID(module.id),
            title=module.title,
            description=module.description,
            content=module.json(),
            duration=module.estimatedTimeMinutes,
            difficulty=module.level,
        )
        self.db.add(record)
        self.db.flush()

        quiz_record = Quiz(
            educational_module_id=record.educational_module_id,
            title=quiz_data.title if quiz_data else None,
        )
        self.db.add(quiz_record)
        self.db.flush()

        for q_data in sanitized_questions:
            question_record = Question(
                quiz_id=quiz_record.quiz_id,
                question_text=q_data["question"],
            )
            self.db.add(question_record)
            self.db.flush()

            for opt_text in (q_data["options"] or []):
                is_correct = (q_data["options"].index(opt_text) == q_data["correctAnswer"])
                self.db.add(AnswerOption(
                    question_id=question_record.question_id,
                    answer_text=opt_text,
                    is_correct=is_correct,
                ))

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
