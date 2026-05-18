"""Shared pytest fixtures.

Available to every test module automatically - no explicit import needed.
Just declare the fixture name as a function parameter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bci_dapp.blockchain_ledger import MockBlockchainLedger
from bci_dapp.eeg_simulator import EEGSimulator
from bci_dapp.llm_agent import BCIAgent
from bci_dapp.provenance import ProvenanceManager

# ---------------------------------------------------------------------------
# EEG
# ---------------------------------------------------------------------------


@pytest.fixture()
def sim() -> EEGSimulator:
    """A seeded :class:`EEGSimulator` for fully reproducible tests."""
    return EEGSimulator(seed=42)


# ---------------------------------------------------------------------------
# LLM agent
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent() -> BCIAgent:
    """A :class:`BCIAgent` forced into rule-based mode (no API key required)."""
    return BCIAgent(use_llm=False)


@pytest.fixture()
def sample_features() -> dict[str, Any]:
    """Representative EEG feature dict with alpha as dominant band."""
    return {
        "dominant_band": "alpha",
        "snr_db": 15.3,
        "mean_delta": 0.05,
        "mean_theta": 0.10,
        "mean_alpha": 0.55,
        "mean_beta": 0.20,
        "mean_gamma": 0.10,
    }


# ---------------------------------------------------------------------------
# Provenance + ledger
# ---------------------------------------------------------------------------


@pytest.fixture()
def provenance() -> ProvenanceManager:
    """A fresh :class:`ProvenanceManager` instance."""
    return ProvenanceManager()


@pytest.fixture()
def keypair(provenance: ProvenanceManager) -> dict[str, str]:
    """An Ed25519 keypair generated from the shared *provenance* fixture."""
    return provenance.generate_keypair()


@pytest.fixture()
def tmp_ledger(tmp_path: Path) -> MockBlockchainLedger:
    """A :class:`MockBlockchainLedger` backed by a temp-dir JSON file."""
    return MockBlockchainLedger(ledger_path=tmp_path / "test_ledger.json")
