# murtazai-bci-dapp

[![CI](https://github.com/murtazai/murtazai-bci-dapp/actions/workflows/ci.yml/badge.svg)](https://github.com/murtazai/murtazai-bci-dapp/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Typed: strict](https://img.shields.io/badge/typing-strict-informational)](https://mypy.readthedocs.io/)

> Built by **[Murtaza Ali Imtiaz](https://github.com/murtazaai)** · MurtazAI · April 2024–Present

> **EEG signal simulation → rig-core LLM classification → Ed25519 provenance signing → SHA-256 blockchain ledger**

A production-architecture Brain-Computer Interface (BCI) DApp pipeline. Designed for children with motor impairments, it turns raw EEG signals into cryptographically signed, tamper-evident session records committed to a hash-chained ledger - clinical-grade auditability without a full blockchain node.

---

## Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Development](#development)
- [Zed IDE Integration](#zed-ide-integration)
- [Module Reference](#module-reference)
- [Design Decisions](#design-decisions)
- [STAR Interview Story](#star-interview-story)

---

## Architecture

Each pipeline run processes one or more EEG sessions in four sequential stages:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          murtazai-bci-dapp                               │
│                                                                          │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐  │
│  │  EEGSimulator   │    │    BCIAgent       │    │ ProvenanceManager  │  │
│  │                 │    │                   │    │                    │  │
│  │  4-ch synthetic │───▶│  rig-core LLM /   │───▶│  Ed25519           │  │
│  │  Fp1 Fp2 C3 C4  │    │  OpenAI-compat    │    │  sign / verify     │  │
│  │                 │    │                   │    │                    │  │
│  │  δ θ α β γ bands│    │  relax | focus    │    └────────┬───────────┘  │
│  │  FFT band power │    │  fatigue | select │             │              │
│  │  SNR estimation │    │  + confidence     │             ▼              │
│  └─────────────────┘    │  + reasoning      │    ┌────────────────────┐  │
│                          └──────────────────┘    │ MockBlockchain     │  │
│                                                   │ Ledger             │  │
│                                                   │                    │  │
│                                                   │  SHA-256 chained   │  │
│                                                   │  JSON persistence  │  │
│                                                   │  verify_chain()    │  │
│                                                   └────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Data flow per session:**

```
EEGSimulator.generate_frame()          →  EEGFrame
    │   .to_feature_dict()
    ▼
BCIAgent.classify(features)            →  IntentResult  { intent, confidence, reasoning }
    │   .to_payload()
    ▼
ProvenanceManager.sign_session()       →  signed record  { payload + Ed25519 sig + pubkey }
    │
    ▼
MockBlockchainLedger.append()          →  Block  { SHA-256 hash-linked, JSON-persisted }
```

---

## Project Structure

```
murtazai-bci-dapp/
├── src/
│   └── bci_dapp/
│       ├── __init__.py           # Public API - all importable names in one place
│       ├── __version__.py        # Single source of truth for version string
│       ├── exceptions.py         # BCIDAppError hierarchy
│       ├── settings.py           # Env-var driven Settings (frozen dataclass)
│       ├── logging_config.py     # configure_logging() - call once at startup
│       ├── eeg_simulator.py      # EEGSimulator + EEGFrame
│       ├── llm_agent.py          # BCIAgent + IntentResult
│       ├── provenance.py         # ProvenanceManager (Ed25519 sign/verify)
│       ├── blockchain_ledger.py  # MockBlockchainLedger + Block + ChainVerification
│       └── cli.py                # bci-dapp entry point (run_pipeline + main)
├── tests/
│   ├── conftest.py               # Shared fixtures: sim, agent, provenance, keypair, ledger
│   ├── test_eeg_simulator.py     # 11 tests
│   ├── test_llm_agent.py         # 13 tests
│   └── test_provenance_ledger.py # 17 tests  ─── 41 total
├── .zed/
│   ├── tasks.json                # 29 Zed task runner configs
│   └── debug.json                # 17 DAP debugger configs
├── .github/
│   └── workflows/ci.yml          # Lint + test matrix (Python 3.11, 3.12)
├── data/
│   └── ledger.json               # Runtime ledger (gitignored)
├── pyproject.toml                # Build, deps, ruff, mypy, pytest, coverage
├── .pre-commit-config.yaml       # trailing-whitespace, ruff, mypy hooks
├── .env.example                  # Documents every supported env var
└── .gitignore
```

---

## Quick Start

**Prerequisites:** Python ≥ 3.11, pip.

```bash
git clone https://github.com/murtazai/murtazai-bci-dapp.git
cd murtazai-bci-dapp

# Install with dev tools
pip install -e ".[dev]"

# Run the pipeline (no API key needed)
bci-dapp
```

**Sample output:**

```
════════════════════════════════════════════════════════════
  MurtazAI BCI DApp - EEG → LLM → Blockchain Provenance
════════════════════════════════════════════════════════════

  Classifier   : Rule-based
  Sessions     : 5
  Ledger       : data/ledger.json
  Public Key   : 47a89a3375515127397af4e3…

────────────────────────────────────────────────────────────

  Session 01  Block #1
  Intent     : FOCUS    [█████████████████░░░] 85%
  Reasoning  : High beta power is consistent with active concentration.
  SNR        : 16.8 dB   Dominant: beta
  Bands      :  DEL 0.00  THE 0.02  ALP 0.18  BET 0.73  GAM 0.07
  Session ID : 8cea8681-451b-43de-a455-776e6c656c9f
  Block Hash : 1f4216ee1fc80a78…
  Sig Valid  : ✓ YES

  ✓ Chain verified - all 5 blocks intact
```

---

## Usage

### CLI

The `bci-dapp` command is registered as a package entry point via `pyproject.toml`:

```bash
bci-dapp                        # 5 sessions, rule-based classifier
bci-dapp --n 20                 # custom session count
bci-dapp --llm                  # LLM classifier (requires OPENAI_API_KEY)
bci-dapp --export               # write data/ledger_export.json after the run
bci-dapp --n 10 --llm --export  # combine flags
```

| Flag | Type | Default | Description |
|---|---|---|---|
| `--n` | `int` | `5` | Number of EEG sessions to simulate |
| `--llm` | flag | off | Use LLM classifier instead of rule-based fallback |
| `--export` | flag | off | Export the full ledger to `data/ledger_export.json` |

### Python API

```python
from bci_dapp import (
    EEGSimulator,
    BCIAgent,
    ProvenanceManager,
    MockBlockchainLedger,
)

sim        = EEGSimulator(seed=42)      # seed=None for random each run
agent      = BCIAgent(use_llm=False)    # True requires OPENAI_API_KEY
provenance = ProvenanceManager()
ledger     = MockBlockchainLedger(ledger_path="data/ledger.json")
keypair    = provenance.generate_keypair()

# Run one session
frame    = sim.generate_frame()
features = sim.to_feature_dict(frame)
result   = agent.classify(features)
record   = provenance.sign_session(result.to_payload(), keypair)
block    = ledger.append(record)

print(f"intent={result.intent}  confidence={result.confidence:.0%}")
print(f"block=#{block.index}  hash={block.block_hash[:16]}…")
print(f"sig_valid={provenance.verify_record(record)}")

# Verify the full chain
v = ledger.verify_chain()
print(f"chain valid={v.valid}  blocks={ledger.height}")
```

To point `BCIAgent` at a local rig-core or Ollama instance - no other code changes needed:

```python
agent = BCIAgent(base_url="http://localhost:11434/v1", model="llama3")
```

---

## Configuration

Copy `.env.example` to `.env` and override any value. The `.env` file is gitignored.

```bash
cp .env.example .env
```

| Environment Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `murtazai-bci-dapp` | Application name for logging |
| `APP_DEBUG` | `false` | Enable debug mode (`true`/`1`/`yes`) |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint (swap for rig-core/Ollama) |
| `LLM_MODEL` | `gpt-4o-mini` | Model identifier passed to the completion endpoint |
| `OPENAI_API_KEY` | _(empty)_ | API key - when absent, the rule-based classifier is used |
| `EEG_SAMPLING_RATE` | `256` | Simulated sample rate in Hz (matches Emotiv EPOC) |
| `EEG_WINDOW_SEC` | `2.0` | Analysis window duration in seconds |
| `LEDGER_PATH` | `data/ledger.json` | JSON file path for ledger persistence |

Settings are loaded once at import time into a frozen `Settings` dataclass singleton:

```python
from bci_dapp.settings import settings

agent = BCIAgent(base_url=settings.llm_base_url, model=settings.llm_model)
```

---

## Development

### Install dev dependencies

```bash
pip install -e ".[dev]"
```

### Run the test suite

```bash
pytest                              # all 41 tests with coverage
pytest tests/test_eeg_simulator.py  # single module
pytest -x                           # stop on first failure
pytest --last-failed                # re-run only failed tests
```

Coverage is enforced at ≥ 80% branch coverage via `pyproject.toml`. HTML report:

```bash
pytest --cov-report=html:htmlcov && python -m http.server 8080 --directory htmlcov
```

### Lint and format

```bash
ruff check src/ tests/          # lint
ruff check --fix src/ tests/    # lint with auto-fix
ruff format src/ tests/         # format
ruff format --check src/ tests/ # format check (CI mode)
```

### Type checking

```bash
mypy src/
```

Mypy runs in `strict` mode. The `numpy.*` module is exempt via `ignore_missing_imports`.

### Pre-commit hooks

```bash
pre-commit install       # install hooks (run once after cloning)
pre-commit run --all-files
```

Hooks: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`,
`check-merge-conflict`, `debug-statements`, `ruff`, `ruff-format`, `mypy`.

### CI

GitHub Actions runs on every push and pull request to `main`/`master`:

- **Lint job** - `ruff check`, `ruff format --check`, `mypy src/` (Python 3.12)
- **Test job** - `pytest` on Python 3.11 and 3.12 in parallel; coverage uploaded to Codecov on 3.12

---

## Zed IDE Integration

`.zed/tasks.json` and `.zed/debug.json` are included for first-class Zed support.

### Tasks (29 total) - `Ctrl+Shift+P` → `task: spawn`

| Group | Tasks |
|---|---|
| **Setup** | Install all dependencies, install pre-commit hooks, install debugpy |
| **Test** | All tests, with coverage, current file, fail-fast, per-module (EEG / LLM / Provenance), last-failed, open HTML report |
| **Lint** | `ruff check`, `ruff check --fix`, `ruff format`, `ruff format --check`, current file, `mypy src/`, mypy current file, pre-commit all |
| **Run** | Pipeline 5 sessions, 10 sessions, +export, LLM mode, DEBUG logging |
| **Inspect** | Print version, dump ledger JSON, smoke-test EEG frame, smoke-test keypair |

### Debug configurations (17 total) - `Ctrl+Shift+D`

| Group | Configurations |
|---|---|
| **Pipeline** | CLI 5 sessions, CLI 10 sessions + export, CLI LLM mode |
| **pytest** | All tests, current test file, EEG Simulator, LLM Agent, Provenance & Ledger, fail-fast `-x`, last-failed |
| **Module** | `eeg_simulator.py`, `blockchain_ledger.py`, `provenance.py`, `llm_agent.py`, current file, current file with stop-on-entry |
| **Attach** | Attach to running `debugpy` server on `127.0.0.1:5678` |

All debug configs set `PYTHONPATH=$ZED_WORKTREE_ROOT/src`, `justMyCode: false`, and `LOG_LEVEL=DEBUG`. For remote attach, start the process separately with:

```bash
python -m debugpy --listen 5678 --wait-for-client -m bci_dapp.cli --n 5
```

---

## Module Reference

### `eeg_simulator` - Signal generation

**`EEGFrame`** `(frozen dataclass)` - one windowed snapshot of EEG features.

| Field | Type | Description |
|---|---|---|
| `channel_powers` | `dict[str, dict[str, float]]` | Per-channel relative band power `{channel: {band: power}}` |
| `band_mean` | `dict[str, float]` | Band powers averaged across all channels |
| `dominant_band` | `str` | Band with the highest mean power |
| `snr_db` | `float` | Simulated signal-to-noise ratio |

**`EEGSimulator`** - generates `EEGFrame` objects from intent-biased sinusoidal signals.

| Method | Description |
|---|---|
| `generate_frame(intent?)` | Synthesise one 2-second EEG window at 256 Hz across 4 channels |
| `to_feature_dict(frame)` | Flatten an `EEGFrame` into a plain dict for the LLM prompt or provenance payload |

Channels: `Fp1`, `Fp2`, `C3`, `C4`. Bands: `delta (0.5–4 Hz)`, `theta (4–8 Hz)`, `alpha (8–13 Hz)`, `beta (13–30 Hz)`, `gamma (30–100 Hz)`. Intent profiles bias band-power weights toward the expected dominant band for each of the four intents. Pass `seed=` for fully reproducible output.

---

### `llm_agent` - Intent classification

**`IntentResult`** `(frozen dataclass)` - immutable classification output.

| Field | Type | Description |
|---|---|---|
| `intent` | `str` | One of `relax \| focus \| fatigue \| select` |
| `confidence` | `float` | Classifier confidence in `[0.0, 1.0]` |
| `reasoning` | `str` | One-sentence natural-language explanation |
| `raw_features` | `dict[str, Any]` | Original feature dict passed to the classifier |

`to_payload()` returns a JSON-serialisable dict ready for provenance signing, containing `intent`, `confidence`, `reasoning`, and an `eeg_summary` of mean band powers.

**`BCIAgent`** - classifies EEG features via LLM or rule-based fallback.

| Method | Description |
|---|---|
| `classify(features)` | Returns `IntentResult`; falls back to rule-based on any network / parse error |

The LLM path calls any OpenAI-compatible `/chat/completions` endpoint at `temperature=0.2`. The rule-based fallback checks `dominant_band` first and uses band-power thresholds as tiebreakers - runs offline with no API key and is used by all tests.

---

### `provenance` - Ed25519 signing

**`ProvenanceManager`** - keypair generation and session record signing.

| Method | Description |
|---|---|
| `generate_keypair()` | Returns `{"private_key": "<hex>", "public_key": "<hex>"}` |
| `sign_session(payload, keypair, *, session_id?)` | Signs the payload with Ed25519; returns a self-contained verifiable record |
| `verify_record(record)` | Returns `True` if the signature is valid; never raises |

The canonical form signed is a deterministic JSON serialisation of `{session_id, timestamp, payload}` with `sort_keys=True`. The signature, public key, and original payload are all embedded in the returned record so any party can verify it offline without trusting the ledger.

---

### `blockchain_ledger` - Hash-chained ledger

**`Block`** `(frozen dataclass)` - one immutable hash-linked entry.

| Field | Type | Description |
|---|---|---|
| `index` | `int` | Zero-based chain position (0 = genesis) |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
| `session_id` | `str` | Session ID from the provenance record |
| `record` | `dict[str, Any]` | Full signed provenance record |
| `previous_hash` | `str` | SHA-256 hash of the preceding block |
| `block_hash` | `str` | SHA-256 hash of this block's canonical content |

**`MockBlockchainLedger`** - append-only ledger with JSON persistence.

| Method / Property | Description |
|---|---|
| `append(record)` | Hash-chain a signed record into a new `Block` and auto-save |
| `verify_chain()` | Walk every block; check stored hash vs recomputed and previous-hash links |
| `get_block(index)` | Return `Block` at position or `None` |
| `get_session(session_id)` | Return the `Block` containing the given session ID or `None` |
| `export()` | Return the full chain as a JSON-serialisable list |
| `height` | Number of non-genesis data blocks |
| `head` | Most recently appended block |

`verify_chain()` returns a `ChainVerification(valid, n_invalid, errors)` frozen dataclass. Replacing `_save` / `_load` with Anchor program calls converts this to an on-chain Solana ledger - the signing and hashing layers above are fully chain-agnostic.

---

### `exceptions` - Error hierarchy

```
BCIDAppError
├── SignatureError(message)              - Ed25519 sign / verify failures
├── ChainIntegrityError(block_index, detail)  - hash-chain tamper detection
└── ClassificationError(detail)          - intent classification failures
```

Always catch these specific types rather than bare `Exception`.

---

### `settings` - Environment configuration

```python
from bci_dapp.settings import settings

print(settings.llm_base_url)   # "https://api.openai.com/v1"
print(settings.ledger_path)    # "data/ledger.json"
```

`Settings` is a `frozen=True, slots=True` dataclass loaded once at import. All fields are overridable via env vars (see [Configuration](#configuration)).

---

### `logging_config` - Logging setup

```python
from bci_dapp.logging_config import configure_logging

configure_logging(level="DEBUG")  # call once at application startup
```

Library modules use `logger = logging.getLogger(__name__)` and never call `configure_logging`. The CLI calls it in `main()` before running the pipeline.

---

## Design Decisions

**Ed25519 over ECDSA.** Ed25519 provides 128-bit security with ~64-byte signatures and constant-time signing, making it suitable for resource-constrained BCI hardware. The `cryptography` library's implementation is production-grade. The same key format is native to Solana (`Ed25519Program`), so on-chain migration requires no cryptographic changes.

**Frozen dataclasses with `slots=True` for all value objects.** `EEGFrame`, `IntentResult`, `Block`, `ChainVerification`, and `Settings` are all `frozen=True, slots=True`. This enforces immutability at the Python level, reduces per-instance memory overhead, and makes the objects safe to hash and cache. `Block.__post_init__` uses `object.__setattr__` to set `block_hash` on a frozen instance, which is the correct idiom.

**Rule-based fallback over silent failure.** `BCIAgent.classify` catches only recoverable errors (`URLError`, `JSONDecodeError`, `KeyError`, `ValueError`) and returns a new `IntentResult` with the fallback reasoning prefixed `[LLM fallback: ...]`. The pipeline never silently drops a session. This is tested explicitly: `test_fallback_on_llm_failure_preserves_result` points at `localhost:0` to force a connection error and asserts the result is still a valid `IntentResult`.

**Seeded numpy RNG throughout.** The original code used `random.choice` for intent selection, which bypassed the numpy seed. All randomness now flows through `self._rng = np.random.default_rng(seed)`, including intent selection, phase angles, noise, and SNR sampling. `test_reproducible_with_seed` and `test_seeded_rng_controls_intent_selection` enforce this property.

**Canonical JSON for signing and hashing.** Both `ProvenanceManager.sign_session` and `Block.compute_hash` serialise with `sort_keys=True, separators=(",", ":")`. Field insertion order is irrelevant to signature and hash validity, which matters when records travel over HTTP or are reconstructed from storage.

---

## STAR Interview Story

**Situation.** Children with motor impairments need a non-invasive way to interact with digital environments. Raw EEG signals are noisy, high-dimensional, and clinically meaningless without interpretation - and any interpretation used in a therapeutic context must be auditable and tamper-evident to maintain trust.

**Task.** Design and build a complete BCI DApp pipeline that takes simulated Emotiv EPOC signals, classifies user intent with an LLM agent, and commits every interpretation to a cryptographically signed, hash-chained ledger - demonstrating both rig-core agentic AI and Web3 blockchain architecture in a single runnable project.

**Action.**
- Built `EEGSimulator` to produce intent-biased, statistically plausible 4-channel EEG at 256 Hz with FFT band-power extraction. All randomness flows through a seeded numpy Generator so any test run is exactly reproducible.
- Wired `BCIAgent` against a rig-core / OpenAI-compatible `/chat/completions` endpoint with a BCI-specific system prompt and `temperature=0.2`. A deterministic rule-based fallback handles offline / CI runs and serves as the test double.
- Implemented `ProvenanceManager` using Ed25519 (cryptography ≥ 42) - every session payload is canonically serialised and signed before it touches the ledger. Signatures are self-contained and verifiable without trusting any server.
- Built `MockBlockchainLedger` with SHA-256 hash-chaining, frozen immutable `Block` dataclasses, JSON persistence, and a full `verify_chain()` integrity check.
- Applied the python_template standard: `src/` layout, `pyproject.toml` (hatchling, ruff, mypy strict, pytest-cov ≥ 80%), `frozen=True, slots=True` dataclasses, `collections.abc.Sequence`, parameterised return types throughout, pre-commit hooks, and GitHub Actions CI matrix on Python 3.11 + 3.12.
- Added Zed IDE integration: 29 task runner configs and 17 DAP debug configurations covering every module, pytest variant, CLI option, and remote-attach scenario.

**Result.** A fully runnable, screen-capturable demo that shows EEG → LLM → signed provenance → verified chain in under 200 ms per session. 41 tests, 100% passing. Replacing `_save`/`_load` in `MockBlockchainLedger` with Anchor program calls produces a production Solana deployment - the signing, hashing, and classification layers are chain-agnostic.

---

## Author

**Murtaza Ali Imtiaz** · Polar Bear Systems · Pakistan (remote - open to US/EU)
[very.kool.king@gmail.com](mailto:very.kool.king@gmail.com) · [GitHub](https://github.com/murtazai) · [LinkedIn](https://linkedin.com/in/murtazai)

## License

© 2026 Murtaza Ali Imtiaz
