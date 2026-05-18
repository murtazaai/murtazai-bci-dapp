"""Ed25519 provenance signing for BCI session records.

Each signed record is a self-contained, offline-verifiable unit:
``payload + signature + public_key``.  The :class:`MockBlockchainLedger` then
wraps these records into tamper-evident SHA-256 hash-chained blocks.

STAR story note: This is the cryptographic spine of the BCI DApp —
every EEG interpretation event is signed before it ever touches the chain.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

logger = logging.getLogger(__name__)


class ProvenanceManager:
    """Generates Ed25519 keypairs and creates / verifies signed session records.

    Example::

        pm      = ProvenanceManager()
        keypair = pm.generate_keypair()
        record  = pm.sign_session({"alpha": 0.52, "intent": "select"}, keypair)
        assert pm.verify_record(record)
    """

    # ── Key management ───────────────────────────────────────────────────────

    def generate_keypair(self) -> dict[str, str]:
        """Generate a fresh Ed25519 keypair.

        Returns:
            ``{"private_key": "<hex>", "public_key": "<hex>"}``.
            Keep the private key secret; store only the public key on-chain.
        """
        private_key: Ed25519PrivateKey = Ed25519PrivateKey.generate()
        public_key: Ed25519PublicKey = private_key.public_key()

        priv_hex = private_key.private_bytes(
            encoding=Encoding.Raw,
            format=PrivateFormat.Raw,
            encryption_algorithm=NoEncryption(),
        ).hex()
        pub_hex = public_key.public_bytes(
            encoding=Encoding.Raw,
            format=PublicFormat.Raw,
        ).hex()

        logger.debug("Generated Ed25519 keypair: pub=%s…", pub_hex[:16])
        return {"private_key": priv_hex, "public_key": pub_hex}

    # ── Signing ──────────────────────────────────────────────────────────────

    def sign_session(
        self,
        payload: dict[str, Any],
        keypair: dict[str, str],
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Sign a BCI session payload and return a verifiable record.

        Args:
            payload:    Arbitrary dict of BCI measurements / LLM interpretation.
            keypair:    Dict with ``"private_key"`` and ``"public_key"`` hex strings.
            session_id: Explicit session ID; auto-generated UUID4 when omitted.

        Returns:
            A dict ready to pass directly to :meth:`MockBlockchainLedger.append`.
        """
        sid = session_id or str(uuid.uuid4())
        timestamp = datetime.now(UTC).isoformat()

        # Canonical JSON is deterministic - field order does not affect the signature.
        canonical = json.dumps(
            {"session_id": sid, "timestamp": timestamp, "payload": payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

        priv_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(keypair["private_key"]))
        signature = priv_key.sign(canonical).hex()

        logger.debug("Signed session: id=%s sig=%s…", sid, signature[:16])
        return {
            "session_id": sid,
            "timestamp": timestamp,
            "payload": payload,
            "public_key": keypair["public_key"],
            "signature": signature,
        }

    # ── Verification ─────────────────────────────────────────────────────────

    def verify_record(self, record: dict[str, Any]) -> bool:
        """Verify the Ed25519 signature on a session record.

        Returns:
            ``True`` if the signature is valid, ``False`` otherwise.
            Never raises - all errors are swallowed and return ``False``.
        """
        try:
            canonical = json.dumps(
                {
                    "session_id": record["session_id"],
                    "timestamp": record["timestamp"],
                    "payload": record["payload"],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()

            pub_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(record["public_key"]))
            pub_key.verify(bytes.fromhex(record["signature"]), canonical)
            return True

        except (InvalidSignature, KeyError, ValueError):
            return False
