"""Custom exceptions for bci_dapp.

Always catch these specific types rather than bare ``Exception`` so callers
can distinguish failure modes without swallowing unrelated errors.

Hierarchy::

    BCIDAppError
    ├── SignatureError        - Ed25519 sign / verify failures
    ├── ChainIntegrityError  - hash-chain linkage or tamper detection
    └── ClassificationError  - LLM / rule-based intent classification failures
"""

from __future__ import annotations


class BCIDAppError(Exception):
    """Base exception for all bci_dapp errors."""


class SignatureError(BCIDAppError):
    """Raised when an Ed25519 signature operation fails or a record is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Signature error: {message}")


class ChainIntegrityError(BCIDAppError):
    """Raised when blockchain hash-chain verification detects tampering."""

    def __init__(self, block_index: int, detail: str) -> None:
        self.block_index = block_index
        super().__init__(f"Chain integrity error at block {block_index}: {detail}")


class ClassificationError(BCIDAppError):
    """Raised when intent classification fails and no fallback is available."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Classification error: {detail}")
