
---

# 📐 TriggerForge Architecture Specification

> **Version**: v1.1-PRO
> **Status**: Approved
> **Scope**: System core blueprint and isolation model specification, serving as the definitive guide for core engineering and development.

---

## I. System Architecture Overview

TriggerForge implements a strictly decoupled **four-layer isolation architecture model**. This design guarantees absolute stability and self-healing capabilities for the core engine, even under heavy concurrent file events, untrusted third-party plugin crashes, or severe memory leaks.

```plaintext
┌─────────────────────────────────────────────────────────────────┐
│                 Looper (Main Loop / Orchestrator)               │
│   load config → per folder: Watcher + Queue + Worker Threads     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Sentry (Sentinel Watcher Layer)                │
│   Watchdog events → temp filter → debounce Timer → enqueue       │
└──────────────────────────────┬──────────────────────────────────┘
                               │  EventBufferQueue (thread-safe)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ForgeCore (Execution Engine Layer)              │
│   workers consume queue → sequential strategies → subprocess     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Clerk (Output Manager Layer)                  │
│   success → success_path / failure → error_path + .panic.json    │
└─────────────────────────────────────────────────────────────────┘

```

---

## II. Core Layered Design

### 1. Looper (Main Loop Layer)

* **Responsibilities**: Serves as the outermost long-running daemon process of the system. It handles the entire lifecycle of the TriggerForge engine, including initialization, configuration loading, graceful shutdown sequencing, and global OS signal handling.
* **Orchestration**: For every watched directory it instantiates a `SentryWatcher` plus an `EventBufferQueue`, then spawns `concurrency` worker threads that consume the queue and drive the full "run plugins → archive" pipeline.
* **Self-Healing Mechanics**: Ensures zero configuration loss during catastrophic unexpected global errors, maintaining the capacity to dynamically reboot downstream layers.

### 2. Sentry (Sentinel Watcher Layer)

* **Responsibilities**: Filesystem event ingestion, static filtering, and write debouncing.
* **Technical Implementation**:
* **Watchdog Poller**: Listens for real-time filesystem events (`on_created` / `on_modified`) on the configured directories.
* **Static Filtering**: Drops temp/editor artifacts (`.tmp`, `.swp`, trailing `~`, dotfiles) before they reach the pipeline.
* **Write Debouncing**: A per-path `Timer` is cancelled and rescheduled for repeated events inside the `debounce_seconds` window, guaranteeing downstream plugins only see fully written files.
* **Buffered Handoff**: Once the debounce window expires, the path is enqueued into the thread-safe `EventBufferQueue`, decoupling ingestion from execution and absorbing bursts.



### 3. ForgeCore (Execution Engine Layer)

* **Responsibilities**: Host environment and execution pipeline coordinator for plugins.
* **Execution Flow**: worker threads pull a path from `EventBufferQueue` and run `strategies` **sequentially**; the first failure short-circuits the remaining strategies.
* **Subprocess Sandbox Isolation**:
* **Hard Process Isolation**: ForgeCore strictly prohibits executing third-party plugin code within the main process or worker threads. For every strategy it spawns a **completely independent subprocess** via `PluginRunner`, invoked as `main.py <file_path> <json_params>`.
* **Fault and Crash Isolation**: Plugin child processes possess their own isolated memory space and are bounded by hard execution timeout fences. If a plugin suffers a memory leak, enters an infinite loop, or encounters a sudden segmentation fault (Segfault), only that specific subprocess is impacted. ForgeCore safely destroys the corrupted child process, reclaims system resources, and leaves the core engine 100% unaffected.
* **Multi-Version Virtual Environment Support**: Supports explicitly defining a custom `python_path` in the configuration. This allows child processes to dynamically invoke separate, fully-isolated Python virtual environments (Venvs), seamlessly solving dependency conflicts between legacy and modern plugins. Invalid paths fall back to the current interpreter with a warning.



### 4. Clerk (Output Manager Layer)

* **Responsibilities**: Manages the post-execution cleanup, file lifecycle tracking, and state materialization.
* **Asset & Diagnostics Routing**:
* **Pipeline Archiving**: Automatically moves processed files to either `success_path` (Success Archive) or `error_path` (Error Archive) based on the exact status returned by the plugin subprocess, with directory self-healing and timestamp-based collision avoidance.
* **Panic Dumps**: When a plugin fails, times out, or crashes, Clerk writes a structured `panic_{plugin}_{timestamp}.json` containing target file metadata, the failing plugin and strategy params, environment context, and the captured `stdout` / `stderr` streams — providing immediate, zero-consultation troubleshooting evidence for SRE teams.



---

## III. Defensive Engineering Standards

### 1. Architecture as Code

Static documentation inevitably degrades and drifts as code iterates. Manual modifications to configuration documentation are strictly forbidden in TriggerForge. All system metadata (such as `watch_folders`, `concurrency`, `strategies`, etc.) must be declared programmatically via **Python Type Hints + Pydantic Schemas** inside `src/triggerforge/core/schema.py`. Running `scripts/generate_docs.py` automatically extracts these fields, ensuring `docs/configuration.md` is always up to date.

### 2. Modern Python Source Layout (`src/` Layout)

The project abandons traditional nested module architectures in favor of the clean, modern `src/` layout backed by the Hatch build system. The core source code resides under `src/triggerforge/`. This eliminates the risk of implicit local path contamination within `PYTHONPATH` during testing and development, guaranteeing a pure and predictable build distribution when packaged into a Wheel file.

### 3. Deterministic CI/CD and Flaky Test Elimination

To guarantee that CI/CD pipelines remain 100% stable in containerized or virtualized environments (such as GitHub Actions), integration tests inside the `tests/` directory are completely decoupled from OS-level disk I/O hooks. The test suite leverages an **in-memory mock queue filesystem** declared via `tests/conftest.py`. This mock event system fires deterministic event streams in memory, completely eliminating intermittent test suite timeouts caused by OS file event processing latencies.

---

> 