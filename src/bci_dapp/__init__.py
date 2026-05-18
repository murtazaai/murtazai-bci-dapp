"""bci_dapp - EEG signal sim → rig-core LLM → Ed25519 provenance → blockchain ledger.

Pipeline (one session)::

    EEGSimulator.generate_frame()   →  EEGFrame
        │  .to_feature_dict()
        ▼
    BCIAgent.classify()             →  IntentResult
        │  .to_payload()
        ▼
    ProvenanceManager.sign_session()  →  signed record dict
        │
        ▼
    MockBlockchainLedger.append()     →  Block
"""

from bci_dapp.__version__ import __version__
from bci_dapp.blockchain_ledger import Block, ChainVerification, MockBlockchainLedger
from bci_dapp.eeg_simulator import EEGFrame, EEGSimulator
from bci_dapp.exceptions import (
    BCIDAppError,
    ChainIntegrityError,
    ClassificationError,
    SignatureError,
)
from bci_dapp.llm_agent import BCIAgent, IntentResult
from bci_dapp.provenance import ProvenanceManager

__all__ = [
    "BCIAgent",
    "BCIDAppError",
    "Block",
    "ChainIntegrityError",
    "ChainVerification",
    "ClassificationError",
    "EEGFrame",
    "EEGSimulator",
    "IntentResult",
    "MockBlockchainLedger",
    "ProvenanceManager",
    "SignatureError",
    "__version__",
]
