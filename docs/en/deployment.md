
---

```markdown
# ⚙️ TriggerForge Production Deployment & Operations Guide

> **Version**: v1.1-PRO  
> **Status**: Approved  
> **Scope**: Production daemon deployment and containerized orchestration blueprint for SREs, DevOps engineers, and system administrators.

---

## I. Daemon Management via Systemd (Recommended for Linux)

As a resident event-driven engine, TriggerForge must be managed by the Systemd service manager in production environments to guarantee autostart on boot and crash self-healing capabilities.

### 1. Creating the Service Configuration
Create a service definition file at `/etc/systemd/system/triggerforge.service` and populate it with the following configuration:

```ini
[Unit]
Description=TriggerForge Event-Driven Directory Orchestration Engine
After=network.target

[Service]
Type=simple
User=triggerforge
Group=triggerforge
WorkingDirectory=/opt/triggerforge

# Critical Detail: Inject the correct global PYTHONPATH to match the modern src/ layout
Environment=PYTHONPATH=/opt/triggerforge/src

# Invoke the Python interpreter inside the Venv to boot up the core main module directly
ExecStart=/opt/triggerforge/venv/bin/python -m triggerforge.main --config /opt/triggerforge/config.yaml

# Crash Recovery and Graceful Restart Policies
Restart=always
RestartSec=5

# Route stdout and stderr directly to the system journal manager
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

```

### 2. Service Control and Administration Commands

Once the configuration is in place, execute the following commands in sequence to reload the Systemd manager daemon and activate the engine:

```bash
# Reload the system daemon configuration profiles
sudo systemctl daemon-reload

# Enable TriggerForge to start automatically on system boot
sudo systemctl enable triggerforge.service

# Launch the TriggerForge service immediately
sudo systemctl start triggerforge.service

# Inspect the real-time runtime status and diagnostic brief of the daemon
sudo systemctl status triggerforge.service

```

---

## II. Log Aggregation and System Observability

Because TriggerForge delegates its `StandardOutput` and `StandardError` completely to `journald`, operations teams do not need to configure cumbersome log rotation layers (`logrotate`) at the application level. You can utilize native `journalctl` commands for efficient, zero-consultation troubleshooting.

### 1. Real-Time Log Tailing

Run the following command to track the master dispatching sequence, thread pool allocations, and subprocess sandbox stdout in real time:

```bash
journalctl -u triggerforge.service -f -n 100

```

### 2. Failure Snapshot Diagnostics

When a third-party plugin hits a timeout wall or encounters an unhandled segmentation fault (Segfault), the Clerk module flushes the failure context alongside a binary Hexdump snapshot directly into the error stream. Use the following filter to quickly pinpoint failures:

```bash
journalctl -u triggerforge.service --priority=err -n 50

```

---

## III. 🐳 Cloud-Native Dockerization and Orchestration (v1.2 Preview)

To meet agile deployment requirements within cloud-native environments and Kubernetes (K8s) clusters, TriggerForge offers an ultra-lightweight multi-stage build setup integrated with an explicit health checking mechanism.

### 1. Production-Grade `Dockerfile` Specification

Create a `Dockerfile` in the root directory of the project:

```dockerfile
# -----------------------------------------------------------------
# Stage 1: Dependency Assembly and Wheel Packaging (Hatch Backend)
# -----------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install the modern Hatch packaging frontend
RUN pip install --no-cache-dir hatch

# Copy project declarations and manifest definitions
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Compile the project into standard distribution wheels
RUN hatch build -t wheel

# -----------------------------------------------------------------
# Stage 2: Minimal Production Runtime (Kept ultra-pure and lean)
# -----------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /opt/triggerforge

# Copy compiled wheels from the build stage and execute zero-cache local installations
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl \
    && rm *.whl \
    && mkdir -p /opt/triggerforge/storage

# Declare a standard persistent volume mount for target directories
VOLUME ["/opt/triggerforge/storage"]

# Inject standard Python package lookup boundaries
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages

# Implement the technical health check probe to prevent silent sandbox deadlocks
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ps aux | grep -v grep | grep triggerforge || exit 1

# Setup a unified system entrypoint
ENTRYPOINT ["triggerforge"]
CMD ["--config", "/opt/triggerforge/storage/config.yaml"]

```

### 2. Local Image Compilation and Run Sequences

```bash
# Build the production-ready TriggerForge container image
docker build -t triggerforge:v1.1-pro .

# Mount local storage paths and spin up the container in daemonized detached mode
docker run -d \
  --name triggerforge-engine \
  -v /absolute/path/to/local/storage:/opt/triggerforge/storage \
  triggerforge:v1.1-pro

```

---

