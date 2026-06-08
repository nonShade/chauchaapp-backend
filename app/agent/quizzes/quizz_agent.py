from __future__ import annotations

import ast
import json
import os
import re
from datetime import datetime
from typing import List, Literal, Optional

from agno.agent import Agent
from agno.models.nvidia import Nvidia
from agno.tools.tavily import TavilyTools
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

load_dotenv()

LevelType = Literal["Principiante", "Intermedio", "Avanzado"]
QuestionType = Literal["multiple_choice", "true_false", "single_choice", "fill_blank"]
PRACTICAL_SCENARIO_CUES = (
    "si ",
    "cuando ",
    "mientras ",
    "tienes ",
    "estas ",
    "quieres ",
    "vas a ",
    "debes ",
    "decides ",
    "recibes ",
    "observas ",
    "revisas ",
    "comparas ",
    "te ",
    "tu ",
    "tus ",
    "cliente ",
    "inversionista ",
    "participe ",
    "portafolio ",
    "cartera ",
    "fondo ",
)
THEORETICAL_PREFIXES = (
    "quien ",
    "que es ",
    "que significa ",
    "cual es ",
    "cuales son ",
    "que documento ",
    "que tipo ",
    "que riesgos ",
    "que activos ",
    "que entidad ",
    "quien regula ",
    "que regula ",
    "que indica ",
    "que define ",
)
THEORETICAL_TOKENS = (
    "definicion",
    "define",
    "significa",
    "regula",
    "regulador",
    "supervisa",
    "autoridad",
    "institucion",
    "documento",
    "lista",
    "tipos de",
    "es la",
    "son los",
)
MIN_PRACTICAL_QUESTION_RATIO = 0.7


class Section(BaseModel):
    id: str
    title: str
    content: str
    source: Optional[dict] = None


class Topic(BaseModel):
    id: str
    name: str


class Question(BaseModel):
    id: str
    type: QuestionType
    question: str
    options: Optional[List[str]] = None
    correctAnswer: Optional[int] = None
    explanation: Optional[str] = None

    @validator("options", always=True)
    def validate_options_for_choice(cls, v, values):
        qtype = values.get("type")
        if qtype in ("multiple_choice", "single_choice"):
            if not v or len(v) < 2:
                raise ValueError("choice questions require at least two options")
        return v

    @validator("correctAnswer", always=True)
    def validate_correct_answer(cls, v, values):
        qtype = values.get("type")
        opts = values.get("options")
        if qtype in ("multiple_choice", "single_choice"):
            if v is None:
                return 0
            if isinstance(v, list):
                v = v[0] if v else 0
            if isinstance(v, str):
                lower = v.strip().lower()
                if lower in ("verdadero", "true"):
                    v = 0
                elif lower in ("falso", "false"):
                    v = 1
                elif opts:
                    try:
                        v = opts.index(v)
                    except ValueError:
                        for i, opt in enumerate(opts):
                            if lower in str(opt).strip().lower():
                                v = i
                                break
                        else:
                            v = 0
                else:
                    v = 0
            if not isinstance(v, int):
                v = 0
            if opts:
                v = max(0, min(v, len(opts) - 1))
        return v


class Quiz(BaseModel):
    id: str
    title: str
    questionsCount: int = Field(..., gt=0)
    passingScore: int = Field(..., ge=0, le=100)
    questions: List[Question]

    @validator("questions")
    def validate_questions_count(cls, v, values):
        count = values.get("questionsCount")
        if count is None:
            return v
        if len(v) != count:
            raise ValueError("questionsCount must match length of questions list")
        return v


class Content(BaseModel):
    introduction: str
    sections: List[Section]
    practicalTips: List[str]


