
```markdown
# TriggerForge v1.2 Migration Guide

> **Version**: v1.2-Final (Approved)
> **Status**: Active
> **Path**: docs/en/migration_v1.2.md

## 1. Overview
This guide assists in migrating configurations to the v1.2 standard. Version 1.2 introduces stricter timeout constraints and automated configuration auditing.

## 2. Deprecation & Migration Mapping Table

| Deprecated Key | Recommended Replacement | Disposal Plan | Planned Removal |
| :--- | :--- | :--- | :--- |
| `timeout` (Global) | `max_execution_timeout` | Rename (Global hard limit) | v1.4 |
| `strategies[].timeout` | `strategies[].strategy.timeout` | Move to strategy object | v1.4 |
| `debounce_seconds` | (Removed) | Refactored in v1.1 | v1.3 |
| `recursive` | (Removed) | Enabled by default | v1.3 |

## 3. Core Migration Steps

### Step 1: Update Global Configuration
Rename legacy global `timeout` to `max_execution_timeout`.

### Step 2: Adapt Plugin Strategies
Update individual plugin strategies to the new nested schema.

**v1.2 Standard Example:**
```yaml
watch_folders:
  - path: "./data"
    strategies:
      - plugin_name: "OCRProcessor"
        strategy:
          timeout: 60
          priority: "standard"
          allow_override_timeout: false

```

### Step 3: Run Configuration Audit

Run the following to verify compliance:

```bash
hatch run python scripts/config_manager.py --check

```

*If the return code is 0, the migration is successful.*

## 4. FAQ

**Q: How do I verify migration success?**
A: Run the `--check` command; a return code of 0 confirms compliance. Results are logged in the audit trail.

**Q: Can I mix legacy and new configurations?**
A: Backward compatibility is supported with `DeprecationWarning` logs. Complete full migration before v1.4 to avoid potential startup failures.

**Q: Why was the priority field introduced?**
A: To implement resource anti-lockout mechanisms, ensuring high-priority core tasks remain stable.

---

*Technical support and development details are available in [Development Plan](https://www.google.com/search?q=../en/dev_plan_v1.2.md).*

```

```