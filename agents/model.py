"""Model factory with a tokenless local fallback.

Default: Gemini (needs Google quota).
Set USE_OLLAMA=1 to run every agent on a local Ollama model instead — no cloud
tokens. Optionally override OLLAMA_MODEL (default llama3.2:3b) or GEMINI_MODEL.
"""
import os
from google.genai import types


def build_model():
    if os.getenv("USE_OLLAMA") == "1":
        from google.adk.models.lite_llm import LiteLlm
        return LiteLlm(model="ollama_chat/" + os.getenv("OLLAMA_MODEL", "llama3.2:3b"))
    from google.adk.models import Gemini
    return Gemini(
        model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        retry_options=types.HttpRetryOptions(attempts=6),
    )
