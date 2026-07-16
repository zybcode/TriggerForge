

---

# 📜 TriggerForge Project Charter

> **Version**: v1.1-PRO
> **Status**: Approved
> **Scope**: Defines the core business pain points, system boundaries, and technical vision of TriggerForge, serving as the foundational governance document for project initialization.

---

## I. Core Pain Points & Project Background

In modern enterprise automation pipelines and data processing workflows, triggering downstream business logic (such as file decompression, format conversion, and data parsing) by watching filesystem directory events is a ubiquitous requirement. However, conventional scripts and lightweight utilities frequently suffer from three fatal pain points in production environments:

1. **"Zombie Documentation" and Configuration Drift**: Traditional system configurations are completely disconnected from developer documentation. As the project iterates rapidly, static markdown files quickly become outdated, eventually turning into misleading trash that confuses onboarding engineers.
2. **"Single Point of Failure" in Plugin Environments**: Third-party plugins or legacy scripts are often poorly written. When a plugin encounters a memory leak, enters an infinite loop, or triggers a sudden segmentation fault (Segfault), it typically crashes the entire main monitoring process due to a complete lack of fault isolation boundaries.
3. **Flaky Tests Polluting CI/CD Pipelines**: Because underlying libraries like `Watchdog` rely heavily on native OS filesystem hooks, they often exhibit extreme instability—manifested as intermittent test timeouts—in containerized or virtualized CI/CD environments (such as GitHub Actions) due to disk I/O latencies. This consumes massive maintenance effort from the engineering team.

TriggerForge is engineered to systematically eliminate these engineering dysfunctions. It rejects the "good enough to run" mindset of temporary scripts, establishing itself as a **full-lifecycle engineering product featuring enterprise-grade process isolation, automated document generation, and production-ready deployment solutions**.

---

## II. Technical Vision & Strategic Goals

The core vision of TriggerForge is to build a modern, event-driven directory orchestration engine that is **resilient under pressure, completely fault-isolated, self-documenting, highly collaborative, and open-source compliant**.

### 1. Core Engineering Targets

* **Architecture as Code**: Leverage the Python type system and Pydantic schemas as the definitive source of truth for "living documentation." Manual editing of configuration specifications is strictly prohibited; all field metadata is auto-generated from the system schema to eradicate document drift.
* **Hardcore Subprocess Sandbox Isolation**: Spawn an independent child process for every plugin execution, bounded by strict execution timeout fences and resource perimeters. This guarantees that runtime failures are perfectly locked inside the sub-environment.
* **Cloud-Native & CI/CD Determinism**: Introduce an in-memory mock queue filesystem to bypass native disk I/O within containerized environments, ensuring that testing pipelines pass with 100% stability and consistency.

---

## III. System Boundaries & Delivery Scope (v1.1-PRO)

### 1. In-Scope Deliverables

* **Modern Source Layout**: Implements a clean `src/` layout matching the modern Python community's best practices, managed via a standard `pyproject.toml` configuration utilizing the Hatch build backend and PEP 621 specifications.
* **Non-Blocking Concurrent Event Dispatching**: A decoupled workflow where the main loop (`Looper`) and the sentinel watcher (`Sentry`) collaborate with a managed thread pool (`ThreadPoolExecutor`) to dispatch filesystem events concurrently, ensuring the main ingestion stream is never blocked.
* **Dynamic Multi-Venv Environments**: Supports explicitly specifying a custom `python_path` inside the configuration, allowing child processes to dynamically invoke separate, fully-isolated virtual environments to seamlessly execute legacy plugins.
* **Production-Grade Operations Lifecycle**: Provides an out-of-the-box Linux Systemd configuration for process守护 (daemonization), paired with `journald`-based log stream observability and automated binary hexdump snapshot generation for post-mortem diagnostics.

### 2. Out-of-Scope Boundaries

* **Network API Endpoints**: The v1.1-PRO release is strictly scoped as a resident local background daemon. It does not adapt to, nor does it provide, any HTTP/RESTful network interfaces, preserving complete architectural simplicity and core focus.

---

## IV. Commercial & Open-Source Roadmap

To balance the ecosystem benefits of open-source community collaboration with the commercial value of enterprise close-loop deployments, TriggerForge adopts a **Dual-Licensing Model**:

1. **Open-Source Version (GNU GPL v3)**: Targeted at personal use, academic research, and open-source community development. The source code is entirely transparent and protected by the copyleft nature of the GPL v3 license—any derivative works or integrated products distributed externally must also publish their full source code.
2. **Commercial License**: Targeted at enterprise customers wishing to integrate TriggerForge into proprietary commercial software or SaaS platforms **without** being bound by GPL copyleft restrictions. This tier provides closed-source integration rights, custom plugin engineering, and SRE-grade enterprise support agreements.
3. **Contributor Compliance**: Every external developer submitting a Pull Request to this repository must sign a Contributor License Agreement (CLA) to protect the integrity of the project's copyright ownership and ensure the legal distribution of the commercial edition.

---

