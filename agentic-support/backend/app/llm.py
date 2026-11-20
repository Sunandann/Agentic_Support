"""Optional LLM access. Every caller must work when this returns None (offline mode)."""
from .config import settings


class LLM:
    @property
    def enabled(self) -> bool:
        return bool(settings.llm_api_key)

    def complete(self, system: str, prompt: str, temperature: float = 0.2, n: int = 1) -> list[str] | None:
        if not self.enabled:
            return None
        try:
            from openai import OpenAI  # imported lazily so the package stays optional
            client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url or None)
            resp = client.chat.completions.create(
                model=settings.llm_model, temperature=temperature, n=n,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
            return [c.message.content.strip() for c in resp.choices if c.message.content]
        except Exception:  # network/auth/package problems degrade to the template path
            return None


llm = LLM()
