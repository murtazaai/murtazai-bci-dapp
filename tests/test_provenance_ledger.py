"""Tests for :class:`ProvenanceManager` and :class:`MockBlockchainLedger`."""

from __future__ import annotations

import json
from pathlib import Path

from bci_dapp.blockchain_ledger import MockBlockchainLedger
from bci_dapp.provenance import ProvenanceManager


class TestProvenanceManager:
    def test_generate_keypair_has_both_keys(self, provenance: ProvenanceManager) -> None:
        kp = provenance.generate_keypair()
        assert "private_key" in kp
        assert "public_key" in kp

    def test_keypair_values_are_hex_strings(self, provenance: ProvenanceManager) -> None:
        kp = provenance.generate_keypair()
        bytes.fromhex(kp["private_key"])  # must not raise
        bytes.fromhex(kp["public_key"])

    def test_sign_session_has_required_fields(
        self, provenance: ProvenanceManager, keypair: dict[str, str]
    ) -> None:
        record = provenance.sign_session({"alpha": 0.5, "beta": 0.3}, keypair)
        for key in ("session_id", "timestamp", "payload", "public_key", "signature"):
            assert key in record

    def test_verify_valid_signature(
        self, provenance: ProvenanceManager, keypair: dict[str, str]
    ) -> None:
        record = provenance.sign_session({"alpha": 0.5}, keypair)
        assert provenance.verify_record(record) is True

    def test_verify_tampered_payload_fails(
        self, provenance: ProvenanceManager, keypair: dict[str, str]
    ) -> None:
        record = provenance.sign_session({"alpha": 0.5}, keypair)
        record["payload"]["alpha"] = 0.99  # tamper
        assert provenance.verify_record(record) is False

    def test_session_ids_are_unique(
        self, provenance: ProvenanceManager, keypair: dict[str, str]
    ) -> None:
        r1 = provenance.sign_session({"x": 1}, keypair)
        r2 = provenance.sign_session({"x": 1}, keypair)
        assert r1["session_id"] != r2["session_id"]

    def test_custom_session_id_is_preserved(
        self, provenance: ProvenanceManager, keypair: dict[str, str]
    ) -> None:
        record = provenance.sign_session({"x": 1}, keypair, session_id="my-session")
        assert record["session_id"] == "my-session"


class TestMockBlockchainLedger:
    def test_genesis_block_exists_on_init(self, tmp_ledger: MockBlockchainLedger) -> None:
        assert tmp_ledger.height == 0
        assert tmp_ledger.head is not None
        assert tmp_ledger.head.index == 0

    def test_append_increments_height(
        self,
        tmp_ledger: MockBlockchainLedger,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        for i in range(3):
            tmp_ledger.append(provenance.sign_session({"i": i}, keypair))
        assert tmp_ledger.head.index == 3

    def test_chain_links_are_correct(
        self,
        tmp_ledger: MockBlockchainLedger,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        b1 = tmp_ledger.append(provenance.sign_session({"a": 1}, keypair))
        b2 = tmp_ledger.append(provenance.sign_session({"a": 2}, keypair))
        assert b2.previous_hash == b1.block_hash

    def test_verify_chain_on_valid_chain(
        self,
        tmp_ledger: MockBlockchainLedger,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        for i in range(3):
            tmp_ledger.append(provenance.sign_session({"i": i}, keypair))
        result = tmp_ledger.verify_chain()
        assert result.valid is True
        assert result.n_invalid == 0

    def test_get_block_by_index(
        self,
        tmp_ledger: MockBlockchainLedger,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        tmp_ledger.append(provenance.sign_session({"x": 7}, keypair))
        block = tmp_ledger.get_block(1)
        assert block is not None
        assert block.index == 1

    def test_get_block_out_of_range_returns_none(self, tmp_ledger: MockBlockchainLedger) -> None:
        assert tmp_ledger.get_block(999) is None

    def test_get_session_by_id(
        self,
        tmp_ledger: MockBlockchainLedger,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        tmp_ledger.append(provenance.sign_session({"x": 7}, keypair, session_id="find-me"))
        block = tmp_ledger.get_session("find-me")
        assert block is not None
        assert block.session_id == "find-me"

    def test_get_session_missing_returns_none(self, tmp_ledger: MockBlockchainLedger) -> None:
        assert tmp_ledger.get_session("does-not-exist") is None

    def test_export_is_json_serialisable(
        self,
        tmp_ledger: MockBlockchainLedger,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        tmp_ledger.append(provenance.sign_session({"x": 1}, keypair))
        json.dumps(tmp_ledger.export())  # must not raise

    def test_block_hash_integrity(
        self,
        tmp_ledger: MockBlockchainLedger,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        block = tmp_ledger.append(provenance.sign_session({"v": "hash_test"}, keypair))
        assert block.block_hash == block.compute_hash()

    def test_persistence_across_reload(
        self,
        tmp_path: Path,
        provenance: ProvenanceManager,
        keypair: dict[str, str],
    ) -> None:
        """A reloaded ledger must reproduce the same height and pass verification."""
        path = tmp_path / "persist_test.json"
        ledger = MockBlockchainLedger(ledger_path=path)
        ledger.append(provenance.sign_session({"persistent": True}, keypair))
        height = ledger.height

        reloaded = MockBlockchainLedger(ledger_path=path)
        assert reloaded.height == height
        assert reloaded.verify_chain().valid
