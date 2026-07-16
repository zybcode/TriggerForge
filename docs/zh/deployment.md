
---

```markdown
# ⚙️ TriggerForge 生产环境部署与运维手册 (Deployment & Operations Guide)

> **版本**：v1.1-PRO  
> **状态**：已全量验收 (Approved)  
> **定位**：面向 SRE、运维团队与系统管理员的生产级常驻守护进程部署与容器化编排指南。

---

## 一、 使用 Systemd 进行进程守护 (Linux 推荐)

TriggerForge 作为常驻型事件驱动引擎，在 Linux 生产环境中必须通过 Systemd 进程守护管理器进行配置，以保障系统的开机自启与崩溃自愈能力。

### 1. 创建服务配置文件
请在 `/etc/systemd/system/triggerforge.service` 路径下创建服务守护文件，并写入以下配置：

```ini
[Unit]
Description=TriggerForge Event-Driven Directory Orchestration Engine
After=network.target

[Service]
Type=simple
User=triggerforge
Group=triggerforge
WorkingDirectory=/opt/triggerforge

# 核心细节：注入正确的全局 PYTHONPATH 以适配现代 src/ 布局结构
Environment=PYTHONPATH=/opt/triggerforge/src

# 调用虚拟环境中的 Python 解释器直接拉起核心 main 模块
ExecStart=/opt/triggerforge/venv/bin/python -m triggerforge.main --config /opt/triggerforge/config.yaml

# 崩溃自愈与优雅重启策略
Restart=always
RestartSec=5

# 日志直接导向系统的标准日志管理器 journald
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target

```

### 2. 服务控制与管理指令

配置完成后，依次执行以下命令刷新 Systemd 守护进程并启动服务：

```bash
# 重新加载系统守护进程配置
sudo systemctl daemon-reload

# 启用 TriggerForge 开机自启
sudo systemctl enable triggerforge.service

# 启动 TriggerForge 服务
sudo systemctl start triggerforge.service

# 查看服务当前的实时运行状态与诊断简报
sudo systemctl status triggerforge.service

```

---

## 二、 日志流收集与系统观测

由于 TriggerForge 的 `StandardOutput` 和 `StandardError` 已完全托管给 `journald`，运维团队无需在应用层配置繁琐的日志轮转（Logrotate），直接使用 `journalctl` 即可实现零咨询的高效运维观测。

### 1. 实时日志滚动追踪

使用以下命令实时追踪主进程的调度流水、线程池状态以及沙盒进程的输出流：

```bash
journalctl -u triggerforge.service -f -n 100

```

### 2. 诊断与排查故障快照

当第三方插件触发超时熔断或未捕获的段错误（Segfault）时，Clerk 模块会将异常上下文与二进制 Hexdump 快照直接刷入错误流。可以使用以下指令快速定向排查错误日志：

```bash
journalctl -u triggerforge.service --priority=err -n 50

```

---

## 三、 🐳 Docker 容器化编排部署 (v1.2 预告版)

为了满足云原生及 Kubernetes (K8s) 环境下的敏捷部署需求，TriggerForge 提供了超轻量的多阶段构建（Multi-stage Build）方案，并集成了硬性守护进程健康检查探针。

### 1. 生产级 `Dockerfile` 镜像定义

在项目根目录下创建 `Dockerfile`：

```dockerfile
# -----------------------------------------------------------------
# 阶段 1：依赖构建与 Wheel 打包 (使用现代 Hatch 后端)
# -----------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装 Hatch 构建工具
RUN pip install --no-cache-dir hatch

# 复制项目骨架与构建定义
COPY pyproject.toml README.md ./
COPY src/ ./src/

# 构建标准发布 Wheel 包
RUN hatch build -t wheel

# -----------------------------------------------------------------
# 阶段 2：生产常驻运行镜像 (保持绝对纯净与轻量)
# -----------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /opt/triggerforge

# 从构建阶段复制打包好的包并直接进行无缓存本地安装
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl \
    && rm *.whl \
    && mkdir -p /opt/triggerforge/storage

# 显式声明持久化挂载卷，供外部被监听目录接入
VOLUME ["/opt/triggerforge/storage"]

# 注入 Python 运行时标准包查找路径
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages

# 引入终审技术强化的容器健康检查 (Healthcheck) 探针，防范沙盒僵死
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ps aux | grep -v grep | grep triggerforge || exit 1

# 设置容器统一入口点
ENTRYPOINT ["triggerforge"]
CMD ["--config", "/opt/triggerforge/storage/config.yaml"]

```

### 2. 本地镜像构建与试运行指令

```bash
# 编译生成 TriggerForge 容器镜像
docker build -t triggerforge:v1.1-pro .

# 挂载本地存储目录并以后台常驻模式拉起容器
docker run -d \
  --name triggerforge-engine \
  -v /absolute/path/to/local/storage:/opt/triggerforge/storage \
  triggerforge:v1.1-pro

```

---

