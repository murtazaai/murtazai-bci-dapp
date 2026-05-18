"""EEG signal simulator with band-power feature extraction.

Simulates 4-channel EEG data (Fp1, Fp2, C3, C4) and extracts standard
frequency-band power features: delta, theta, alpha, beta, gamma.

In a real BCI DApp this module is replaced by a live LSL-stream reader or the
Emotiv EPOC SDK adapter - the rest of the pipeline is unchanged.

STAR story note: Swap :class:`EEGSimulator` for a real LSL reader and
everything downstream (agent → provenance → ledger) stays identical.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHANNELS: tuple[str, ...] = ("Fp1", "Fp2", "C3", "C4")

# (low_hz, high_hz) - lower inclusive, upper exclusive
BAND_RANGES: dict[str, tuple[float, float]] = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta": (13.0, 30.0),
    "gamma": (30.0, 100.0),
}

# Centre frequency used for signal synthesis (midpoint of each band)
_BAND_CENTRE_HZ: dict[str, float] = {
    "delta": 2.0,
    "theta": 6.0,
    "alpha": 10.5,
    "beta": 20.0,
    "gamma": 40.0,
}

# Band-power weight profiles per intent class (values sum to 1.0)
INTENT_PROFILES: dict[str, dict[str, float]] = {
    "relax": {"alpha": 0.55, "theta": 0.25, "delta": 0.10, "beta": 0.08, "gamma": 0.02},
    "focus": {"beta": 0.50, "alpha": 0.25, "gamma": 0.15, "theta": 0.07, "delta": 0.03},
    "fatigue": {"theta": 0.50, "delta": 0.30, "alpha": 0.12, "beta": 0.06, "gamma": 0.02},
    "select": {"beta": 0.45, "gamma": 0.25, "alpha": 0.20, "theta": 0.07, "delta": 0.03},
}

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EEGFrame:
    """One windowed snapshot of EEG features.

    Attributes:
        channel_powers: Per-channel relative band power - ``{channel: {band: power}}``.
        band_mean:      Band powers averaged across all channels - ``{band: power}``.
        dominant_band:  Name of the band with highest mean power.
        snr_db:         Simulated signal-to-noise ratio in dB.
    """

    channel_powers: dict[str, dict[str, float]]
    band_mean: dict[str, float]
    dominant_band: str
    snr_db: float


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------


class EEGSimulator:
    """Generates synthetic EEG frames with intent-biased band-power profiles.

    Args:
        sampling_rate: Sample rate in Hz (default 256 - matches Emotiv EPOC).
        window_sec:    Analysis window in seconds (default 2.0).
        noise_level:   Additive Gaussian noise standard deviation (default 0.05).
        channels:      Channel names to simulate (default ``CHANNELS``).
        seed:          Optional RNG seed for full reproducibility.
    """

    def __init__(
        self,
        sampling_rate: int = 256,
        window_sec: float = 2.0,
        noise_level: float = 0.05,
        channels: Sequence[str] = CHANNELS,
        seed: int | None = None,
    ) -> None:
        self.sampling_rate = sampling_rate
        self.window_sec = window_sec
        self.noise_level = noise_level
        self.channels = list(channels)
        self._rng = np.random.default_rng(seed)
        logger.debug(
            "EEGSimulator initialised: %d Hz, %.1f s window, %d channels",
            sampling_rate,
            window_sec,
            len(self.channels),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_frame(self, intent: str | None = None) -> EEGFrame:
        """Generate a single EEG analysis window.

        Args:
            intent: Key from :data:`INTENT_PROFILES` to bias band powers.
                    Chosen uniformly at random (via the seeded RNG) when omitted.

        Returns:
            :class:`EEGFrame` with per-channel band powers and aggregate features.
        """
        # Use the seeded numpy RNG so results are reproducible when seed is set.
        if intent is None:
            intent = str(self._rng.choice(list(INTENT_PROFILES.keys())))
        profile = INTENT_PROFILES.get(intent, INTENT_PROFILES["relax"])

        channel_powers: dict[str, dict[str, float]] = {
            ch: self._bandpower(self._simulate_raw_signal(profile)) for ch in self.channels
        }

        band_mean: dict[str, float] = {
            band: float(np.mean([channel_powers[ch][band] for ch in self.channels]))
            for band in BAND_RANGES
        }
        dominant_band = max(band_mean, key=band_mean.__getitem__)
        snr_db = round(float(self._rng.uniform(8.0, 22.0)), 2)

        logger.debug(
            "Generated frame: intent=%s dominant=%s snr=%.1f dB", intent, dominant_band, snr_db
        )
        return EEGFrame(
            channel_powers=channel_powers,
            band_mean=band_mean,
            dominant_band=dominant_band,
            snr_db=snr_db,
        )

    def to_feature_dict(self, frame: EEGFrame) -> dict[str, Any]:
        """Flatten an :class:`EEGFrame` into a plain dict for LLM prompts / provenance payloads."""
        out: dict[str, Any] = {
            "dominant_band": frame.dominant_band,
            "snr_db": frame.snr_db,
        }
        for band, power in frame.band_mean.items():
            out[f"mean_{band}"] = round(power, 4)
        for ch, powers in frame.channel_powers.items():
            for band, power in powers.items():
                out[f"{ch}_{band}"] = round(power, 4)
        return out

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _simulate_raw_signal(self, profile: dict[str, float]) -> np.ndarray:  # type: ignore[type-arg]
        """Synthesise a time-domain EEG signal.

        Sums sinusoids at band-centre frequencies weighted by the intent profile,
        then adds Gaussian noise.
        """
        n_samples = int(self.sampling_rate * self.window_sec)
        t = np.linspace(0, self.window_sec, n_samples, endpoint=False)
        signal: np.ndarray = np.zeros(n_samples)  # type: ignore[type-arg]
        for band, weight in profile.items():
            phase = float(self._rng.uniform(0.0, 2.0 * np.pi))
            signal += weight * np.sin(2.0 * np.pi * _BAND_CENTRE_HZ[band] * t + phase)
        signal += self._rng.normal(0.0, self.noise_level, n_samples)
        return signal

    def _bandpower(self, signal: np.ndarray) -> dict[str, float]:  # type: ignore[type-arg]
        """Compute normalised band power via FFT (approximation of Welch's method)."""
        freqs = np.fft.rfftfreq(len(signal), d=1.0 / self.sampling_rate)
        power_spectrum = np.abs(np.fft.rfft(signal)) ** 2

        raw: dict[str, float] = {}
        for band, (lo, hi) in BAND_RANGES.items():
            mask = (freqs >= lo) & (freqs < hi)
            raw[band] = float(power_spectrum[mask].sum())

        total = sum(raw.values())
        return {band: val / total for band, val in raw.items()} if total > 0 else raw
