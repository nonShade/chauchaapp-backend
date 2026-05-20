import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from agno.agent import Agent
from agno.models.nvidia import Nvidia
from agno.tools.tavily import TavilyTools

load_dotenv()


class DailyTip(BaseModel):
    """Modelo para un tip financiero individual."""
    titulo: str = Field(..., description="Título del tip financiero")
    texto: str = Field(...,
                       description="Contenido detallado del tip financiero")
    categoria: str = Field(...,
                           description="Categoría a la que pertenece el tip")
    day_of_week: Optional[int] = Field(
        None,
        description="Día de la semana (0=Lunes, 6=Domingo). Opcional para tips individuales."
    )


class DailyTipWeekly(BaseModel):
    """Modelo para un tip financiero en un batch semanal (day_of_week requerido)."""
    titulo: str = Field(..., description="Título del tip financiero")
    texto: str = Field(...,
                       description="Contenido detallado del tip financiero")
    categoria: str = Field(...,
                           description="Categoría a la que pertenece el tip")
    day_of_week: int = Field(
        ...,
        description="Día de la semana (0=Lunes, 6=Domingo). Requerido para batch semanal.",
        ge=0,
        le=6
    )


class DailyTipBatch(BaseModel):
    """Modelo para un lote de 7 tips financieros semanales."""
    tips: list[DailyTipWeekly] = Field(
        ...,
        description="Lista de exactamente 7 tips financieros para la semana"
    )

    def __init__(self, **data):
        super().__init__(**data)
        if len(self.tips) != 7:
            raise ValueError(
                f"Se esperaban exactamente 7 tips, se recibieron: {len(self.tips)}"
            )


