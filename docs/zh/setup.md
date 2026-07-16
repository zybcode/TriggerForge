
---

# 🚀 TriggerForge 环境搭建与开发指南 (Development Setup Guide)

> **版本**：v1.1-PRO
> **状态**：已全量验收 (Approved)
> **定位**：面向内部开发人员与开源贡献者的本地开发环境初始化、依赖管理与工程就绪指南。

---

## 一、 开发环境前置要求

在开始搭建环境之前，请确保您的开发机已安装并配置好以下基础设施：

* **Python 运行时**：建议使用 **Python 3.10、3.11 或 3.12** 运行环境。
* **构建系统（Hatch）**：TriggerForge 摒弃了传统的 `setup.py`，全面拥抱 PEP 621 标准，使用 **Hatch** 作为现代打包与环境管理后端。
* **操作系统**：支持 Linux (推荐用于生产部署)、macOS 以及 Windows。

---

## 二、 快速初始化本地开发环境

我们已经将所有的依赖、构建元数据以及虚拟环境管理配置写入了根目录下的 `pyproject.toml`。您只需按照以下三步即可一键初始化完全隔离的开发环境：

### 1. 克隆项目并进入根目录

```bash
git clone https://github.com/zybcode/TriggerForge.git
cd TriggerForge

```

### 2. 安装 Hatch（如果尚未安装）

Hatch 既是构建工具，也是极佳的虚拟环境管理器。您可以通过 `pip` 或系统包管理器直接全局安装它：

```bash
pip install --user hatch

```

### 3. 一键同步环境并安装依赖

运行以下命令，Hatch 会自动为您创建独立的虚拟环境，并以可编辑模式（Editable Mode）安装项目及其所有的开发与测试依赖：

```bash
# 激活默认的开发环境并安装所有依赖
hatch env create

```

---

## 三、 本地日常开发核心指令

使用 Hatch 管理环境时，您无需手动运行 `source venv/bin/activate`。Hatch 提供了优雅的命令托管机制：

### 1. 运行测试套件（消除 Flaky Tests 防线）

TriggerForge 的测试套件通过内存模拟队列绕过了不稳定的磁盘 I/O。在本地运行测试极为迅速且稳定：

```bash
# 在独立虚拟环境中自动运行 pytest
hatch run cov

```

*(注：该指令在幕后会执行 `pytest --cov=triggerforge tests/` 并自动输出覆盖率报告)*

### 2. 在虚拟环境中执行任意命令

如果您需要直接运行本地的代码脚本或排查工具，可以使用 `hatch run`：

```bash
# 检查当前虚拟环境中的 Python 版本
hatch run python --version

# 验证您的配置文件是否合规（利用 Pydantic Schema 校验）
hatch run triggerforge --check-config config.yaml

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
├── README.md                # 开源门户与双重许可商业声明
├── LICENSE                  # 开源 GPL v3 授权文件
├── src/                     # 纯净的源码存放目录
│   └── triggerforge/        # 核心包根目录
│       ├── main.py          # 引擎守护进程启动入口
│       ├── core/            # 核心引擎层（Looper, Sentry, ForgeCore, Clerk）
│       │   └── schema.py    # Pydantic 核心配置 Schema（架构即代码的源头）
│       └── plugins/         # 插件机制存放路径
│           └── base.py      # 所有插件必须继承的 BasePlugin 抽象基类
├── tests/                   # 100% 稳定的测试目录
│   ├── conftest.py          # 内存队列 Mock 桩配置
│   └── test_core.py         # 核心隔离机制与调度功能测试
└── scripts/
    └── generate_docs.py     # 自动化文档抽取脚本

```

---

> ⚖️ **注意**：为了防范沙盒子进程依赖冲突，严禁直接使用全局 `pip install` 往系统环境里塞包。所有的依赖更新必须在 `pyproject.toml` 的 `[project.dependencies]` 或 `[tool.hatch.envs.default]` 块中声明，然后运行 `hatch env prune && hatch env create` 进行干净的重新同步。