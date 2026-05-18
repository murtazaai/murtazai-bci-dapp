"""Tests for :class:`BCIAgent` - rule-based path only (no API key required in CI)."""

from __future__ import annotations

from typing import Any

import pytest

from bci_dapp.llm_agent import BCIAgent, IntentResult

_VALID_INTENTS: frozenset[str] = frozenset({"relax", "focus", "fatigue", "select"})


class TestIntentResult:
    def test_to_payload_has_required_keys(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        payload = agent.classify(sample_features).to_payload()
        assert "intent" in payload
        assert "confidence" in payload
        assert "reasoning" in payload
        assert "eeg_summary" in payload

    def test_to_payload_eeg_summary_has_mean_bands(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        summary = agent.classify(sample_features).to_payload()["eeg_summary"]
        assert "mean_alpha" in summary
        assert "dominant_band" in summary

    def test_intent_result_is_immutable(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        from dataclasses import FrozenInstanceError

        result = agent.classify(sample_features)
        with pytest.raises(FrozenInstanceError):
            result.intent = "mutated"  # type: ignore[misc]


class TestBCIAgentRuleBased:
    def test_classify_returns_intent_result(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        assert isinstance(agent.classify(sample_features), IntentResult)

    def test_intent_is_valid_label(self, agent: BCIAgent, sample_features: dict[str, Any]) -> None:
        assert agent.classify(sample_features).intent in _VALID_INTENTS

    def test_confidence_in_range(self, agent: BCIAgent, sample_features: dict[str, Any]) -> None:
        result = agent.classify(sample_features)
        assert 0.0 <= result.confidence <= 1.0

    def test_reasoning_is_non_empty_string(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        assert len(agent.classify(sample_features).reasoning) > 0

    def test_alpha_dominant_gives_relax(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        feat = {**sample_features, "dominant_band": "alpha", "mean_alpha": 0.60}
        assert agent.classify(feat).intent == "relax"

    def test_beta_dominant_gives_focus(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        feat = {**sample_features, "dominant_band": "beta", "mean_beta": 0.55}
        assert agent.classify(feat).intent == "focus"

    def test_theta_dominant_gives_fatigue(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        feat = {**sample_features, "dominant_band": "theta", "mean_theta": 0.45}
        assert agent.classify(feat).intent == "fatigue"

    def test_gamma_dominant_gives_select(
        self, agent: BCIAgent, sample_features: dict[str, Any]
    ) -> None:
        feat = {**sample_features, "dominant_band": "gamma"}
        assert agent.classify(feat).intent == "select"

    def test_fallback_on_llm_failure_preserves_result(
        self, sample_features: dict[str, Any]
    ) -> None:
        """When LLM call raises, classify must still return a valid IntentResult."""
        bad_agent = BCIAgent(base_url="http://localhost:0", use_llm=True)
        result = bad_agent.classify(sample_features)
        assert isinstance(result, IntentResult)
        assert result.intent in _VALID_INTENTS
        assert "[LLM fallback:" in result.reasoning
