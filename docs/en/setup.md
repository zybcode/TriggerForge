
---

# 🚀 TriggerForge Development Setup Guide

> **Version**: v1.1-PRO
> **Status**: Approved
> **Scope**: Guide for internal developers and open-source contributors on local environment initialization, dependency management, and engineering readiness.

---

## I. Prerequisites

Before setting up your local environment, ensure your development machine has the following infrastructure installed and configured:

* **Python Runtime**: **Python 3.11 or newer** is required (matching `requires-python = ">=3.11"` in `pyproject.toml`).
* **Build System (Hatch, optional)**: TriggerForge abandons traditional `setup.py` scripts and fully embraces the PEP 621 standard, using **Hatch** as its modern packaging and environment management backend. Hatch is optional — plain `pip` works for all development tasks (see Option B below).
* **Operating System**: Fully compatible with Linux (recommended for production), macOS, and Windows.

---

## II. Rapid Local Environment Initialization

Pick one of the two options below. **Either way, install the dependencies before running the tests**, otherwise pytest fails during collection with a batch of `ModuleNotFoundError`s (import errors, not test failures).

### Option A: Hatch-Managed Environment (Recommended)

All project dependencies, build metadata, and virtual environment management configurations are declared inside `pyproject.toml` in the project root.

#### 1. Clone the Repository and Enter the Project Root

```bash
git clone https://github.com/zybcode/TriggerForge.git
cd TriggerForge

```

#### 2. Install Hatch (If Not Already Installed)

Hatch serves as both a build utility and an exceptional virtual environment manager. You can install it globally via `pip` or your system's package manager:

```bash
pip install --user hatch

```

#### 3. Synchronize Environment and Install Dependencies

Run the following command to let Hatch automatically spin up an isolated virtual environment and install the package along with all development and testing dependencies in **Editable Mode**:

```bash
# Initialize the default development environment and install dependencies
hatch env create

```

### Option B: Minimal pip Environment

No Hatch required — install the project and test tools into your current interpreter (global or virtualenv) directly:

```bash
# 1. Install the project in editable mode (pulls in watchdog / pydantic / pyyaml)
python -m pip install -e .

# 2. Install the test tooling
python -m pip install pytest pytest-cov

# 3. Run the suite from the project root
python -m pytest
```

> 💡 **Common pitfall**: if the interpreter behind your `pytest` command differs from the one where the dependencies were installed (e.g. `pytest.exe` lives in Python 3.12's `Scripts/` while the deps landed in another Python), you get mass `ModuleNotFoundError`s during collection. Verify with `pytest --version` and `where pytest` / `where python` that both sides point to the same environment.

---

## III. Core Local Development Commands

### 1. Executing the Test Suite

```bash
# Option A (Hatch): run pytest with coverage inside the managed environment
hatch run cov

# Option B (pip): run directly from the project root
python -m pytest

# Unit tests only / integration tests only
python -m pytest tests/unit
python -m pytest tests/integration
```

The current suite contains 47 tests (38 unit + 9 integration) and completes in roughly 10–25 seconds.

### 2. Running Arbitrary Commands Within the Virtual Environment

If you need to run local diagnostic scripts or tools within the context of your project's virtual environment, use `hatch run`:

```bash
# Inspect the Python version within the virtual environment
hatch run python --version

# Validate your configuration profile against the Pydantic schema (no watchers started)
hatch run triggerforge --config config.yaml --dry-run

```

### 3. Entering the Environment Shell

If you prefer to work inside an active virtual environment shell for frequent debugging sessions, launch the managed shell:

```bash
hatch shell

```

Once inside, you can run commands like `pytest`, `python`, or `triggerforge` directly. Simply type `exit` to safely close the session when finished.

---

## IV. Project Directory Layout & Key Paths

Before developing and committing code, make sure you are familiar with our standard `src/` layout structure:

```plaintext
TriggerForge/
├── pyproject.toml           # Unified project config file complying with PEP 621 specifications
├── config.yaml              # Runtime config (watched folders & plugin strategies)
├── config.sample.yaml       # Production-grade configuration sample
├── mkdocs.yml               # Docs site navigation config
├── README.md                # Open-source landing page & quick start
├── LICENSE                  # Open-source GNU GPL v3 license text
├── docs/                    # Bilingual documentation site (mkdocs-material)
├── src/                     # Clean source code repository
│   └── triggerforge/
│       ├── main.py          # Engine daemon startup entry point
│       ├── cli.py           # CLI entrypoint (--config / --dry-run / --version)
│       ├── core/
│       │   ├── looper.py    # Orchestrator: queue + worker threads + pipeline wiring
│       │   ├── schema.py    # Pydantic config schemas (single source of truth)
│       │   ├── runner/      # ForgeCore: PluginRunner subprocess sandbox
│       │   ├── sentry/      # Sentry: watcher / queue / filter
│       │   └── clerk/       # Clerk: archiver (file zones) / journal (panic reports)
│       └── plugins/
│           └── base.py      # Optional plugin abstract base class (see plugin_dev.md)
└── tests/
    ├── conftest.py          # Shared fixtures & src path injection
    ├── unit/                # 38 unit tests
    └── integration/         # 9 integration tests (incl. real-watchdog e2e)

```

---

> ⚖️ **Important**: To prevent dependency conflicts within sandboxed child processes, always declare dependencies in the `[project.dependencies]` or `[tool.hatch.envs.default]` blocks of `pyproject.toml` and sync from there. For everyday local development, Option B's `pip install -e .` is also a supported path; the key requirement is that **the interpreter running pytest is the same one where the dependencies are installed**.