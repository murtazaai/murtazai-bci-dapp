"""LLM-backed BCI intent classifier.

Wraps an OpenAI-compatible chat completion endpoint (rig-core exposes one) to
classify EEG band-power features into a BCI intent label with confidence score.

Pipeline position::

    EEGSimulator.to_feature_dict()
            │
            ▼
    BCIAgent.classify(features)  →  IntentResult
            │  .to_payload()
            ▼
    ProvenanceManager.sign_session()
            │
            ▼
    MockBlockchainLedger.append()

STAR story note: Swap ``base_url`` to ``http://localhost:11434/v1`` to run
against a local rig-core / Ollama agent - zero code changes.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

_VALID_INTENTS: frozenset[str] = frozenset({"relax", "focus", "fatigue", "select"})


@dataclass(frozen=True, slots=True)
class IntentResult:
    """Immutable result of an intent classification.

    Attributes:
        intent:       One of ``relax | focus | fatigue | select``.
        confidence:   Classifier confidence in [0.0, 1.0].
        reasoning:    One-sentence natural-language explanation.
        raw_features: Original feature dict passed to the classifier.
    """

    intent: str
    confidence: float
    reasoning: str
    raw_features: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        """Return a JSON-serialisable payload for provenance signing."""
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "eeg_summary": {
                k: v
                for k, v in self.raw_features.items()
                if k.startswith("mean_") or k in ("dominant_band", "snr_db")
            },
        }


# ---------------------------------------------------------------------------
# Rule-based fallback (no API key required - runs in CI / offline)
# ---------------------------------------------------------------------------


def _rule_based_classify(features: dict[str, Any]) -> IntentResult:
    """Deterministic rule-based classifier.

    Checks ``dominant_band`` first; uses power thresholds only as a tiebreaker.
    This ensures tests are deterministic and the demo runs without an API key.
    """
    alpha: float = features.get("mean_alpha", 0.0)
    beta: float = features.get("mean_beta", 0.0)
    theta: float = features.get("mean_theta", 0.0)
    dom: str = features.get("dominant_band", "alpha")

    if dom == "beta" or (dom not in ("alpha", "theta", "gamma") and beta > 0.40):
        intent, conf, reason = (
            "focus",
            0.85,
            "High beta power is consistent with active concentration.",
        )
    elif dom == "theta" or (dom not in ("alpha", "beta", "gamma") and theta > 0.35):
        intent, conf, reason = (
            "fatigue",
            0.78,
            "Dominant theta suggests drowsiness or mental fatigue.",
        )
    elif dom == "gamma":
        intent, conf, reason = (
            "select",
            0.80,
            "Gamma burst pattern associated with motor intent / selection.",
        )
    elif dom == "alpha" or alpha > 0.40:
        intent, conf, reason = "relax", 0.82, "Elevated alpha power indicates relaxed, idle state."
    else:
        intent, conf, reason = "relax", 0.60, "No dominant pattern; defaulting to baseline relax."

    return IntentResult(intent=intent, confidence=conf, reasoning=reason, raw_features=features)


# ---------------------------------------------------------------------------
# LLM system prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a BCI (Brain-Computer Interface) signal interpreter for a children's EEG DApp.
You receive JSON-formatted EEG band-power features and must classify them into one of:
  relax | focus | fatigue | select

Respond ONLY with a JSON object - no markdown, no explanation outside the JSON:
{
  "intent": "<label>",
  "confidence": <float 0-1>,
  "reasoning": "<one sentence>"
}
"""

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class BCIAgent:
    """Classifies EEG features using an LLM (rig-core / OpenAI-compatible).

    Args:
        base_url: OpenAI-compatible endpoint.
                  Default: ``https://api.openai.com/v1``.
                  For rig-core local: ``http://localhost:11434/v1``.
        model:    Model identifier (default ``"gpt-4o-mini"``).
        api_key:  API key; loaded from ``OPENAI_API_KEY`` env var if omitted.
        use_llm:  Force LLM (``True``) or rule-based fallback (``False``).
                  Auto-detected from API key availability when ``None``.
    """

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        use_llm: bool | None = None,
    ) -> None:
        import os

        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._use_llm = use_llm if use_llm is not None else bool(self._api_key)
        logger.debug("BCIAgent initialised: model=%s llm=%s", self.model, self._use_llm)

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(self, features: dict[str, Any]) -> IntentResult:
        """Classify EEG features into a BCI intent label.

        Falls back to the rule-based classifier when no API key is set or when
        the LLM call raises a recoverable error (network, parse, key lookup).

        Args:
            features: Feature dict produced by :meth:`EEGSimulator.to_feature_dict`.

        Returns:
            :class:`IntentResult` with intent, confidence, and reasoning.
        """
        if not self._use_llm:
            return _rule_based_classify(features)

        try:
            return self._llm_classify(features)
        except (urllib.error.URLError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("LLM classify failed (%s), using rule-based fallback", exc)
            fallback = _rule_based_classify(features)
            return IntentResult(
                intent=fallback.intent,
                confidence=fallback.confidence,
                reasoning=f"[LLM fallback: {exc}] {fallback.reasoning}",
                raw_features=fallback.raw_features,
            )

    # ── Internal ─────────────────────────────────────────────────────────────

    def _llm_classify(self, features: dict[str, Any]) -> IntentResult:
        """Call the OpenAI-compatible ``/chat/completions`` endpoint."""
        summary = {
            k: v
            for k, v in features.items()
            if k.startswith("mean_") or k in ("dominant_band", "snr_db")
        }
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(summary, indent=2)},
                ],
                "temperature": 0.2,
                "max_tokens": 200,
            }
        ).encode()

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())

        raw_text: str = body["choices"][0]["message"]["content"].strip()
        parsed: dict[str, Any] = json.loads(raw_text)
        return IntentResult(
            intent=parsed["intent"],
            confidence=float(parsed["confidence"]),
            reasoning=parsed["reasoning"],
            raw_features=features,
        )
