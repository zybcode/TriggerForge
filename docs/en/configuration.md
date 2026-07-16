# ⚙️ TriggerForge Configuration Specification

> **Version**: v1.1-PRO[cite: 2]
> **Notice**: This document is automatically generated from the system configuration schema. Do not modify this file manually. To introduce configuration changes, please update `src/triggerforge/core/schema.py` and re-run `python scripts/generate_docs.py`.[cite: 2]

---

## I. Global Configuration Parameters

The TriggerForge main configuration file utilizes the standard YAML format. The core parameters are structurally split into two primary modules: **Global Dispatching Parameters** and **Directory Monitoring Strategies**.[cite: 2]

### 1. Core Field Definition

| Field Name | Type | Default | Status | Description |
| --- | --- | --- | --- | --- |
| `watch_folders` | `List[WatchFolderSchema]` | `[]` | **(Required)** | A list of monitored directory strategies monitored by the engine. Supports multi-directory orchestration. |[cite: 2]

### 2. `WatchFolderSchema` (Directory Monitor Configuration Object)

<!-- WATCH_FOLDER_SCHEMA_TABLE -->

### 3. `PluginStrategySchema` (Plugin Execution Strategy Configuration Object)

<!-- PLUGIN_STRATEGY_SCHEMA_TABLE -->

---

## II. Production-Ready Configuration Sample (`config.sample.yaml`)

Below is a production-grade configuration sample. You can copy this content directly to create your local `config.yaml` for enterprise deployments:[cite: 2]

```yaml
# =================================================================
# TriggerForge Production Configuration Blueprint
# =================================================================

watch_folders:
  - path: "./storage/watch_folder"
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 4                      # Sentry layer dedicated thread pool concurrency capacity
    strategies:
      # Strategy 1: Invokes a modern compression pipeline with a tight 15-second timeout wall
      - plugin_name: "compress_plugin"
        plugin_version: "1.0.0"
        timeout: 15                     # 15s hard execution fence to prevent thread locking
        params:
          level: "high"
          archive_type: "tar.gz"

      # Strategy 2: Invokes a legacy data parsing pipeline mounted inside a separate virtual environment
      - plugin_name: "legacy_parser_plugin"
        plugin_version: "0.8.2"
        # Architectural Highlight: Circumvents dependency hell by dynamically running the child process in a separate sandbox environment
        python_path: "/opt/venv/legacy_env/bin/python" 
        timeout: 30                     # 30s timeout breaker
        params:
          legacy_mode: true
          encoding: "gbk"
```[cite: 2]

---

> ⚖️ To systematically validate the structural integrity of your deployment profiles, execute `triggerforge --check-config config.yaml` before starting the daemon to run self-describing static assertions against the schema.