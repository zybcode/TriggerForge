# 欢迎来到 TriggerForge 文档

---

## 🚀 项目简介 / Project Overview

**[简体中文]**  
TriggerForge 是一个高性能、模块化的自动化工作流引擎，专注于文件监控、任务触发及工程级插件管理。它通过子进程沙箱和防御性接口设计，确保了在复杂研发环境下的稳定运行与数据安全[cite: 10]。

**[English]**  
TriggerForge is a high-performance, modular automation workflow engine designed for file monitoring, event triggering, and enterprise-grade plugin management. Through subprocess sandboxing and defensive interface design, it ensures stable execution and data integrity in complex R&D environments[cite: 10].

---

## 🛠 快速开始 / Quick Start

如果您是开发者，请查看以下指南：

| 语言版本 | 访问链接 |
| :--- | :--- |
| **简体中文** | [查看中文插件开发规范](zh/plugin_dev.md) |
| **English** | [View English Plugin Dev Spec](en/plugin_dev.md) |

---

## 💡 核心特性 / Key Features

*   **🛡️ 零信任沙箱**：通过独立的子进程执行插件，隔离致命运行时错误[cite: 10]。
*   **⏱️ 防御性设计**：内置执行时间围栏，强制终止挂起的异常任务[cite: 10]。
*   **🐍 动态 Python 环境**：支持针对不同插件指定不同的 Python 运行时环境[cite: 10]。
*   **📦 模块化扩展**：基于 `BasePlugin` 抽象类，快速构建自定义业务逻辑[cite: 10]。

---

> **Note**: 本文档由 MkDocs Material 驱动，支持多语言自动切换。如需贡献翻译或功能改进，请参考 [GitHub 仓库](https://github.com/zybcode/triggerforge)。