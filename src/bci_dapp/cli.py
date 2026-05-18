"""CLI entry point for the MurtazAI BCI DApp demo.

Pipeline: EEGSimulator → BCIAgent → ProvenanceManager → MockBlockchainLedger

Usage::

    bci-dapp                 # 5 sessions, rule-based (no API key needed)
    bci-dapp --n 10          # custom session count
    bci-dapp --llm           # use LLM classifier (requires OPENAI_API_KEY)
    bci-dapp --export        # also dump data/ledger_export.json

STAR story: This script drives the 1-min screen capture for the CV evidence repo.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from bci_dapp.blockchain_ledger import MockBlockchainLedger
from bci_dapp.eeg_simulator import EEGSimulator
from bci_dapp.llm_agent import BCIAgent
from bci_dapp.logging_config import configure_logging
from bci_dapp.provenance import ProvenanceManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_RED = "\033[31m"

_INTENT_COLOUR: dict[str, str] = {
    "relax": "\033[34m",
    "focus": "\033[32m",
    "fatigue": "\033[33m",
    "select": "\033[35m",
}


def _coloured(text: str, colour: str) -> str:
    return f"{colour}{text}{_RESET}"


def _bar(value: float, width: int = 20) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(n_sessions: int = 5, use_llm: bool = False, export: bool = False) -> None:
    """Run the full EEG → LLM → provenance → ledger pipeline.

    Args:
        n_sessions: Number of EEG sessions to simulate.
        use_llm:    If ``True``, call the LLM endpoint (requires ``OPENAI_API_KEY``).
        export:     If ``True``, also write ``data/ledger_export.json``.
    """
    print(f"\n{_BOLD}{'═' * 60}{_RESET}")
    print(f"{_BOLD}  MurtazAI BCI DApp - EEG → LLM → Blockchain Provenance{_RESET}")
    print(f"{_BOLD}{'═' * 60}{_RESET}\n")

    Path("data").mkdir(exist_ok=True)

    sim = EEGSimulator()
    agent = BCIAgent(use_llm=use_llm)
    provenance = ProvenanceManager()
    ledger = MockBlockchainLedger(ledger_path=Path("data/ledger.json"))
    keypair = provenance.generate_keypair()

    print(f"  Classifier   : {_coloured('LLM' if use_llm else 'Rule-based', _CYAN)}")
    print(f"  Sessions     : {n_sessions}")
    print("  Ledger       : data/ledger.json")
    print(f"  Public Key   : {keypair['public_key'][:24]}…\n")
    print(f"{'─' * 60}")

    for i in range(1, n_sessions + 1):
        frame = sim.generate_frame()
        features = sim.to_feature_dict(frame)
        result = agent.classify(features)
        record = provenance.sign_session(result.to_payload(), keypair)
        block = ledger.append(record)

        ic = _INTENT_COLOUR.get(result.intent, "")
        print(f"\n  {_BOLD}Session {i:02d}{_RESET}  Block #{block.index}")
        print(
            f"  Intent     : {_coloured(result.intent.upper().ljust(8), ic)} "
            f"[{_bar(result.confidence)}] {result.confidence:.0%}"
        )
        print(f"  Reasoning  : {result.reasoning}")
        print(f"  SNR        : {frame.snr_db:.1f} dB   Dominant: {frame.dominant_band}")

        bands = "  Bands      :" + "".join(
            f"  {b[:3].upper()} {p:.2f}" for b, p in frame.band_mean.items()
        )
        print(bands)
        print(f"  Session ID : {record['session_id']}")
        print(f"  Block Hash : {block.block_hash[:16]}…")
        sig_ok = provenance.verify_record(record)
        print(f"  Sig Valid  : {_coloured('✓ YES', _GREEN) if sig_ok else _coloured('✗ NO', _RED)}")

    print(f"\n{'─' * 60}")
    verification = ledger.verify_chain()
    if verification.valid:
        print(
            f"\n  {_coloured('✓ Chain verified - all ' + str(ledger.height) + ' blocks intact', _GREEN)}"
        )
    else:
        print(f"\n  {_coloured('✗ Chain verification FAILED', _RED)}")
        for err in verification.errors:
            print(f"    • {err}")

    if export:
        out = Path("data/ledger_export.json")
        out.write_text(json.dumps(ledger.export(), indent=2), encoding="utf-8")
        print(f"  Ledger exported → {out}")

    print(f"\n{_BOLD}{'═' * 60}{_RESET}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI args and run the pipeline. Registered as ``bci-dapp`` script."""
    configure_logging()
    parser = argparse.ArgumentParser(
        description="MurtazAI BCI DApp - EEG → LLM → blockchain provenance demo"
    )
    parser.add_argument("--n", type=int, default=5, help="Number of EEG sessions (default 5)")
    parser.add_argument(
        "--llm", action="store_true", help="Use LLM classifier (requires OPENAI_API_KEY)"
    )
    parser.add_argument("--export", action="store_true", help="Export full ledger to JSON")
    args = parser.parse_args()
    run_pipeline(n_sessions=args.n, use_llm=args.llm, export=args.export)


if __name__ == "__main__":
    main()
