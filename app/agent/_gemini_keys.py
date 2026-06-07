import os
from threading import Lock


_KEY_NAMES = (
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_FALLBACK",
    "GEMINI_API_KEY_FALLBACK2",
    "GEMINI_API_KEY_FALLBACK3",
    "GEMINI_API_KEY_FALLBACK4",
)


def get_gemini_api_keys() -> list[str]:
    """Return non-empty Gemini API keys from env (in order)."""
    return [k.strip() for k in (os.getenv(name) for name in _KEY_NAMES) if k and k.strip()]


def get_gemini_api_key() -> str:
    """Return the first available Gemini API key or raise."""
    keys = get_gemini_api_keys()
    if not keys:
        raise ValueError(
            "No GEMINI_API_KEY configured. Add at least one to your .env file."
        )
    return keys[0]


_counter = 0
_lock = Lock()


def next_gemini_api_key() -> str:
    """Round-robin pick across configured Gemini keys. Thread-safe."""
    keys = get_gemini_api_keys()
    if not keys:
        raise ValueError(
            "No GEMINI_API_KEY configured. Add at least one to your .env file."
        )
    global _counter
    with _lock:
        key = keys[_counter % len(keys)]
        _counter += 1
    return key
