"""SHA-256 hash-chained mock blockchain ledger.

Not a distributed chain - but architecturally correct for demo and interview
evidence: each block is immutable once appended, the full chain is verifiable,
and the ledger persists to a JSON file between runs.

STAR story note: Replacing ``_save`` / ``_load`` with Anchor program calls
is a one-function change - the signing and hashing layers are chain-agnostic.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Block:
    """An immutable, hash-linked ledger block.

    Attributes:
        index:         Zero-based position in the chain (0 = genesis).
        timestamp:     ISO-8601 UTC timestamp at block creation.
        session_id:    Session ID from the embedded provenance record.
        record:        Full signed provenance record dict.
        previous_hash: SHA-256 hash of the preceding block.
        block_hash:    SHA-256 hash of this block's canonical content.
                       Computed in ``__post_init__`` when left empty.
    """

    index: int
    timestamp: str
    session_id: str
    record: dict[str, Any]
    previous_hash: str
    block_hash: str = ""  # computed in __post_init__ when empty

    def __post_init__(self) -> None:
        # frozen=True requires object.__setattr__ for any field mutation.
        if not self.block_hash:
            object.__setattr__(self, "block_hash", self.compute_hash())

    # ── Hashing ──────────────────────────────────────────────────────────────

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash of this block's canonical content."""
        content = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "session_id": self.session_id,
                "record": self.record,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(content).hexdigest()

    # ── Serialisation ────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of this block."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "record": self.record,
            "previous_hash": self.previous_hash,
            "block_hash": self.block_hash,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Block:
        """Reconstruct a :class:`Block` from a serialised dict.

        The stored ``block_hash`` is passed directly - ``__post_init__`` will
        not overwrite a non-empty value.
        """
        return cls(
            index=d["index"],
            timestamp=d["timestamp"],
            session_id=d["session_id"],
            record=d["record"],
            previous_hash=d["previous_hash"],
            block_hash=d["block_hash"],
        )


# ---------------------------------------------------------------------------
# Chain verification result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChainVerification:
    """Result of a full chain integrity check.

    Attributes:
        valid:     ``True`` when no linkage or hash errors were found.
        n_invalid: Number of invalid blocks detected.
        errors:    Human-readable descriptions of each error found.
    """

    valid: bool
    n_invalid: int
    errors: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


class MockBlockchainLedger:
    """Append-only SHA-256 hash-chained ledger with JSON persistence.

    Args:
        ledger_path: Optional path to a JSON file.  If the file exists, the
                     ledger is loaded from it.  Every :meth:`append` call
                     auto-saves.  Pass ``None`` for an in-memory-only ledger.
    """

    GENESIS_HASH: str = "0" * 64

    def __init__(self, ledger_path: Path | str | None = None) -> None:
        self._chain: list[Block] = []
        self._ledger_path: Path | None = Path(ledger_path) if ledger_path else None

        if self._ledger_path and self._ledger_path.exists():
            self._load()
            logger.debug("Loaded ledger from %s (%d blocks)", self._ledger_path, len(self._chain))
        else:
            self._chain.append(self._make_genesis())
            self._save()
            logger.debug("Initialised new ledger at %s", self._ledger_path)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def height(self) -> int:
        """Number of non-genesis (data) blocks."""
        return len(self._chain) - 1

    @property
    def head(self) -> Block:
        """The most recently appended block (genesis if empty)."""
        return self._chain[-1]

    # ── Public API ────────────────────────────────────────────────────────────

    def append(self, record: dict[str, Any]) -> Block:
        """Append a signed session record as a new block.

        Args:
            record: Signed record dict from :meth:`ProvenanceManager.sign_session`.

        Returns:
            The newly created and persisted :class:`Block`.
        """
        block = Block(
            index=len(self._chain),
            timestamp=datetime.now(UTC).isoformat(),
            session_id=record.get("session_id", ""),
            record=record,
            previous_hash=self.head.block_hash,
        )
        self._chain.append(block)
        self._save()
        logger.info(
            "Appended block #%d session=%s hash=%s…",
            block.index,
            block.session_id,
            block.block_hash[:12],
        )
        return block

    def verify_chain(self) -> ChainVerification:
        """Walk every block and verify hash linkage and content integrity.

        Returns:
            :class:`ChainVerification` with a summary of any errors found.
        """
        errors: list[str] = []
        for i in range(1, len(self._chain)):
            current = self._chain[i]
            previous = self._chain[i - 1]
            if current.block_hash != current.compute_hash():
                errors.append(f"Block {i}: hash mismatch (content tampered)")
            if current.previous_hash != previous.block_hash:
                errors.append(f"Block {i}: broken chain link to block {i - 1}")

        result = ChainVerification(valid=not errors, n_invalid=len(errors), errors=tuple(errors))
        if result.valid:
            logger.info("Chain verified - %d blocks intact", self.height)
        else:
            logger.warning("Chain verification FAILED - %d error(s)", result.n_invalid)
        return result

    def get_block(self, index: int) -> Block | None:
        """Return the block at *index*, or ``None`` if out of range."""
        if 0 <= index < len(self._chain):
            return self._chain[index]
        return None

    def get_session(self, session_id: str) -> Block | None:
        """Return the block whose ``session_id`` matches, or ``None``."""
        return next((b for b in self._chain if b.session_id == session_id), None)

    def export(self) -> list[dict[str, Any]]:
        """Return the full chain as a JSON-serialisable list of dicts."""
        return [b.to_dict() for b in self._chain]

    # ── Internal ─────────────────────────────────────────────────────────────

    def _make_genesis(self) -> Block:
        return Block(
            index=0,
            timestamp=datetime.now(UTC).isoformat(),
            session_id="genesis",
            record={},
            previous_hash=self.GENESIS_HASH,
        )

    def _save(self) -> None:
        if self._ledger_path is None:
            return
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._ledger_path, "w", encoding="utf-8") as fh:
            json.dump(self.export(), fh, indent=2)

    def _load(self) -> None:
        if self._ledger_path is None:
            return
        with open(self._ledger_path, encoding="utf-8") as fh:
            data: list[dict[str, Any]] = json.load(fh)
        self._chain = [Block.from_dict(d) for d in data]
