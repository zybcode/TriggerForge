
---

# 🚀 TriggerForge Development Setup Guide

> **Version**: v1.1-PRO
> **Status**: Approved
> **Scope**: Guide for internal developers and open-source contributors on local environment initialization, dependency management, and engineering readiness.

---

## I. Prerequisites

Before setting up your local environment, ensure your development machine has the following infrastructure installed and configured:

* **Python Runtime**: **Python 3.10, 3.11, or 3.12** is highly recommended.
* **Build System (Hatch)**: TriggerForge abandons traditional `setup.py` scripts and fully embraces the PEP 621 standard, using **Hatch** as its modern packaging and environment management backend.
* **Operating System**: Fully compatible with Linux (recommended for production), macOS, and Windows.

---

## II. Rapid Local Environment Initialization

All project dependencies, build metadata, and virtual environment management configurations are declared inside `pyproject.toml` in the project root. You can spin up a fully isolated development environment in three steps:

### 1. Clone the Repository and Enter the Project Root

```bash
git clone https://github.com/zybcode/TriggerForge.git
cd TriggerForge

```

### 2. Install Hatch (If Not Already Installed)

Hatch serves as both a build utility and an exceptional virtual environment manager. You can install it globally via `pip` or your system's package manager:

```bash
pip install --user hatch

```

### 3. Synchronize Environment and Install Dependencies

Run the following command to let Hatch automatically spin up an isolated virtual environment and install the package along with all development and testing dependencies in **Editable Mode**:

```bash
# Initialize the default development environment and install dependencies
hatch env create

```

---

## III. Core Local Development Commands

When managing environments with Hatch, you never need to manually run activation commands like `source venv/bin/activate`. Hatch provides an elegant command orchestration interface instead:

### 1. Executing the Test Suite (Deterministic Testing Pipeline)

TriggerForge's test suite bypasses unpredictable disk I/O hooks via in-memory mock queues. Running tests locally is extremely fast and stable:

```bash
# Run pytest with code coverage tracking within the isolated virtual environment
hatch run cov

```

*(Note: Behind the scenes, this executes `pytest --cov=triggerforge tests/` and prints out a coverage breakdown).*

### 2. Running Arbitrary Commands Within the Virtual Environment

If you need to run local diagnostic scripts or tools within the context of your project's virtual environment, use `hatch run`:

```bash
# Inspect the Python version within the virtual environment
hatch run python --version

# Validate your configuration profile against the Pydantic schema assertions
hatch run triggerforge --check-config config.yaml

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
├── README.md                # Open-source landing page & dual-licensing business declaration
├── LICENSE                  # Open-source GNU GPL v3 license text
├── src/                     # Clean source code repository
│   └── triggerforge/        # Core package root
│       ├── main.py          # Engine daemon startup entry point
│       ├── core/            # Core system layers (Looper, Sentry, ForgeCore, Clerk)
│       │   └── schema.py    # Pydantic configuration schemas (Source of truth for "Architecture as Code")
│       └── plugins/         # Extensible plugin system path
│           └── base.py      # Abstract BaseClass (BasePlugin) that all plugins must inherit
├── tests/                   # 100% stable integration test suite
│   ├── conftest.py          # In-memory mock queue configuration
│   └── test_core.py         # Core process isolation and scheduling tests
└── scripts/
    └── generate_docs.py     # Automated configuration document extraction script

```

---

> ⚖️ **Important**: To prevent dependency conflicts within sandboxed child processes, never use global `pip install` commands to force-install packages. Any dependency additions or modifications must be declared inside the `[project.dependencies]` or `[tool.hatch.envs.default]` blocks in `pyproject.toml`, followed by running `hatch env prune && hatch env create` to cleanly rebuild the workspace.