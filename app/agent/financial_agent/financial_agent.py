
import os
import json

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.tavily import TavilyTools

from app.agent._gemini_keys import next_gemini_api_key
from app.agent._gemini_run import run_with_key_rotation

load_dotenv()


class FinancialPlanningResource(BaseModel):
    title: str
    url: str


class FinancialPlanningTip(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    category: str
    keyPoints: list[str]
    actionItems: list[str]
    resources: list[FinancialPlanningResource]


class FinancialPlanningTipsPayload(BaseModel):
    financialPlanningTips: list[FinancialPlanningTip] = Field(
        ..., min_length=1, max_length=10
    )


class FinancialPlanningAgent:
    def __init__(self) -> None:
        self.session_id = "financial_planning_session"
        self.agent = self._create_agent()

    def _get_nvidia_api_key(self) -> str:
        """Round-robin pick among configured GEMINI_API_KEY* entries."""
        return next_gemini_api_key()

    def _create_agent(self, api_key: str | None = None) -> Agent:
        api_key = api_key or self._get_nvidia_api_key()
        model = Gemini(
            id="gemini-2.5-flash",
            api_key=api_key,
            temperature=0.3,
            retries=3,
            delay_between_retries=2,
            exponential_backoff=True,
            thinking_budget=0,
        )
        instructions = """
Eres un experto en planificacion financiera para Chile.
Reglas criticas:
1) Usa SIEMPRE la herramienta web_search para verificar datos actuales.
2) Responde SOLO con JSON valido, sin texto extra.
3) No inventes numeros ni fuentes. Si no hay dato, omite numero.
4) Devuelve entre 5 y 7 tips.
5) Cada tip incluye id (string), title, description, icon, category,
   keyPoints (4 items), actionItems (4 items), resources (1-3 items con title y url).
6) Usa categoria en: emergencia, metas, deudas, retiro, habitos, presupuesto, inversion.
7) Usa icon en: shield, target, trending-up, calendar, piggybank, wallet, chart-line.
"""
        return Agent(
            name="FinancialPlanningAgent",
            tools=[TavilyTools()],
            model=model,
            instructions=instructions,
            description="Agente para tips de planificacion financiera reciente",
            session_id=self.session_id,
            markdown=True,
        )

    def get_financial_planning_tips(self) -> list[FinancialPlanningTip]:
        payload = self._generate_financial_planning_payload()
        return payload.financialPlanningTips

    def _generate_financial_planning_payload(self) -> FinancialPlanningTipsPayload:
        prompt = self._build_prompt()
        response = run_with_key_rotation(self._create_agent, prompt)
        payload = self._parse_response_payload(response)

        if payload.financialPlanningTips:
            return payload

        retry_prompt = self._build_prompt(retry=True)
        response = run_with_key_rotation(self._create_agent, retry_prompt)
        payload = self._parse_response_payload(response)

        if not payload.financialPlanningTips:
            raise ValueError("Agent returned empty financialPlanningTips")

        return payload

    def _build_prompt(self, retry: bool = False) -> str:
        retry_note = (
            "Responde SOLO con JSON valido. NO incluyas markdown, ni texto adicional."
            if retry
            else ""
        )
        return f"""
Busca en web_search fuentes chilenas recientes (CMF, SII, AFP, Superintendencias).
Genera tips de planificacion financiera general (no personalizados).
Devuelve JSON con estructura:
{{
  "financialPlanningTips": [
    {{
      "id": "1",
      "title": "...",
      "description": "...",
      "icon": "shield|target|trending-up|calendar|piggybank|wallet|chart-line",
      "category": "emergencia|metas|deudas|retiro|habitos|presupuesto|inversion",
      "keyPoints": ["...", "...", "...", "..."],
      "actionItems": ["...", "...", "...", "..."],
      "resources": [
        {{"title": "...", "url": "https://..."}}
      ]
    }}
  ]
}}
{retry_note}
"""

    def _parse_response_payload(self, response) -> FinancialPlanningTipsPayload:
        if response is None or response.content is None:
            raise ValueError("Agent returned no content")

        content = response.content
        if not isinstance(content, str):
            content_dict = (
                content.model_dump() if hasattr(content, "model_dump") else content
            )
            return FinancialPlanningTipsPayload(**content_dict)

        raw_content = content.strip()
        if raw_content.startswith("```json"):
            raw_content = raw_content.replace("```json", "").replace("```", "").strip()

        content_dict = json.loads(raw_content)
        return FinancialPlanningTipsPayload(**content_dict)


financial_planning_agent = FinancialPlanningAgent()

__all__ = [
    "FinancialPlanningAgent",
    "FinancialPlanningTip",
    "FinancialPlanningResource",
    "FinancialPlanningTipsPayload",
    "financial_planning_agent",
]
