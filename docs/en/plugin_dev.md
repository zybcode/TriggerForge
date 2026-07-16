
# 🇺🇸 英文版：docs/plugin_dev.md

```markdown
# 🔌 TriggerForge Plugin Development Specification (Plugin Development Specification)

> **Version**: v1.1-PRO  
> **Status**: Approved  
> **Scope**: Definitive lifecycle interface guide for internal developers and open-source community contributors building modular workflows.

---

## I. Architectural Philosophy & Sandbox Constraints

To maintain absolute core resilience, TriggerForge enforces a strict **Zero-Trust Plugin Model**. Every plugin registered within the execution pipeline is subjected to the following runtime guardrails:

1. **Subprocess Sandboxing**: Plugins are never executed inside the primary monitoring process. They are invoked as independent subprocesses, ensuring memory limits and fatal runtimes (e.g., Segfaults) are safely contained.
2. **Defensive Timeouts**: Every plugin lifecycle is bound by a hard execution fence. If a plugin locks or blocks beyond its configured threshold, it will be forcefully terminated.
3. **Dynamic Virtual Environments**: Plugins can explicitly target specific Python runtimes via `python_path`. This allows legacy scripts requiring older package versions to coexist seamlessly alongside modern pipelines.

---

## II. The Base Interface (`BasePlugin`)

All TriggerForge plugins must be written in Python and must inherit from the abstract base class `BasePlugin`. The engine interacts with your custom logic exclusively through this abstract contract.

### 1. The Interface Definition
Your plugin module must expose a concrete class implementing the following structure:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Path

class BasePlugin(ABC):
    """
    Abstract Base Class defining the lifecycle contract for TriggerForge plugins.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the unique identifier string for the plugin.
        Matches the 'plugin_name' specified in config.yaml.
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Returns the semantic version string of the plugin (e.g., '1.0.0').
        """
        pass

    @abstractmethod
    def execute(self, target_file: Path, params: Dict[str, Any]) -> bool:
        """
        Core execution pipeline block invoked by the ForgeCore subprocess manager.
        
        Args:
            target_file (Path): The absolute path to the file that triggered the event.
            params (Dict[str, Any]): Dynamic custom parameters passed down from the YAML config.
            
        Returns:
            bool: True if the processing succeeds, False if an expected failure occurs.
        """
        pass

```

---

## III. Step-by-Step Plugin Implementation

To write and register a new plugin named `compress_plugin`, follow this strict structural layout:

### 1. Directory Blueprint

Create your plugin module under the standard layout `src/triggerforge/plugins/`:

```plaintext
src/triggerforge/plugins/
├── __init__.py
└── compress_plugin/
    ├── __init__.py
    └── main.py          # Concrete implementation resides here

```

### 2. Writing the Concrete Logic (`main.py`)

Implement the interface, handling all long-running behaviors gracefully:

```python
import os
import tarfile
from pathlib import Path
from typing import Dict, Any
from triggerforge.plugins.base import BasePlugin

class CompressPlugin(BasePlugin):
    
    @property
    def name(self) -> str:
        return "compress_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def execute(self, target_file: Path, params: Dict[str, Any]) -> bool:
        """
        Compresses the incoming file into a standard tar.gz payload.
        """
        # 1. Extract dynamic configuration parameters safely
        compression_level = params.get("level", "high")
        
        print(f"[Info] Initializing compression on {target_file.name} (Level: {compression_level})")
        
        if not target_file.exists():
            print(f"[Error] Target file missing: {target_file}")
            return False
            
        try:
            # 2. Execute business processing logic
            output_archive = target_file.with_suffix(".tar.gz")
            with tarfile.open(output_archive, "w:gz") as tar:
                tar.add(target_file, arcname=target_file.name)
                
            print(f"[Success] Successfully archived payload to {output_archive.name}")
            return True
            
        except Exception as e:
            # 3. Standard error output streams will be automatically grabbed by the Clerk layer
            print(f"[Exception] Compression failure sequence encountered: {str(e)}")
            return False

```

---

## IV. Defensive Coding Guidelines for Plugin Developers

To ensure your code integrates flawlessly with the TriggerForge execution matrix, abide by these standard practices:

* **Leverage Standard Outputs**: Do not implement specialized custom file logging backends inside your plugin. Use standard `print()` statements or direct `sys.stdout`/`sys.stderr` streams. TriggerForge captures these streams from the child process and passes them to the **Clerk layer** to populate the operational `journald` logs.
* **Idempotency is Non-Negotiable**: In high-throughput directory routing, a file event might fire multiple times under specialized edge cases. Ensure your `execute()` logic is safe to run multiple times against the same file without corrupting states or duplicating database entries.
* **Graceful Exception Anchoring**: Always wrap your inner logic loops inside an exhaustive `try/except` block. Unhandled critical failures (e.g., unexpected library exceptions) should be caught, logged to standard error, and resolved by returning `False` so the Clerk can seamlessly move the target file into the designated `error_path` quarantine.

```
