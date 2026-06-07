import logging
from typing import Any, Callable

from google.genai import errors as genai_errors

from app.agent._gemini_keys import get_gemini_api_keys

logger = logging.getLogger(__name__)


_RATE_LIMIT_STATUS_CODES = {401, 403, 429}
_RATE_LIMIT_KEYWORDS = (
    "rate limit",
    "rate-limit",
    "quota",
    "resource exhausted",
    "resource_exhausted",
    "too many requests",
    "unauthenticated",
    "permission denied",
    "api key not valid",
    "api_key_invalid",
)


def _is_retryable_auth_error(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    if code in _RATE_LIMIT_STATUS_CODES:
        return True
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if status in _RATE_LIMIT_STATUS_CODES:
        return True
    message = (str(exc) or "").lower()
    return any(kw in message for kw in _RATE_LIMIT_KEYWORDS)


def run_with_key_rotation(
    create_agent_fn: Callable[..., Any],
    prompt: str,
    *args: Any,
    run_method: str = "run",
    **kwargs: Any,
) -> Any:
    """
    Run an agent prompt; on auth/rate-limit error (401/403/429) rotate to the
    next configured Gemini key and retry. Raises the last error when all
    configured keys are exhausted.
    """
    keys = get_gemini_api_keys()
    if not keys:
        raise ValueError(
            "No GEMINI_API_KEY configured. Add at least one to your .env file."
        )

    last_error: BaseException | None = None
    for index, key in enumerate(keys):
        try:
            agent = create_agent_fn(api_key=key)
            return getattr(agent, run_method)(prompt, *args, **kwargs)
        except (genai_errors.ClientError, genai_errors.APIError) as exc:
            if not _is_retryable_auth_error(exc):
                raise
            logger.warning(
                "Gemini key ...%s hit %s; rotating (%d/%d).",
                key[-4:],
                getattr(exc, "code", None) or getattr(exc, "status", "error"),
                index + 1,
                len(keys),
            )
            last_error = exc
            continue
        except Exception as exc:
            if not _is_retryable_auth_error(exc):
                raise
            logger.warning(
                "Gemini key ...%s hit non-genai error; rotating (%d/%d). %s",
                key[-4:],
                index + 1,
                len(keys),
                exc,
            )
            last_error = exc
            continue

    raise RuntimeError(
        f"All {len(keys)} Gemini API keys are rate-limited or auth-failing. "
        f"Last error: {last_error}"
    ) from last_error
