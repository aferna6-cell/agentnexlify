"""LLM provider abstraction.

Agent OS demos and tests run with **no API key**: the default
:class:`DeterministicProvider` returns the agent's own templated fallback, so
every draft is real, placeholder-free, and channel-correct offline. When
``ANTHROPIC_API_KEY`` is set, :class:`AnthropicProvider` upgrades free-form
drafts to Claude output (Haiku for routing, Sonnet for drafts — per the cost
discipline plan).

``available`` models the credit/outage state the QA report cares about. When a
provider is unavailable, agents must surface that to the owner and emit no
silent empty draft (see :class:`agent_os.result.AgentResult.no_draft`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model: str
    # True when this came from a live model; False when it's the deterministic
    # fallback. Lets the trace stay honest about what produced the draft.
    live: bool


class LLMProvider:
    """Base provider. Subclasses implement :meth:`complete`."""

    name = "base"

    @property
    def available(self) -> bool:  # pragma: no cover - trivial
        return True

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        fallback: str,
        model: str = "draft",
        max_tokens: int = 1024,
    ) -> LLMResponse:
        raise NotImplementedError


class DeterministicProvider(LLMProvider):
    """Offline provider. Always returns the agent-supplied *fallback* text.

    This is intentionally not "the LLM is down" — it's a working, deterministic
    template engine. To exercise the credit-out path, construct it with
    ``available=False``.
    """

    name = "deterministic"

    def __init__(self, available: bool = True):
        self._available = available

    @property
    def available(self) -> bool:
        return self._available

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        fallback: str,
        model: str = "draft",
        max_tokens: int = 1024,
    ) -> LLMResponse:
        return LLMResponse(text=fallback, model="deterministic", live=False)


class AnthropicProvider(LLMProvider):
    """Live provider backed by the Anthropic SDK.

    Only imported/constructed when an API key is present so the package has no
    hard dependency on network access.
    """

    name = "anthropic"

    # Model routing: cheap+fast for classification, stronger for final drafts.
    ROUTER_MODEL = "claude-haiku-4-5-20251001"
    DRAFT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None
        self._available = bool(self._api_key)

    @property
    def available(self) -> bool:
        return self._available

    def _ensure_client(self):
        if self._client is None:
            import anthropic  # lazy import

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        fallback: str,
        model: str = "draft",
        max_tokens: int = 1024,
    ) -> LLMResponse:
        model_id = self.ROUTER_MODEL if model == "router" else self.DRAFT_MODEL
        try:
            client = self._ensure_client()
            resp = client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text
                for block in resp.content
                if getattr(block, "type", "") == "text"
            ).strip()
            if not text:
                # Treat an empty completion as unavailable rather than shipping
                # a silent empty draft.
                self._available = False
                return LLMResponse(text=fallback, model=model_id, live=False)
            return LLMResponse(text=text, model=model_id, live=True)
        except Exception:
            # Network/credit/outage failure: mark unavailable and fall back. The
            # caller decides whether to show the fallback or surface "service
            # temporarily unavailable".
            self._available = False
            return LLMResponse(text=fallback, model=model_id, live=False)


def default_provider() -> LLMProvider:
    """Return the best provider for the current environment."""

    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicProvider()
    return DeterministicProvider()
