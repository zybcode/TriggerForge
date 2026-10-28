# ⚙️ TriggerForge Configuration Specification

> **Version**: v1.2-Final
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
| `max_execution_timeout` | `Optional[int]` | `None` | Optional (v1.2) | Global hard execution-timeout ceiling (safety baseline). A strategy `timeout` exceeding it is clamped at runtime unless the strategy holds the `priority="high"` + `allow_override_timeout=true` exemption. |

> **v1.2 deprecation**: the legacy global `timeout` key is auto-mapped to `max_execution_timeout` with a `DeprecationWarning`; removal is planned for v1.4. See the [Migration Guide](./migration_v1.2.md).

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
| `timeout` | `int` | `30` | Optional | Hard timeout (seconds) for the plugin subprocess, must be > 0. The legacy flat form is deprecated; migrate to the `strategy.timeout` nested object (flat form removal planned for v1.4). |
| `params` | `Dict[str, Any]` | `{}` | Optional | Dynamic custom parameters injected into the plugin subprocess as JSON. |
| `python_path` | `Optional[str]` | `None` | Optional | Path to an isolated interpreter (virtualenv). Falls back to the current interpreter if missing. |
| `strategy` | `Optional[dict]` | `None` | Optional (v1.2) | **New standard nested object**: may carry `timeout` / `priority` / `allow_override_timeout`; nested keys take precedence over flat fields. |
| `priority` | `Literal["high","standard","low"]` | `"standard"` | Optional (v1.2) | Strategy priority enum. **Only `high` supports timeout override**; `standard` and `low` do not. |
| `allow_override_timeout` | `bool` | `false` | Optional (v1.2) | Timeout-override exemption switch. **Dual constraint**: setting it to `true` requires `priority="high"` simultaneously, otherwise pre-flight raises `ValueError` and blocks engine start (resource anti-lockout). |
| `metadata` | `Dict[str, Any]` | `{}` | Optional (v1.2) | Commercial extension slot (digital signature / License Hash / customer authorization). Placeholder-only in v1.2 open-source; ignored during startup validation for forward compatibility. |

---

## II. Production-Ready Configuration Sample (`config.sample.yaml`)

Below is a production-grade configuration sample. Copy it to create your local `config.yaml`:

```yaml
# =================================================================
# TriggerForge Production Configuration Blueprint (v1.2)
# =================================================================

# Plugin root: the engine resolves {plugin_directory}/{plugin_name}/main.py
plugin_directory: "./plugins"

# Global default debounce window (seconds); overridable per watch folder
debounce_seconds: 1.0

# Global hard execution-timeout ceiling (safety baseline, v1.2)
max_execution_timeout: 300

watch_folders:
  - path: "./storage/watch_folder"        # dropping a file here triggers the pipeline
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 4                        # dedicated worker threads for this directory
    debounce_seconds: 1.0                 # directory-specific debounce window

    strategies:
      # Strategy 1 (v1.2 nested form): high-priority core, may exceed the global cap
      - plugin_name: "compress_plugin"
        plugin_version: "1.0.0"
        strategy:
          timeout: 15
          priority: "high"                # only "high" supports allow_override_timeout
          allow_override_timeout: true    # must be combined with priority: high
        params:
          level: "high"
          archive_type: "tar.gz"

      # Strategy 2: standard-priority parser running inside an isolated virtualenv
      - plugin_name: "legacy_parser_plugin"
        plugin_version: "0.8.2"
        python_path: "/opt/venv/legacy_env/bin/python"
        strategy:
          timeout: 30
          priority: "standard"            # default; no timeout override allowed
        params:
          legacy_mode: true
          encoding: "gbk"
```

---

## III. Runtime Behavior

1. **Event path**: file written into the watched directory → debounce window waits for the write to finish → event enters the buffer queue → worker thread consumes it → `strategies` run sequentially.
2. **Short-circuit**: if any strategy fails, remaining strategies are skipped and the file goes to the error zone.
3. **Archiving**: all strategies succeeded → `success_path`; any failure → a `.panic.json` diagnostic report is written and the file is moved to `error_path`.
4. **Validation**: config is validated at startup via `TriggerForgeConfigSchema`; use `--dry-run` to validate without starting watchers, or `--check` to run the full v1.2 compliance audit (exit codes 0/1/2/3).
5. **Resource anti-lockout (v1.2)**: a strategy `timeout` exceeding `max_execution_timeout` is clamped to the ceiling at runtime; only strategies with `priority="high"` and `allow_override_timeout=true` are exempt.
6. **Hot reload (v1.2)**: send `SIGHUP` to the engine process to trigger config hot reload; the new config is fully audited by `ForgeConfigManager` first — on failure the running config is kept unchanged and an alert is logged, on success the config set is atomically swapped ("validate-then-replace") with a before/after audit summary.
