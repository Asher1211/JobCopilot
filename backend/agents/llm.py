"""LLM factory — supports any OpenAI-compatible API.

User brings their own: api_key, base_url (optional), model name.
Works with: DeepSeek, OpenAI, Groq, Together, Ollama, vLLM, etc.
"""
from langchain_openai import ChatOpenAI


def get_llm(
    temperature: float = 0.3,
    api_key: str = "",
    base_url: str = "",
    model: str = "deepseek-chat",
):
    """Create an LLM instance from user-provided config.

    If base_url is empty, it's auto-detected from the model name:
      deepseek → https://api.deepseek.com/v1
      otherwise → https://api.openai.com/v1
    """
    if not api_key:
        raise ValueError(
            "No API key configured. Please add your key in Settings → API Keys."
        )

    if not base_url:
        if "deepseek" in model:
            base_url = "https://api.deepseek.com/v1"
        else:
            base_url = "https://api.openai.com/v1"

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
        max_tokens=4096,
    )
