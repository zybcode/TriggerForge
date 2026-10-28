# 🔌 TriggerForge Plugin Development Specification

> **Version**: v1.1-PRO
> **Status**: Approved
> **Implementation**: `src/triggerforge/core/runner/plugin_runner.py`
> **Scope**: Definitive lifecycle interface guide for internal developers and open-source contributors building modular workflows.

---

## I. Architectural Philosophy & Sandbox Constraints

To maintain absolute core resilience, TriggerForge enforces a strict **Zero-Trust Plugin Model**. Every plugin registered in the execution pipeline is subject to the following runtime guardrails:

1. **Subprocess Sandboxing**: Plugins never execute inside the primary monitoring process. They are invoked as independent subprocesses, so memory limits and fatal runtime errors (e.g. segfaults) are safely contained.
2. **Defensive Timeouts**: Every plugin lifecycle is bound by a hard execution fence. A plugin blocking beyond its `timeout` is forcefully terminated and the file is quarantined.
3. **Dynamic Virtual Environments**: plugins may target a specific Python runtime via `python_path`, letting legacy scripts with old dependencies coexist with modern pipelines.
4. **Short-Circuit**: `strategies` for a directory run sequentially; the first failure skips all remaining strategies.

---

## II. Plugin Layout & Entrypoint Convention

Plugins are stored in a **flat directory layout**, one directory per plugin:

```plaintext
{plugin_directory}/           # configured via plugin_directory, default ./plugins
└── my_plugin/                # directory name must equal plugin_name in the strategy
    └── main.py               # entrypoint (alternatives: plugin.py, index.py)
```

The engine resolves the entrypoint in the order `main.py` → `plugin.py` → `index.py`; if none exists the strategy is considered failed.

---

## III. Execution Contract (Process-Level Interface)

Plugins are **not** wired in via class inheritance. The engine launches your plugin as an executable Python script with this command line:

```bash
{interpreter} {plugin_main.py} {target_file} ["{json_params}"]
```

### 1. Input Channels

| Channel | Content | Notes |
| :--- | :--- | :--- |
| `sys.argv[1]` | **Absolute path** of the target file | Always provided; the file dropped into the watched directory. |
| `sys.argv[2]` | JSON string of the strategy `params` | Only passed when `params` is non-empty. |
| Env var `TRIGGERFORGE_PARAMS` | JSON string of the strategy `params` | Only set when `params` is non-empty; convenient for plugins that do not parse argv. |
| Working directory | The engine's current working directory | Never assume cwd is the watched directory; use the absolute path from `argv[1]`. |

### 2. Output Contract

A plugin must write **exactly one JSON object to stdout** describing the outcome:

```json
{"status": "success", "message": "processed 42 rows"}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `status` | `str` | Yes | `"success"` means success; any other value is treated as failure. |
| other fields | any | No | Preserved verbatim in the engine result for auditing/logging (e.g. `message`, `rows`). |

> ⚠️ **Important**: any extra stdout output that is not part of the JSON object makes parsing fail and the plugin is marked failed. Send debug output to **stderr** — the engine records it in the `.panic.json` diagnostic report.

### 3. Exit Codes & Failure Semantics

| Scenario | Engine behavior |
| :--- | :--- |
| Exit `0`, stdout is valid JSON, `status == "success"` | Success; continue with the next strategy. All success → archive to `success_path` |
| Non-zero exit code | Failure; stderr is captured as the error summary |
| Exit `0` but stdout is not valid JSON | Failure ("plugin did not output valid JSON") |
| Runtime exceeds `timeout` seconds | Subprocess killed; failure |
| Uncaught exception | Process exits non-zero; failure |

On the first failure the engine will:
1. write `panic_{plugin_name}_{timestamp}.json` into `log_dir` (default `logs/`);
2. move the source file into the watch folder's configured `error_path`.

---

## IV. Reference Implementation

### 1. Minimal Plugin

```python
# plugins/my_plugin/main.py
import json
import sys
from pathlib import Path

def main() -> int:
    target = Path(sys.argv[1])

    # Optional: read strategy params
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    # Your processing logic (example: count bytes)
    size = target.stat().st_size

    # Must emit a single JSON object on stdout
    print(json.dumps({
        "status": "success",
        "file": target.name,
        "size_bytes": size,
        "mode": params.get("mode", "default"),
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### 2. Matching Strategy Configuration

```yaml
plugin_directory: "./plugins"

watch_folders:
  - path: "./storage/watch_folder"
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 2
    debounce_seconds: 1.0
    strategies:
      - plugin_name: "my_plugin"     # maps to plugins/my_plugin/main.py
        plugin_version: "1.0.0"
        timeout: 15
        params:
          mode: "strict"
```

### 3. Failure Reporting Example

```python
import json
import sys

def main() -> int:
    try:
        # ... business logic ...
        raise ValueError("malformed input")
    except Exception as exc:
        # Failures must also emit JSON so the engine can record a summary
        print(json.dumps({"status": "failed", "error": str(exc)}))
        print(f"traceback details: {exc}", file=sys.stderr)   # details go to stderr
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## V. Defensive Coding Guidelines

* **Use standard streams only**: do not build custom logging backends inside the plugin. The engine captures `stdout`/`stderr` from the child process and forwards them to the Clerk layer.
* **Idempotency matters**: in high-throughput directory routing a file event may fire more than once. Make processing safe to repeat on the same file.
* **Anchor exceptions**: wrap inner logic in `try/except`. Report failures as a JSON object with a non-success `status` (and a non-zero exit code) so the file is quarantined instead of silently lost.
* **Never mutate the source path**: read from `argv[1]`; the engine owns archiving (moving the file into the success/error zone).

---

## VI. Plugin Self-Test Checklist

Before wiring a plugin into the pipeline, verify it manually in its directory:

```bash
# 1. Invoke it exactly as the engine would
python main.py /absolute/path/to/sample.txt '{"mode": "strict"}'

# 2. Confirm stdout is a single valid JSON object with status == "success"
# 3. Confirm the exit code is 0 (bash: echo $? / PowerShell: $LASTEXITCODE)
```

If the plugin needs its own dependency set, point `python_path` in the strategy at that virtualenv's interpreter. When the path is invalid the engine logs a warning and falls back to the current interpreter.