class Module(BaseModel):
    id: str
    slug: str
    title: str
    description: str
    level: LevelType
    estimatedTimeMinutes: int = Field(..., gt=0)
    category: str
    tags: List[str]
    topicsCount: int = Field(..., gt=0)
    createdAt: datetime
    learningObjectives: List[str]
    content: Content
    topics: List[Topic]
    quiz: Quiz

    @validator("description")
    def description_word_limit(cls, v: str):
        words = v.split()
        if len(words) > 20:
            raise ValueError("description must be 20 words or fewer")
        return v

    @validator("topics")
    def topics_count_matches(cls, v, values):
        expected = values.get("topicsCount")
        if expected is None:
            return v
        if len(v) != expected:
            raise ValueError("topicsCount must match length of topics list")
        return v


class QuizAttempt(BaseModel):
    attempt: int
    score: int = Field(..., ge=0, le=100)
    correctAnswers: int
    totalQuestions: int
    completedAt: datetime


class UserModuleProgress(BaseModel):
    userId: str
    moduleId: str
    status: Literal["not_started", "in_progress", "completed"] = "not_started"
    progressPercentage: int = Field(0, ge=0, le=100)
    completedSections: List[str] = []
    quizAttempts: List[QuizAttempt] = []
    startedAt: Optional[datetime] = None
    lastAccessedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None


