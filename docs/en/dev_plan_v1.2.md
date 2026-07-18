# TriggerForge v1.2 Development Plan

> **Version**: v1.2-Final (Approved)
> **Status**: In Development
> **Path**: docs/en/dev_plan_v1.2.md

## 1. Overview
This version aims to establish an automated operational lifecycle for TriggerForge. The core objective is to implement a pipeline-driven approach to configuration management, and to enhance system stability and prevent deadlocks under high loads through the synergy of "Global Constraints + Plugin Strategies."

## 2. Key Task List

| No. | Module | Key Development Tasks |
| :--- | :--- | :--- |
| 1 | **Schema Extension** | Implement `priority` enum and `allow_override_timeout` flag with dual-constraint validation logic. |
| 2 | **Audit Engine** | Develop `ForgeConfigManager`, supporting `--check` mode and structured JSON output. |
| 3 | **Architecture Base** | Update documentation, detailing the process-level scheduling mechanism and v1.3 hot-reload roadmap. |
| 4 | **Migration Guide** | Create `migration_v1.2.md`, outlining deprecated keys and upgrade paths. |
| 5 | **Integration Tests** | Build unit tests covering permission-based exemptions and edge cases. |

## 3. Technical Requirements

### 3.1 Dual-Constraint Validation (`src/triggerforge/core/schema.py`)
In the `PluginStrategySchema`, implement a `model_validator`:
* When `allow_override_timeout` is `True`, `priority` MUST be set to `"high"`.
* Non-compliant configurations must trigger a `ValueError` during pre-flight, blocking engine execution.

### 3.2 Configuration Audit Interface (`src/triggerforge/utils/config_manager.py`)
* **CLI Interaction**: Terminal mode outputs human-readable reports; CI/CD mode (detected via `CI=true`) outputs structured JSON.
* **Exit Codes**:
    * **0**: Passed, configuration compliant.
    * **1**: Failed, non-compliant configuration (e.g., timeout violation).
    * **2**: File not found or YAML syntax error.
    * **3**: Internal execution exception.
* **JSON Structure**:
  ```json
  {"status": "fail", "exit_code": 1, "errors": [{"field": "...", "message": "..."}]}