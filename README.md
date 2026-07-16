
---

```markdown
# 🛠️ TriggerForge (v1.1-PRO)

> **An event-driven directory orchestration engine with robust subprocess sandboxing, configuration-as-code, and resilient fault isolation.**

TriggerForge is a modern, production-ready daemon designed to watch folders, orchestrate complex file-processing pipelines, and execute custom plugins inside highly isolated subprocesses.

---

## 🛠️ Development Setup

To ensure consistency in your development environment and stability in your test suite, please follow these steps:

### 1. Environment Preparation
TriggerForge uses a `src/` layout to keep the source code organized. To ensure that tests can correctly identify module paths, please always run `pytest` via `python -m` from the project root directory.

```bash
# 1. Create and activate a virtual environment (Windows PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install necessary dependencies
pip install -r requirements.txt

```

### 2. Running Tests

We prioritize both functionality and test stability. Our test suite includes an automatic module import path injection mechanism to ensure it runs consistently across different development environments.

```bash
# Run all tests from the project root directory
python -m pytest -s

```

*Note: If you encounter a `ModuleNotFoundError`, please ensure you are executing the command from the project root and that your virtual environment is activated. We have resolved complex module import issues via `__init__.py` shims and path injection, eliminating the need to manually configure `PYTHONPATH`.*

---

## ✨ Key Features

* 🛡️ **Subprocess Sandbox Isolation:** Run untrusted or legacy plugins in dedicated, memory-capped child processes.
* 🔄 **Architecture as Code:** Configuration documentation is auto-generated, ensuring consistency between schemas and documentation.
* ⚡ **Resilient Multi-Threading:** High-performance event dispatching powered by `ThreadPoolExecutor`.
* 🧪 **Zero-Flaky Test Suite:** Built-in Mock Filesystem tests ensure 100% stability for CI/CD pipelines.

---

## 🚀 Quick Start

### 1. Configure your Forge

Create a `config.yaml` file:

```yaml
watch_folders:
  - path: "./storage/watch"
    concurrency: 4
    strategies:
      - plugin_name: "example_plugin"
        timeout: 15

```

### 2. Start the Engine

```bash
python -m triggerforge.cli --config config.yaml

```

---

## 🤝 Contributing

We welcome contributions! Please follow project standards and ensure all tests pass via `python -m pytest` before submitting a PR.

---

## ⭐ Show Your Support

If you find TriggerForge helpful in streamlining your workflows, please give us a **Star**! ☕

```

```