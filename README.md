<p align="center">
  <img src="docs/assets/logo.png" width="200">
</p>

<p align="center">
  <strong><a href="docs/index.md">📖 查看详细文档 (Full Documentation)</a></strong>
</p>

---

## 🛠️ 简体中文 (Chinese)

# 🛠️ TriggerForge (v1.1-PRO)

> **一个事件驱动的目录编排引擎，具备健壮的子进程沙箱、配置即代码 (Configuration-as-Code) 以及弹性的故障隔离能力。**

TriggerForge 是一个现代化的、生产就绪的守护进程，专为监控文件夹、编排复杂的文件处理流水线以及在高度隔离的子进程中执行自定义插件而设计。

---

## 🚀 快速开始

```bash
# 1. 安装（在项目根目录）
python -m pip install -e .

# 2. 校验配置（不会启动监听）
python -m triggerforge.cli --config config.yaml --dry-run

# 3. 启动守护进程
python -m triggerforge.cli --config config.yaml
```

终端输出 `TriggerForge looper is ready to receive files.` 后，把任意文件投递到 `watch_folders[].path` 指定的目录，引擎就会：

1. 等待文件写入完成（防抖窗口 `debounce_seconds`）；
2. 以独立子进程依次执行 `strategies` 中的插件；
3. 全部成功 → 归档到 `success_path`；任一失败 → 生成 `logs/panic_*.json` 诊断报告并隔离到 `error_path`。

**投递文件没反应？** 按顺序检查：

- 配置里的监控目录路径是否正确（相对路径基于**启动时的工作目录**）；
- 插件入口 `plugins/{plugin_name}/main.py` 是否存在、目录名是否与 `plugin_name` 完全一致；
- 日志中是否出现 `Plugin not found`、`did not output valid JSON` 或超时提示；
- 若插件需要独立依赖环境，策略中的 `python_path` 是否指向真实存在的解释器。

配置字段与插件约定详见 [配置参考](docs/zh/configuration.md) 与 [插件开发规范](docs/zh/plugin_dev.md)。

---

## 🛠️ 开发设置

为了确保开发环境的一致性和测试套件的稳定性，请遵循以下步骤：

### 1. 环境准备
TriggerForge 使用 `src/` 布局来组织源代码。为了确保测试能正确识别模块路径，请始终从项目根目录通过 `python -m` 运行 `pytest`。

```bash
# 1. 创建并激活虚拟环境 (Windows PowerShell)
python.exe -m pip install --upgrade pip
python -m pip install --user pipx
python -m pipx ensurepath
pipx install hatch
hatch env create
hatch shell

```

### 2. 运行测试

我们的测试套件包含一个自动模块导入路径注入机制，以确保其在不同开发环境下运行的一致性。

```bash
# 从项目根目录运行所有测试
python -m pytest -s

```

## 🤝 贡献与合规 (Contributing)

我们非常欢迎社区贡献！为了确保项目的合规性，请遵循以下流程：

* **签署协议**：首次提交 PR 时，请根据 [CLA Assistant](https://cla-assistant.io/) 的提示签署贡献者许可协议 (CLA)。
* **开发规范**：提交代码前，请务必确保所有测试通过 `python -m pytest`。
* **更多指南**：详细的参与流程请查阅 [docs/zh/CONTRIBUTING.md](https://github.com/zybcode/TriggerForge/blob/master/docs/legal/CONTRIBUTING.md)。

## 📜 协议 (License)

本项目采用 [GPLv3 License](https://github.com/zybcode/TriggerForge/blob/master/LICENSE) 进行开源。

---

## 🇬🇧 English Version

# 🛠️ TriggerForge (v1.1-PRO)

> **An event-driven directory orchestration engine with robust subprocess sandboxing, configuration-as-code, and resilient fault isolation.**

TriggerForge is a modern, production-ready daemon designed to watch folders, orchestrate complex file-processing pipelines, and execute custom plugins inside highly isolated subprocesses.

---

## 🚀 Quick Start

```bash
# 1. Install (from the project root)
python -m pip install -e .

# 2. Validate the config only
python -m triggerforge.cli --config config.yaml --dry-run

# 3. Start the daemon
python -m triggerforge.cli --config config.yaml
```

Once `TriggerForge looper is ready to receive files.` is printed, drop any file into the directory configured in `watch_folders[].path`:

1. the engine waits for the write to finish (`debounce_seconds`);
2. each plugin in `strategies` runs sequentially in an isolated subprocess;
3. all succeeded → archived to `success_path`; any failure → a `logs/panic_*.json` diagnostic report is written and the file is quarantined in `error_path`.

**Dropped a file and nothing happened?** Check, in order:

- the watched path in the config (relative paths resolve against the **startup working directory**);
- whether `plugins/{plugin_name}/main.py` exists and its directory name matches `plugin_name` exactly;
- the logs for `Plugin not found`, `did not output valid JSON`, or timeout messages;
- if the plugin needs its own dependencies, whether `python_path` points to an existing interpreter.

See the [Configuration Reference](docs/en/configuration.md) and [Plugin Development Specification](docs/en/plugin_dev.md) for details.

---

## 🛠️ Development Setup

To ensure consistency in your development environment and stability in your test suite, please follow these steps:

### 1. Environment Preparation

TriggerForge uses a `src/` layout to keep the source code organized. To ensure that tests can correctly identify module paths, please always run `pytest` via `python -m` from the project root directory.

```bash
# 1. Create and activate a virtual environment (Windows PowerShell)
python.exe -m pip install --upgrade pip
python -m pip install --user pipx
python -m pipx ensurepath
pipx install hatch
hatch env create
hatch shell

```

### 2. Running Tests

We prioritize both functionality and test stability. Our test suite includes an automatic module import path injection mechanism to ensure it runs consistently across different development environments.

```bash
# Run all tests from the project root directory
python -m pytest -s

```

## 🤝 Contributing

We welcome contributions! To ensure project compliance, please follow these steps:

* **Sign CLA**: Upon your first pull request, please sign the Contributor License Agreement (CLA) as prompted by the [CLA Assistant](https://cla-assistant.io/).
* **Coding Standards**: Ensure all tests pass via `python -m pytest` before submitting a PR.
* **Detailed Guide**: See [docs/en/CONTRIBUTING.md](https://github.com/zybcode/TriggerForge/blob/master/docs/legal/CONTRIBUTING.md) for full details.

## 📜 License 

This project is licensed under the [GPLv3 License](https://github.com/zybcode/TriggerForge/blob/master/LICENSE).

```