class QuizzAgent:
    def __init__(self, use_sanity: bool = True):
        self._sanity_project = os.getenv("SANITY_PROJECT_ID")
        self._sanity_dataset = os.getenv("SANITY_DATASET", "production")
        self._sanity_token = os.getenv("SANITY_TOKEN")
        self.session_id = "quizz_agent_session"
        self.agent = self._create_agent()
        self._default_modules_cache: list[Module] | None = None

    def _get_nvidia_api_key(self) -> str:
        """
        Obtiene la clave de API de Nvidia con manejo de fallback.
        Intenta usar las claves en orden: NVIDIA_API_KEY, NVIDIA_API_KEY_FALLBACK, etc.
        """
        api_keys = [
            os.getenv("NVIDIA_API_KEY"),
            os.getenv("NVIDIA_API_KEY_FALLBACK"),
            os.getenv("NVIDIA_API_KEY_FALLBACK2"),
            os.getenv("NVIDIA_API_KEY_FALLBACK3"),
            os.getenv("NVIDIA_API_KEY_FALLBACK4"),
        ]

        for api_key in api_keys:
            if api_key and api_key.strip():
                return api_key

        raise ValueError(
            "No NVIDIA API keys found. Please configure NVIDIA_API_KEY "
            "or its fallback variants in your .env file."
        )

    def _create_agent(self) -> Agent:
        api_key = self._get_nvidia_api_key()
        model = Nvidia(id="nvidia/llama-3.3-nemotron-super-49b-v1", api_key=api_key)
        instructions = (
            "Eres un asistente para generar y validar módulos educativos financieros. "
            "Solo puedes usar el contexto provisto. "
            "Prioriza preguntas practicas basadas en escenarios reales del modulo. "
            "Cada pregunta debe presentar un escenario y pedir una decision o accion. "
            "Prohibido: definiciones, regulacion, listas de conceptos, preguntas tipo 'que es', "
            "'quien regula', 'cual es', 'que significa'. "
            "Devuelve SOLO JSON cuando se solicite un módulo, sin texto adicional."
        )
        tools = []
        agent = Agent(
            name="QuizzAgent",
            tools=tools,
            model=model,
            instructions=instructions,
            description="Agente para crear y validar módulos educativos usando GROQ",
            session_id=self.session_id,
            markdown=False,
        )
        return agent

    def _parse_json_content(self, content: str) -> dict | list:
        raw_content = content.strip()
        fenced_match = re.search(r"```(?:json)?\s*(.*?)```", raw_content, re.DOTALL | re.IGNORECASE)
        if fenced_match:
            raw_content = fenced_match.group(1).strip()

        start_candidates = [raw_content.find("{"), raw_content.find("[")]
        start_candidates = [value for value in start_candidates if value != -1]
        if start_candidates:
            start_index = min(start_candidates)
            end_index = max(raw_content.rfind("}"), raw_content.rfind("]"))
            if end_index > start_index:
                raw_content = raw_content[start_index : end_index + 1]

        raw_content = re.sub(r",\s*([}\]])", r"\1", raw_content)

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            try:
                parsed = ast.literal_eval(raw_content)
            except Exception as eval_exc:
                raise RuntimeError(
                    f"Failed to parse agent response: {eval_exc}"
                ) from exc
        if not isinstance(parsed, (dict, list)):
            raise RuntimeError("Agent response parsed to unsupported type")
        return parsed

    def _get_module_context(self, topic: str, country: str = "Chile") -> str:
        api_key = self._get_nvidia_api_key()
        search_agent = Agent(
            name="ModuleContextSearchAgent",
            tools=[TavilyTools()],
            model=Nvidia(id="nvidia/llama-3.3-nemotron-super-49b-v1", api_key=api_key),
            instructions=(
                "Tu unica funcion es buscar informacion con web_search_using_tavily. "
                "Usa EXACTAMENTE esa herramienta y nombre. "
                "No respondas con memoria previa. "
                "Si no encuentras un dato, indicalo como 'dato no encontrado'."
            ),
        )

        response = search_agent.run(
            f"""Usa web_search_using_tavily para buscar AHORA mismo fuentes confiables sobre:
            1. conceptos clave de {topic} en finanzas personales
            2. definiciones claras y actuales de terminos esenciales
            3. buenas practicas y riesgos frecuentes

            Limita la informacion al contexto de {country}. Si algun dato numerico
            no esta disponible o no es verificable, marca 'dato no encontrado'."""
        )
        context = response.content if response.content else ""
        return context[:2000]

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
        return slug.strip("-") or "modulo"

    def _normalize_generated_module(
        self, data: dict, topic: str, level: LevelType
    ) -> dict:
        title = data.get("title") or data.get("name") or topic
        description = data.get("description") or f"Modulo educativo sobre {topic}."
        slug = data.get("slug") or self._slugify(title)
        created_at = data.get("createdAt") or datetime.utcnow().isoformat()

        content_raw = data.get("content") if isinstance(data.get("content"), dict) else {}
        introduction = (
            content_raw.get("introduction")
            or data.get("introduction")
            or ""
        )
        sections = content_raw.get("sections") or data.get("sections") or []
        practical_tips = (
            content_raw.get("practicalTips")
            or data.get("practicalTips")
            or []
        )
        content = {
            "introduction": introduction,
            "sections": sections,
            "practicalTips": practical_tips,
        }

        topics_raw = data.get("topics") or []
        normalized_topics = []
        for item in topics_raw:
            if not isinstance(item, dict):
                continue
            topic_id = item.get("id") or self._slugify(item.get("name") or item.get("title") or "topic")
            topic_name = item.get("name") or item.get("title") or topic_id
            normalized_topics.append({"id": topic_id, "name": topic_name})

        if not normalized_topics and sections:
            for section in sections:
                if not isinstance(section, dict):
                    continue
                section_id = section.get("id") or self._slugify(section.get("title") or "topic")
                section_name = section.get("title") or section_id
                normalized_topics.append({"id": section_id, "name": section_name})

        topics_count = data.get("topicsCount") or len(normalized_topics) or 1

        quiz_raw = data.get("quiz") or data.get("quizzes") or {}
        if isinstance(quiz_raw, list):
            quiz_raw = quiz_raw[0] if quiz_raw else {}
        if not isinstance(quiz_raw, dict):
            quiz_raw = {}

        questions_raw = quiz_raw.get("questions") or data.get("questions") or []
        normalized_questions = []
        for index, question in enumerate(questions_raw, start=1):
            if not isinstance(question, dict):
                continue
            qtype_raw = question.get("type") or "single_choice"
            qtype = str(qtype_raw).replace("-", "_")
            if qtype not in (
                "multiple_choice",
                "single_choice",
                "true_false",
            ):
                qtype = "single_choice"
            qtext = question.get("question") or question.get("title") or f"Pregunta {index}"
            options = question.get("options")
            if not isinstance(options, list):
                options = []
            if qtype in ("multiple_choice", "single_choice") and len(options) < 2:
                options = ["Opcion A", "Opcion B"]
            if qtype == "true_false" and len(options) < 2:
                options = ["Verdadero", "Falso"]
            correct_answer = question.get("correctAnswer")
            if isinstance(correct_answer, list):
                correct_answer = correct_answer[0] if correct_answer else 0
            if isinstance(correct_answer, str) and options:
                normalized_answer = correct_answer.strip().lower()
                if normalized_answer in ("verdadero", "true"):
                    correct_answer = 0
                elif normalized_answer in ("falso", "false"):
                    correct_answer = 1
                else:
                    try:
                        correct_answer = options.index(correct_answer)
                    except ValueError:
                        for i, opt in enumerate(options):
                            if normalized_answer in str(opt).strip().lower():
                                correct_answer = i
                                break
                        else:
                            correct_answer = 0
            if isinstance(correct_answer, int) and options:
                correct_answer = max(0, min(correct_answer, len(options) - 1))

            if qtype in ("multiple_choice", "single_choice", "true_false"):
                if correct_answer is None or not isinstance(correct_answer, int):
                    correct_answer = 0
                correct_answer = max(0, min(correct_answer, len(options) - 1))
            if not options:
                options = ["Opcion A", "Opcion B"]
                correct_answer = 0
            normalized_questions.append(
                {
                    "id": question.get("id") or f"q{index}",
                    "type": qtype,
                    "question": qtext,
                    "options": options,
                    "correctAnswer": correct_answer,
                    "explanation": question.get("explanation"),
                }
            )

        if not normalized_questions:
            normalized_questions = [
                {
                    "id": "q1",
                    "type": "single_choice",
                    "question": f"Tienes una situacion real relacionada con {topic}. Que accion tomas primero?",
                    "options": ["Accion correcta", "Accion incorrecta"],
                    "correctAnswer": 0,
                    "explanation": "Aplica el concepto en un caso real y prioriza la accion correcta.",
                }
            ]

        questions_count = quiz_raw.get("questionsCount") or len(normalized_questions)
        quiz = {
            "id": quiz_raw.get("id") or "quiz-1",
            "title": quiz_raw.get("title") or f"Quiz: {title}",
            "questionsCount": questions_count,
            "passingScore": quiz_raw.get("passingScore") or 70,
            "questions": normalized_questions,
        }

        return {
            "id": data.get("id") or f"modulo-{self._slugify(title)}",
            "slug": slug,
            "title": title,
            "description": description,
            "level": data.get("level") or level,
            "estimatedTimeMinutes": int(data.get("estimatedTimeMinutes") or 15),
            "category": data.get("category") or "general",
            "tags": data.get("tags") or [],
            "topicsCount": int(topics_count),
            "createdAt": created_at,
            "learningObjectives": data.get("learningObjectives") or [],
            "content": content,
            "topics": normalized_topics,
            "quiz": quiz,
        }

    def _is_practical_question(self, question_text: str) -> bool:
        normalized = re.sub(r"\s+", " ", question_text.strip().lower())
        normalized = normalized.lstrip("¿")
        if not normalized:
            return False
        if any(cue in normalized for cue in PRACTICAL_SCENARIO_CUES):
            return True
        if any(normalized.startswith(prefix) for prefix in THEORETICAL_PREFIXES):
            return False
        if any(token in normalized for token in THEORETICAL_TOKENS):
            return False
        return True

    def _practical_question_ratio(self, questions: list[Question]) -> float:
        total = max(len(questions), 1)
        practical = sum(
            1 for question in questions if self._is_practical_question(question.question)
        )
        return practical / total

    def generate_module_from_topic(self, topic: str, level: LevelType) -> Module:
        context = self._get_module_context(topic=topic)
        prompt = f"""CONTEXTO VERIFICADO (usar solo estos datos):
        {context}

        INSTRUCCION:
        Genera un modulo educativo de finanzas personales con nivel '{level}'.
        - Usa SOLO la informacion del contexto de arriba.
        - Si el contexto dice 'dato no encontrado', no uses ese dato.
        - No inventes cifras ni hechos.
        - La descripcion debe tener maximo 20 palabras.
        - topicsCount debe coincidir con la cantidad de topics.
        - questionsCount debe coincidir con el numero de preguntas.
        - El quiz debe tener entre 8 y 12 preguntas.
        - Incluye secciones con ids unicos, contenido claro y coherente.
        - El quiz debe tener preguntas sin ambiguedad y respuestas correctas.
        - Cada pregunta debe ser practica: escenario real del modulo + decision/accion.
        - Usa formato recomendado: "Escenario: ... ? Que haces primero?" o "Estas ... ? Que decision tomas?".
        - Evita preguntas teoricas o definiciones directas.
        - Prohibido: "que es", "quien regula", "cual es", "que significa", listas de conceptos.
        - Opciones deben ser acciones concretas, no definiciones.
        - Evita true_false salvo que el escenario requiera verificar una accion.
        - Prohibido: preguntas tipo fill_blank (rellenar espacio en blanco).
        - La explicacion debe dar feedback practico y conectar con la seccion del modulo.
        - Responde SOLO con JSON valido para el esquema Module.
        - Usa comillas dobles en todas las claves y strings.
        - No uses comillas simples ni comentarios.
        - No uses markdown ni fences de codigo.
        - Incluye SIEMPRE estos campos obligatorios a nivel raiz:
          id, slug, title, description, level, estimatedTimeMinutes, category,
          tags, topicsCount, createdAt, learningObjectives, content, topics, quiz.
        - content debe incluir: introduction, sections (lista), practicalTips (lista).
        - topics debe ser lista de objetos con id y name.
        - quiz debe ser un OBJETO (no lista) con: id, title, questionsCount,
          passingScore, questions (lista).
        - REGLAS OBLIGATORIAS para cada pregunta del quiz:
          * type debe ser SOLO "multiple_choice" o "single_choice" (nunca fill_blank).
          * options es OBLIGATORIO: una lista con exactamente 3 o 4 opciones de texto.
          * correctAnswer es OBLIGATORIO: un entero (0, 1, 2 o 3) que indique el indice de la opcion correcta.
          * explanation es OBLIGATORIO: texto que explique por que esa es la respuesta correcta.
          * NUNCA omitas options o correctAnswer.
        """

        last_error: Exception | None = None
        for _attempt in range(3):
            response = self.agent.run(prompt)
            content = response.content
            if content is None:
                last_error = RuntimeError("Agent returned no content")
                continue

            if isinstance(content, Module):
                return content

            if isinstance(content, str):
                try:
                    parsed = self._parse_json_content(content)
                except RuntimeError as exc:
                    last_error = exc
                    continue
            else:
                parsed = (
                    content.model_dump() if hasattr(content, "model_dump") else content
                )

            if isinstance(parsed, dict) and parsed.get("error"):
                last_error = RuntimeError(f"Agent error: {parsed['error']}")
                continue

            normalized = (
                self._normalize_generated_module(parsed, topic=topic, level=level)
                if isinstance(parsed, dict)
                else parsed
            )
            try:
                module = Module.parse_obj(normalized)
            except Exception as exc:
                last_error = exc
                continue

            if (
                self._practical_question_ratio(module.quiz.questions)
                < MIN_PRACTICAL_QUESTION_RATIO
            ):
                last_error = RuntimeError("Quiz questions are not practical enough")
                continue

            return module

        raise RuntimeError(
            f"Failed to generate module after 3 attempts: {last_error}"
        )

    def _default_modules_data(self) -> list[dict]:
        return [
            {
                "id": "module_credits_1",
                "slug": "entendiendo-los-creditos",
                "title": "Entendiendo los Creditos",
                "description": "Aprende que son los creditos, como funcionan las tasas de interes y como elegir el mejor para ti.",
                "level": "Principiante",
                "estimatedTimeMinutes": 15,
                "category": "creditos",
                "tags": ["creditos", "tasas", "endeudamiento"],
                "topicsCount": 4,
                "createdAt": "2024-03-20T00:00:00",
                "learningObjectives": [
                    "Entender el costo total de un credito con el CAE",
                    "Diferenciar tasa nominal y tasa efectiva",
                    "Evaluar el impacto del plazo en el pago total",
                ],
                "content": {
                    "introduction": "Los creditos son herramientas financieras que te permiten acceder a dinero que no tienes en el momento, con el compromiso de devolverlo en el futuro junto con intereses.",
                    "sections": [
                        {
                            "id": "cae",
                            "title": "CAE (Carga Anual Equivalente)",
                            "content": "Es el indicador mas importante al comparar creditos. Incluye todos los costos: tasa de interes, seguros, comisiones y gastos asociados. Mientras mas bajo el CAE, mejor para ti.",
                        },
                        {
                            "id": "tasa-nominal-efectiva",
                            "title": "Tasa Nominal vs Tasa Efectiva",
                            "content": "La tasa nominal es la tasa base anunciada. La tasa efectiva incluye la capitalizacion de intereses (interes sobre interes), por lo que siempre es igual o mayor a la nominal.",
                        },
                        {
                            "id": "plazo-credito",
                            "title": "Plazo del credito",
                            "content": "Plazos mas largos significan cuotas mas bajas, pero pagas mas intereses en total. Plazos mas cortos implican cuotas mas altas, pero menos intereses totales.",
                        },
                    ],
                    "practicalTips": [
                        "Siempre compara el CAE entre distintas instituciones",
                        "Lee la letra chica sobre seguros y comisiones",
                        "Calcula cuanto pagaras en total, no solo la cuota mensual",
                        "No te endeudes por mas del 30% de tus ingresos mensuales",
                    ],
                },
                "topics": [
                    {"id": "topic_cae", "name": "CAE"},
                    {"id": "topic_tasa_nominal", "name": "Tasa nominal"},
                    {"id": "topic_tasa_efectiva", "name": "Tasa efectiva"},
                    {"id": "topic_comparacion", "name": "Comparacion de creditos"},
                ],
                "quiz": {
                    "id": "quiz_credits_1",
                    "title": "Quiz: Entendiendo los Creditos",
                    "questionsCount": 2,
                    "passingScore": 70,
                    "questions": [
                        {
                            "id": "q1",
                            "type": "single_choice",
                            "question": "Estas comparando dos creditos con la misma cuota mensual, pero CAE distinto. Que haces primero para decidir?",
                            "options": [
                                "Comparo el CAE y costos asociados totales",
                                "Elijo el que tenga la cuota mas baja sin revisar costos",
                                "Elijo el que tenga mas publicidad",
                            ],
                            "correctAnswer": 0,
                            "explanation": "Aplicas el CAE para comparar el costo total real del credito.",
                        },
                        {
                            "id": "q2",
                            "type": "single_choice",
                            "question": "Necesitas un credito y te ofrecen tasa nominal baja pero plazo largo. Que accion te ayuda a decidir mejor?",
                            "options": [
                                "Calcular el total pagado y comparar con un plazo mas corto",
                                "Aceptar de inmediato por la tasa nominal baja",
                                "Elegir el plazo mas largo solo por cuota baja",
                            ],
                            "correctAnswer": 0,
                            "explanation": "Comparar total pagado y plazo muestra el impacto real en intereses.",
                        },
                    ],
                },
            },
            {
                "id": "module_budget_101",
                "slug": "presupuesto-personal-101",
                "title": "Presupuesto Personal 101",
                "description": "Crea tu primer presupuesto y aprende a controlar tus gastos de forma efectiva.",
                "level": "Principiante",
                "estimatedTimeMinutes": 20,
                "category": "presupuesto",
                "tags": ["presupuesto", "gastos", "ahorro"],
                "topicsCount": 3,
                "createdAt": "2024-03-22T00:00:00",
                "learningObjectives": [
                    "Identificar ingresos y gastos mensuales",
                    "Aplicar una regla simple de distribucion",
                    "Crear un fondo de emergencia basico",
                ],
                "content": {
                    "introduction": "Un presupuesto te ayuda a decidir como usar tu dinero. Veras una vista clara de tus ingresos, tus gastos y tu capacidad de ahorro.",
                    "sections": [
                        {
                            "id": "ingresos-gastos",
                            "title": "Mapa de ingresos y gastos",
                            "content": "Anota todas tus fuentes de ingreso y clasifica tus gastos en fijos y variables. Esto revela tus patrones de consumo.",
                        },
                        {
                            "id": "regla-50-30-20",
                            "title": "Regla 50/30/20",
                            "content": "Destina 50% a necesidades, 30% a deseos y 20% a ahorro o pago de deudas. Ajusta los porcentajes segun tu realidad.",
                        },
                    ],
                    "practicalTips": [
                        "Separa primero el ahorro antes de gastar",
                        "Revisa tu presupuesto cada semana",
                        "Usa metas pequeñas para mantener la motivacion",
                    ],
                },
                "topics": [
                    {"id": "topic_ingresos_gastos", "name": "Ingresos y gastos"},
                    {"id": "topic_regla_50_30_20", "name": "Regla 50/30/20"},
                    {"id": "topic_fondo_emergencia", "name": "Fondo de emergencia"},
                ],
                "quiz": {
                    "id": "quiz_budget_101",
                    "title": "Quiz: Presupuesto Personal 101",
                    "questionsCount": 2,
                    "passingScore": 70,
                    "questions": [
                        {
                            "id": "q1",
                            "type": "single_choice",
                            "question": "Recibes tu sueldo y quieres aplicar la regla 50/30/20. Cual es tu primer paso?",
                            "options": [
                                "Separar el 20% para ahorro o deuda antes de gastar",
                                "Gastar primero y ahorrar lo que quede",
                                "Asignar todo a deseos porque es inicio de mes",
                            ],
                            "correctAnswer": 0,
                            "explanation": "Separar el ahorro primero hace aplicable la regla en la vida real.",
                        },
                        {
                            "id": "q2",
                            "type": "single_choice",
                            "question": "Al hacer tu presupuesto, detectas que tus gastos variables suben cada semana. Que accion practica tomas?",
                            "options": [
                                "Revisar gastos semanalmente y ajustar categorias",
                                "Ignorar el problema hasta fin de mes",
                                "Pedir un credito para cubrir el exceso",
                            ],
                            "correctAnswer": 0,
                            "explanation": "Revisar seguido permite corregir el presupuesto antes de salirte del plan.",
                        },
                    ],
                },
            },
        ]

    def get_default_modules(self) -> list[Module]:
        if self._default_modules_cache is None:
            self._default_modules_cache = [
                Module.parse_obj(data) for data in self._default_modules_data()
            ]
        return list(self._default_modules_cache)

    def get_default_progress(
        self, module_id: str, user_id: str | None = None
    ) -> UserModuleProgress:
        resolved_user_id = user_id or "guest"
        if module_id == "module_credits_1":
            return UserModuleProgress(
                userId=resolved_user_id,
                moduleId=module_id,
                status="completed",
                progressPercentage=100,
                completedSections=["cae", "tasa-nominal-efectiva", "plazo-credito"],
                quizAttempts=[
                    QuizAttempt(
                        attempt=1,
                        score=100,
                        correctAnswers=2,
                        totalQuestions=2,
                        completedAt=datetime(2024, 4, 9, 0, 0),
                    ),
                    QuizAttempt(
                        attempt=2,
                        score=50,
                        correctAnswers=1,
                        totalQuestions=2,
                        completedAt=datetime(2024, 4, 4, 0, 0),
                    ),
                ],
                startedAt=datetime(2024, 4, 3, 0, 0),
                lastAccessedAt=datetime(2024, 4, 9, 0, 0),
                completedAt=datetime(2024, 4, 9, 0, 0),
            )

        return UserModuleProgress(
            userId=resolved_user_id,
            moduleId=module_id,
            status="not_started",
            progressPercentage=0,
            completedSections=[],
            quizAttempts=[],
            startedAt=None,
            lastAccessedAt=None,
            completedAt=None,
        )

    def create_module_from_sanity_doc(self, doc: dict) -> Module:
        # map fields from Sanity document to Module model expected structure
        created_at_raw = doc.get("_createdAt")
        created_at = (
            datetime.fromisoformat(created_at_raw)
            if isinstance(created_at_raw, str) and created_at_raw
            else datetime.utcnow()
        )
        data = {
            "id": doc.get("_id") or doc.get("id"),
            "slug": doc.get("slug", {}).get("current")
            if isinstance(doc.get("slug"), dict)
            else doc.get("slug"),
            "title": doc.get("title", ""),
            "description": doc.get("description", ""),
            "level": doc.get("level", "Principiante"),
            "estimatedTimeMinutes": int(doc.get("estimatedTimeMinutes", 15)),
            "category": doc.get("category", "general"),
            "tags": doc.get("tags", []),
            "topicsCount": int(doc.get("topicsCount", 0)),
            "createdAt": created_at,
            "learningObjectives": doc.get("learningObjectives", []),
            "content": doc.get("content", {}),
            "topics": doc.get("topics", []),
            "quiz": doc.get("quiz", {}),
        }
        return Module.parse_obj(data)

    def create_module(self, data: dict) -> Module:
        return Module.parse_obj(data)

    def generate_quiz_from_module(self, module: Module) -> dict:
        prompt = (
            f"Genera un JSON con la estructura completa de quiz para el módulo '{module.title}'. "
            "Usa el contenido del modulo para crear preguntas practicas basadas en escenarios reales. "
            "Cada pregunta debe pedir una decision o accion. "
            "Prohibido: definiciones, regulacion, listas de conceptos, 'que es', 'quien regula'. "
            "Usa escenarios con 'tu' o 'te' y decisiones claras. "
            "Opciones deben ser acciones concretas. Evita true_false salvo que el escenario lo requiera. "
            "La explicacion debe dar feedback practico y conectar con una seccion o tip. "
            "Incluye id, title, questionsCount, passingScore y questions. Responde SOLO con JSON."
        )
        response = self.agent.run(prompt)
        content = response.content
        if content is None:
            raise RuntimeError("Agent returned no content")
        try:
            if isinstance(content, str):
                parsed = self._parse_json_content(content)
            else:
                parsed = (
                    content.model_dump() if hasattr(content, "model_dump") else content
                )
        except Exception as e:
            raise RuntimeError(f"Failed to parse agent response: {e}")
        return parsed

    def serialize_module(self, module: Module) -> dict:
        return module.dict()

    def serialize_progress(self, progress: UserModuleProgress) -> dict:
        return progress.dict()


quizz_agent = QuizzAgent()

__all__ = [
    "quizz_agent",
    "QuizzAgent",
    "Module",
    "Content",
    "Section",
    "Quiz",
    "Question",
    "UserModuleProgress",
    "QuizAttempt",
    "Topic",
]
