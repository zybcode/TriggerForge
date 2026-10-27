# Welcome to TriggerForge

TriggerForge is an event-driven directory orchestration engine: it watches folders, runs a configured plugin pipeline against every file dropped in, and archives or quarantines the result automatically.

## Quick Start

### 1. Install

```bash
python -m pip install -e .
```

### 2. Prepare a configuration

Create `config.yaml` (see the [Configuration Reference](configuration.md) for all fields):

```yaml
plugin_directory: "./plugins"

watch_folders:
  - path: "./storage/watch_folder"        # dropping a file here triggers the pipeline
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 2
    debounce_seconds: 1.0
    strategies:
      - plugin_name: "my_plugin"          # maps to plugins/my_plugin/main.py
        timeout: 15
        params:
          mode: "default"
```

### 3. Validate and start

```bash
# Validate the config only, without starting watchers
python -m triggerforge.cli --config config.yaml --dry-run

# Start the daemon
python -m triggerforge.cli --config config.yaml
```

Once `TriggerForge looper is ready to receive files.` appears, both the watchers and worker threads are up.

### 4. Verify by dropping a file

Copy any file into `storage/watch_folder/`. The engine will:

1. wait for the write to complete (debounce window);
2. run the `strategies` plugins sequentially, each in an isolated subprocess;
3. on success → move the file to `storage/success_folder/`; on failure → move it to `storage/error_folder/` and write a `panic_*.json` diagnostic report under `logs/`.

> If a file is not processed, check: the watched path, whether `plugins/{plugin_name}/main.py` exists, and whether the logs report `Plugin not found` or a JSON parsing failure.

## Further Reading

- [Plugin Development Specification](plugin_dev.md) — entrypoint, parameter injection, output contract
- [Configuration Reference](configuration.md) — every field and runtime behavior
- [Architecture](architecture.md) — layered model and fault isolation