class DailyTipsAgent:
    """Agente para generar tips financieros diarios usando modelos de Nvidia.

    Utiliza agno con Structured Output (Pydantic models) para garantizar
    respuestas válidas y tipadas.
    """

    # Categorías permitidas para los tips
    ALLOWED_CATEGORIES = [
        "Sueldo mínimo",
        "Combustible",
        "Alimentos",
        "Vivienda",
        "Transporte",
        "Servicios básicos",
        "Impuestos",
        "Créditos",
        "Ahorro",
        "Inversiones",
    ]
    ECONOMIC_PSYCHOLOGY_FRAMEWORK = """
    BASE DE PSICOLOGÍA ECONÓMICA (Chile, basada en CEPEC UFRO y lineamientos internos):
    - Diferenciar necesidad vs deseo antes de comprar.
    - Regla de espera: 24 horas (o 30 días en compras de alto monto) para compras no esenciales.
    - Registrar emoción asociada a cada compra para detectar gatillos (estrés, tristeza, aburrimiento, euforia).
    - Presupuesto hedónico: asignar un monto fijo y pequeño para "gustitos" sin romper el plan financiero.
    - Aumentar fricción al gastar online: eliminar tarjetas guardadas, desactivar compras en 1 clic y notificaciones.
    - Preferir efectivo para compras sensibles al impulso (aumenta el "dolor de pagar").
    - Usar listas y presupuesto previo para reducir compras impulsivas.
    - Cuidar sesgos conductuales: efecto manada, sesgo del presente, anclaje y FOMO por escasez/urgencia.
    - Técnicas de autocontrol: 10-10-10 y toma de perspectiva en tercera persona ("técnica del teatro").
    - Evitar decisiones financieras complejas con fatiga mental alta.
    - Resistir neuromarketing en retail: caja, rutas de tienda, estímulos sensoriales y productos agrupados.
    - En temporadas de alta emoción (rebajas/fiestas), definir tope de gasto ANTES de mirar ofertas.
    - Fórmula recomendada del presupuesto: ingreso total - ahorro = ingreso disponible.
    - Carga de deuda mensual recomendada: no superar 40% del ingreso neto.
    """

    def __init__(self):
        """Inicializa el agente con las claves de API de Nvidia con fallback."""
        self.agent = self._create_agent()
        self.session_id = "daily_tips_session"

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
        """
        Crea y configura el agente diario de tips financieros.

        Utiliza:
        - Structured output con Pydantic models
        - Instructions explícitas para mejor control del comportamiento
        - Session tracking para contexto de conversación

        Returns:
            Agent: Agente configurado con el modelo de Nvidia
        """
        api_key = self._get_nvidia_api_key()

        model = Nvidia(
            id="qwen/qwen3-coder-480b-a35b-instruct",
            api_key=api_key,
        )
        instructions = f"""Eres un experto en finanzas personales para Chile.
            Categorías permitidas: {', '.join(self.ALLOWED_CATEGORIES)}
            Marco de psicología económica que DEBES usar:
            {self.ECONOMIC_PSYCHOLOGY_FRAMEWORK}

            REGLAS ABSOLUTAS:
            1. Todos los tips deben ser específicos del contexto económico chileno (CLP, AFP, SII, UF).
            2. NUNCA inventes valores numéricos. Si un tip menciona cifras, DEBES haberlas obtenido
            con la herramienta web_search ANTES de incluirlas.
            3. Si no tienes datos actualizados de una cifra, omite el número o usa una referencia
            genérica como "según el valor vigente de la UF".
            4. Usa SOLO las categorías permitidas.
            5. Cada tip debe incluir al menos una estrategia conductual concreta y accionable.
            6. Evita consejos genéricos: debe ser aplicable hoy por una persona real.
            7. Responde SIEMPRE con el JSON exacto requerido, sin texto adicional."""

        agent = Agent(
            name="DailyTipsAgent",
            tools=[TavilyTools()],
            model=model,
            instructions=instructions,
            description="Agente para generar tips financieros diarios personalizados para Chile",
            session_id="daily_tips_session",
            markdown=True,
        )

        return agent

    def generate_daily_tip(self) -> DailyTip:
        """
        Genera un tip financiero diario individual.

        Returns:
            DailyTip: Objeto con titulo, texto y categoria

        Raises:
            Exception: Si falla la generación del tip
        """
        context = self._get_chile_context()
        categories_str = ', '.join(self.ALLOWED_CATEGORIES)
        prompt = f"""CONTEXTO ECONÓMICO REAL (obtenido con búsqueda web, NO inventado):
        {context}

        MARCO CONDUCTUAL OBLIGATORIO:
        {self.ECONOMIC_PSYCHOLOGY_FRAMEWORK}

        INSTRUCCIÓN: Genera 1 tip financiero para Chile.
        - Usa SOLO los datos del contexto de arriba
        - Si el contexto dice "dato no encontrado" para algo, NO lo incluyas en el tip
        - Integra al menos 1 estrategia de psicología económica del marco conductual
        - El tip debe incluir una micro-acción concreta para hoy
        - Categoría DEBE ser una de: {categories_str}
        - Responde SOLO con JSON, sin texto adicional"""

        try:
            response = self.agent.run(prompt, output_schema=DailyTip)
            if response.content is None:
                raise ValueError("El modelo no devolvió un contenido válido")
            return response.content
        except Exception as e:
            raise Exception(f"Error al generar tip diario: {str(e)}")

    def generate_weekly_tips_batch(self) -> list[DailyTipWeekly]:
        """
        Genera 7 tips financieros en UNA SOLA llamada a la IA.
        Optimizado para usar modelos gratuitos de Nvidia sin limites de rate.

        Usa Structured Output (output_schema) para validación automática.

        Returns:
            list[DailyTip]: Lista de exactamente 7 tips validados

        Raises:
            Exception: Si falla la generación o validación de tips
        """
        context = self._get_chile_context()
        categories_str = ', '.join(self.ALLOWED_CATEGORIES)

        prompt = f"""CONTEXTO ECONÓMICO REAL DE CHILE (obtenido con búsqueda web):
        {context}

        MARCO CONDUCTUAL OBLIGATORIO:
        {self.ECONOMIC_PSYCHOLOGY_FRAMEWORK}

        INSTRUCCIÓN: Genera exactamente 7 tips financieros para Chile (lunes a domingo).

        REGLAS ESTRICTAS:
        - Usa ÚNICAMENTE los números del contexto de arriba
        - Si el contexto marca "dato no encontrado", NO uses ese número
        - Cada tip debe aplicar al menos 1 estrategia de psicología económica
        - No repitas la misma estrategia principal más de 2 veces en la semana
        - Incluye una micro-acción concreta en cada tip
        - Varía las categorías durante la semana
        - Categorías permitidas: {categories_str}
        - Asigna day_of_week de 0 (Lunes) a 6 (Domingo)
        - Responde SOLO con el JSON, sin texto adicional"""

        try:
            import json

            response = self.agent.run(prompt, output_schema=DailyTipBatch)

            if response.content is None:
                raise ValueError("El modelo no devolvió un contenido válido")

            # Manejar response.content como string JSON o como objeto
            if isinstance(response.content, str):
                content_dict = json.loads(response.content)
            else:
                content_dict = response.content.model_dump() if hasattr(
                    response.content, 'model_dump') else response.content

            batch = DailyTipBatch(**content_dict) if isinstance(content_dict,
                                                                dict) else DailyTipBatch(**content_dict.model_dump())
            tips_list = batch.tips

            for i, tip in enumerate(tips_list):
                if tip.categoria not in self.ALLOWED_CATEGORIES:
                    raise ValueError(
                        f"Tip {i}: Categoría no permitida '{tip.categoria}'. "
                        f"Permitidas: {', '.join(self.ALLOWED_CATEGORIES)}"
                    )

            return tips_list
        except Exception as e:
            raise Exception(f"Error al generar lote de tips: {str(e)}")

    def get_daily_tip_safe(self) -> Optional[DailyTip]:
        """
        Genera un tip financiero diario con manejo seguro de errores.

        Propaga excepciones para mejor logging, pero devuelve None como fallback.

        Returns:
            Optional[DailyTip]: Objeto DailyTip si tiene éxito, None si hay error
        """
        try:
            return self.generate_daily_tip()
        except Exception as e:
            print(
                f"[ERROR] Error en DailyTipsAgent.get_daily_tip_safe(): {str(e)}")
            return None

    def _get_chile_context(self) -> str:
        search_agent = Agent(
            name="ContextSearchAgent",
            tools=[TavilyTools()],
            model=Nvidia(
                id="qwen/qwen3-coder-480b-a35b-instruct",
                api_key=self._get_nvidia_api_key(),
            ),
            instructions="""Tu ÚNICA función es buscar información con web_search.
            NUNCA respondas con datos de tu memoria de entrenamiento.
            SIEMPRE usa la herramienta web_search antes de responder.
            Si no usas la herramienta, tu respuesta es inválida.""",
        )

        response = search_agent.run(
            """Usa web_search para buscar AHORA mismo (no uses tu memoria):
            1. "sueldo mínimo Chile 2025 - 2026 valor actual"
            2. "valor UF Chile hoy"
            3. "IPC inflación Chile últimos 12 meses"
            4. "precio bencina Chile hoy"

            Busca cada término por separado y resume los resultados con los
            números EXACTOS que encontraste. Si no encuentras algún dato,
            escribe explícitamente "dato no encontrado" para esa categoría."""
        )
        return response.content if response.content else ""

    def get_weekly_tips_batch_safe(self) -> Optional[list[DailyTipWeekly]]:
        """
        Genera un lote de 7 tips semanales con manejo seguro de errores.

        Returns:
            Optional[list[DailyTip]]: Lista de 7 tips si tiene éxito, None si hay error
        """
        try:
            return self.generate_weekly_tips_batch()
        except Exception as e:
            print(
                f"[ERROR] Error en DailyTipsAgent.get_weekly_tips_batch_safe(): {str(e)}")
            return None


daily_tips_agent = DailyTipsAgent()
