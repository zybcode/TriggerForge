
---

# 🚀 TriggerForge 环境搭建与开发指南 (Development Setup Guide)

> **版本**：v1.1-PRO
> **状态**：已全量验收 (Approved)
> **定位**：面向内部开发人员与开源贡献者的本地开发环境初始化、依赖管理与工程就绪指南。

---

## 一、 开发环境前置要求

在开始搭建环境之前，请确保您的开发机已安装并配置好以下基础设施：

* **Python 运行时**：需要 **Python 3.11 及以上**（与 `pyproject.toml` 中 `requires-python = ">=3.11"` 保持一致）。
* **构建系统（Hatch，可选）**：TriggerForge 摒弃了传统的 `setup.py`，全面拥抱 PEP 621 标准，使用 **Hatch** 作为现代打包与环境管理后端。不使用 Hatch 时，直接用 `pip` 亦可完成全部开发工作（见下文方案 B）。
* **操作系统**：支持 Linux (推荐用于生产部署)、macOS 以及 Windows。

---

## 二、 快速初始化本地开发环境

以下两种方案任选其一。**无论哪种方案，都必须先把依赖装齐再跑测试**，否则 pytest 会在收集阶段报一批 `ModuleNotFoundError`（而不是用例失败）。

### 方案 A：Hatch 托管环境（推荐）

我们已经将所有的依赖、构建元数据以及虚拟环境管理配置写入了根目录下的 `pyproject.toml`。

#### 1. 克隆项目并进入根目录

```bash
git clone https://github.com/zybcode/TriggerForge.git
cd TriggerForge

```

#### 2. 安装 Hatch（如果尚未安装）

Hatch 既是构建工具，也是极佳的虚拟环境管理器。您可以通过 `pip` 或系统包管理器直接全局安装它：

```bash
pip install --user hatch

```

#### 3. 一键同步环境并安装依赖

运行以下命令，Hatch 会自动为您创建独立的虚拟环境，并以可编辑模式（Editable Mode）安装项目及其所有的开发与测试依赖：

```bash
# 激活默认的开发环境并安装所有依赖
hatch env create

```

### 方案 B：极简 pip 环境

不需要 Hatch，直接用 `pip` 把项目和测试工具装进当前解释器（全局或虚拟环境均可）：

```bash
# 1. 以可编辑模式安装项目本体（自动带上 watchdog / pydantic / pyyaml 运行依赖）
python -m pip install -e .

# 2. 安装测试工具
python -m pip install pytest pytest-cov

# 3. 从项目根目录运行测试
python -m pytest
```

> 💡 常见坑：如果 `pytest` 命令挂载的解释器与安装依赖的解释器不是同一个（例如 `pytest.exe` 在 Python 3.12 的 Scripts 下，而依赖装到了别的 Python），就会出现"测试收集阶段大面积 ModuleNotFoundError"。可用 `pytest --version`、`where pytest` / `where python` 核对两边是否为同一环境。

---

## 三、 本地日常开发核心指令

### 1. 运行测试套件

```bash
# 方案 A（Hatch）：在独立虚拟环境中自动运行 pytest 并输出覆盖率
hatch run cov

# 方案 B（pip）：从项目根目录直接运行
python -m pytest

# 仅运行单元测试 / 集成测试
python -m pytest tests/unit
python -m pytest tests/integration
```

当前测试套件共 47 个用例（38 个单元测试 + 9 个集成测试），全绿约需 10~25 秒。

### 2. 在虚拟环境中执行任意命令

如果您需要直接运行本地的代码脚本或排查工具，可以使用 `hatch run`：

```bash
# 检查当前虚拟环境中的 Python 版本
hatch run python --version

# 验证您的配置文件是否合规（利用 Pydantic Schema 校验，不启动监听）
hatch run triggerforge --config config.yaml --dry-run

```

### 3. 手动激活环境 Shell

如果您更喜欢保持激活虚拟环境的状态进行高频调试，可以使用以下命令进入虚拟环境的 Shell：

```bash
hatch shell

```

进入后，您可以直接像平常一样运行 `pytest`、`python` 或 `triggerforge`，调试完毕后输入 `exit` 即可安全退出。

---

## 四、 项目骨架与关键路径说明

在开发和提交代码前，请务必熟悉以下标准的 `src/` 布局结构：

```plaintext
TriggerForge/
├── pyproject.toml           # 遵循 PEP 621 规范的统一项目配置文件
├── config.yaml              # 运行配置（监控目录与插件策略）
├── config.sample.yaml       # 生产级配置示例
├── mkdocs.yml               # 文档站点导航配置
├── README.md                # 开源门户与快速开始
├── LICENSE                  # 开源 GPLv3 授权文件
├── docs/                    # 中英双语文档站（mkdocs-material）
├── src/                     # 纯净的源码存放目录
│   └── triggerforge/
│       ├── main.py          # 引擎守护进程启动入口
│       ├── cli.py           # 命令行入口（--config / --dry-run / --version）
│       ├── core/
│       │   ├── looper.py    # 编排层：队列 + 工作线程 + 插件流水线接线
│       │   ├── schema.py    # Pydantic 核心配置 Schema（配置的唯一定义处）
│       │   ├── runner/      # ForgeCore：PluginRunner 子进程沙箱
│       │   ├── sentry/      # Sentry：watcher / queue / filter
│       │   └── clerk/       # Clerk：archiver（归档）/ journal（panic 报告）
│       └── plugins/
│           └── base.py      # 可选的插件抽象基类（进程契约见 plugin_dev.md）
└── tests/
    ├── conftest.py          # 共享 fixture 与 src 路径注入
    ├── unit/                # 38 个单元测试
    └── integration/         # 9 个集成测试（含真实 watchdog 端到端）

```

---

> ⚖️ **注意**：为防范沙盒子进程依赖冲突，请始终通过 `pyproject.toml` 的 `[project.dependencies]` 或 `[tool.hatch.envs.default]` 声明依赖，再执行同步。日常本地开发使用上文方案 B 的 `pip install -e .` 也是受支持的方式；关键是**保证运行 pytest 的解释器与安装依赖的解释器一致**。