"""Tests for :class:`EEGSimulator` - signal generation and feature extraction."""

from __future__ import annotations

from bci_dapp.eeg_simulator import BAND_RANGES, CHANNELS, INTENT_PROFILES, EEGSimulator


class TestEEGSimulator:
    def test_generate_frame_returns_frame(self, sim: EEGSimulator) -> None:
        assert sim.generate_frame() is not None

    def test_all_channels_present(self, sim: EEGSimulator) -> None:
        frame = sim.generate_frame()
        for ch in CHANNELS:
            assert ch in frame.channel_powers

    def test_all_bands_present_per_channel(self, sim: EEGSimulator) -> None:
        frame = sim.generate_frame()
        for ch in CHANNELS:
            for band in BAND_RANGES:
                assert band in frame.channel_powers[ch]

    def test_band_powers_sum_to_one_per_channel(self, sim: EEGSimulator) -> None:
        frame = sim.generate_frame()
        for ch in CHANNELS:
            total = sum(frame.channel_powers[ch].values())
            assert abs(total - 1.0) < 1e-6, f"Channel {ch} powers don't sum to 1"

    def test_dominant_band_is_valid(self, sim: EEGSimulator) -> None:
        assert sim.generate_frame().dominant_band in BAND_RANGES

    def test_snr_db_in_range(self, sim: EEGSimulator) -> None:
        assert 5.0 <= sim.generate_frame().snr_db <= 30.0

    def test_to_feature_dict_has_mean_bands(self, sim: EEGSimulator) -> None:
        feat = sim.to_feature_dict(sim.generate_frame())
        for band in BAND_RANGES:
            assert f"mean_{band}" in feat

    def test_to_feature_dict_has_metadata_keys(self, sim: EEGSimulator) -> None:
        feat = sim.to_feature_dict(sim.generate_frame())
        assert "dominant_band" in feat
        assert "snr_db" in feat

    def test_reproducible_with_seed(self) -> None:
        f1 = EEGSimulator(seed=7).generate_frame(intent="focus")
        f2 = EEGSimulator(seed=7).generate_frame(intent="focus")
        assert f1.band_mean == f2.band_mean

    def test_intent_biases_dominant_band(self) -> None:
        """Each intent should produce its expected dominant band most of the time."""
        for intent in INTENT_PROFILES:
            expected = max(INTENT_PROFILES[intent], key=INTENT_PROFILES[intent].__getitem__)
            hits = sum(
                1
                for s in range(20)
                if EEGSimulator(seed=s).generate_frame(intent=intent).dominant_band == expected
            )
            assert hits >= 10, f"Intent '{intent}' dominant band not reliably reproduced"

    def test_seeded_rng_controls_intent_selection(self) -> None:
        """With a fixed seed, random intent selection must be deterministic."""
        intents_a = [EEGSimulator(seed=0).generate_frame().dominant_band for _ in range(5)]
        intents_b = [EEGSimulator(seed=0).generate_frame().dominant_band for _ in range(5)]
        assert intents_a == intents_b
