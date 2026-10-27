# ⚙️ TriggerForge Configuration Specification

> **Version**: v1.1-PRO
> **Source of truth**: `src/triggerforge/core/schema.py`
> **Notice**: Field definitions on this page mirror the Pydantic models in `schema.py`. Keep them in sync when the schema changes.

---

## I. Global Configuration Parameters

The TriggerForge main configuration file uses the standard YAML format. Core parameters are split into two modules: **Global Dispatching Parameters** and **Directory Monitoring Strategies**.

### 1. Core Field Definition

| Field Name | Type | Default | Status | Description |
| --- | --- | --- | --- | --- |
| `watch_folders` | `List[WatchFolderSchema]` | none | **(Required)** | List of monitored directory strategies. Multiple independent directories are supported. |
| `plugin_directory` | `str` | `"./plugins"` | Optional | Plugin root directory. The engine resolves `{plugin_name}/main.py` inside it. |
| `debounce_seconds` | `float` | `1.0` | Optional | Global default write-debounce window (seconds), must be > 0. Overridable per watch folder. |

### 2. `WatchFolderSchema` (Directory Monitor Configuration Object)

| Field Name | Type | Default | Status | Description |
| --- | --- | --- | --- | --- |
| `path` | `str` | none | **(Required)** | Directory to watch. Dropping a file here triggers the plugin pipeline. |
| `success_path` | `str` | none | **(Required)** | Archive directory for files whose full pipeline succeeded (atomic move). |
| `error_path` | `str` | none | **(Required)** | Quarantine directory for files that failed or timed out (atomic move). |
| `concurrency` | `int` | `1` | Optional | Number of worker threads assigned to this directory, must be > 0. |
| `debounce_seconds` | `float` | `1.0` | Optional | Directory-specific write-debounce window (seconds), must be > 0. |
| `strategies` | `List[StrategySchema]` | none | **(Required)** | Ordered, sequentially executed plugin strategy pipeline. |

### 3. `StrategySchema` (Plugin Execution Strategy Configuration Object)

| Field Name | Type | Default | Status | Description |
| --- | --- | --- | --- | --- |
| `plugin_name` | `str` | none | **(Required)** | Plugin directory name; resolves `{plugin_directory}/{plugin_name}/main.py`. |
| `plugin_version` | `str` | `"0.0.0"` | Optional | Plugin version marker used for runtime validation and auditing. |
| `timeout` | `int` | `30` | Optional | Hard timeout (seconds) for the plugin subprocess, must be > 0. |
| `params` | `Dict[str, Any]` | `{}` | Optional | Dynamic custom parameters injected into the plugin subprocess as JSON. |
| `python_path` | `Optional[str]` | `None` | Optional | Path to an isolated interpreter (virtualenv). Falls back to the current interpreter if missing. |

---

## II. Production-Ready Configuration Sample (`config.sample.yaml`)

Below is a production-grade configuration sample. Copy it to create your local `config.yaml`:

```yaml
# =================================================================
# TriggerForge Production Configuration Blueprint
# =================================================================

# Plugin root: the engine resolves {plugin_directory}/{plugin_name}/main.py
plugin_directory: "./plugins"

# Global default debounce window (seconds); overridable per watch folder
debounce_seconds: 1.0

watch_folders:
  - path: "./storage/watch_folder"        # dropping a file here triggers the pipeline
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 4                        # dedicated worker threads for this directory
    debounce_seconds: 1.0                 # directory-specific debounce window

    strategies:
      # Strategy 1: modern compression plugin with a 15s hard timeout
      - plugin_name: "compress_plugin"
        plugin_version: "1.0.0"
        timeout: 15
        params:
          level: "high"
          archive_type: "tar.gz"

      # Strategy 2: legacy parser running inside an isolated virtualenv
      - plugin_name: "legacy_parser_plugin"
        plugin_version: "0.8.2"
        python_path: "/opt/venv/legacy_env/bin/python"
        timeout: 30
        params:
          legacy_mode: true
          encoding: "gbk"
```

---

## III. Runtime Behavior

1. **Event path**: file written into the watched directory → debounce window waits for the write to finish → event enters the buffer queue → worker thread consumes it → `strategies` run sequentially.
2. **Short-circuit**: if any strategy fails, remaining strategies are skipped and the file goes to the error zone.
3. **Archiving**: all strategies succeeded → `success_path`; any failure → a `.panic.json` diagnostic report is written and the file is moved to `error_path`.
4. **Validation**: config is validated at startup via `TriggerForgeConfigSchema`; use `--dry-run` to validate without starting watchers.
