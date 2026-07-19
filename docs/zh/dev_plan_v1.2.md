以下是经过架构评审专家审核通过的 **TriggerForge v1.2 全量开发规划文档**。

---

# TriggerForge v1.2 开发规划文档

> **版本**：v1.2-Final-Merged
> **状态**：已锁定（归档版）
> **目录**：docs/zh/dev_plan_v1.2.md

## 1. 概述

本版本致力于实现 TriggerForge 的运维自动化闭环，核心目标是提升高负载下的稳定性与防锁死能力，正式引入工程化路径管理机制及新手引导工具，为商业化基座提供支撑。

## 2. 核心任务清单

| 序号 | 任务模块 | 关键开发内容 |
| --- | --- | --- |
| 1 | **Schema 与目录扩展** | 完善 `priority` 校验、`working_dir` 自定义支持及惰性创建逻辑

 |
| 2 | **配置审计引擎** | 开发 `ForgeConfigManager`，支持 `--check` 及结构化 JSON 审计报告

 |
| 3 | **工程内置引导** | 实现配置模板生成工具 (`init`)，内嵌路径推荐与交互式逻辑

 |
| 4 | **热加载机制** | 实现 `SIGHUP` 信号监听，支持生命周期隔离的原子化配置切换

 |
| 5 | **集成与测试** | 覆盖路径映射、权限校验、静态合规性及自动化回归测试

 |

## 3. 架构约束与技术实施

### 3.1 核心约束 (`src/triggerforge/core/schema.py`)

* **目录自定义 (`working_dir`)**：


* **定义**：支持插件独立工作目录。相对路径基准为配置文件目录 `${config_dir}`；绝对路径原样解析。


* **权限与创建**：启动预检校验父目录是否可写；若目标路径缺失，则触发“惰性创建”（权限 `0750`，递归创建父级）。


* **默认值与联动**：未显式配置时，默认指向约定目录。此配置独立于 `priority`，无联动约束；多插件共享目录风险由用户自担。




* **双重约束**: `allow_override_timeout = true` 强制要求 `priority = "high"`。



### 3.2 配置审计接口 (`src/triggerforge/utils/config_manager.py`)

* **静态检查增强**：`--check` 模式将校验路径合法性（非法字符检测、路径长度限制）。


* **JSON 审计结构**：支持 `--format json`，输出规范如下：


```json
{
  "status": "pass",
  "exit_code": 0,
  "checks": {"total": 10, "passed": 10, "failed": 0, "warnings": 0},
  "errors": [],
  "warnings": [{"field": "watch_folders[0].path", "message": "建议使用 POSIX 风格路径"}],
  "metadata": {"version": "1.2", "os": "linux", "timestamp": "2026-07-20T10:00:00Z"}
}

```



### 3.3 工程内置引导 (`src/triggerforge/cli/init.py`)

* **行为规范**：
* **模板填充**：`init --template` 生成配置时，将为每个 `strategy` 显式填充 `working_dir`（推荐模式：`./output/{plugin_name}/`），降低新手理解成本。


* **路径处理**：模板预设路径统一使用 POSIX 风格 (`/`)。用户自定义路径不做自动转换，仅在 `--check` 阶段校验一致性。




* **系统环境兼容**：根据宿主 OS 动态适配权限位。



### 3.4 热加载与生命周期 (`src/triggerforge/engine/core.py`)

* **原子切换**：采用“校验-替换”原子操作。


* **路径隔离**：新配置生效后，新启动任务采用新路径；运行中任务保持原路径直至生命周期结束。



## 4. 测试策略与验收

* **路径与权限测试**：覆盖无权限/目录缺失场景，验证惰性创建 `0750` 权限有效性。


* **静态合规测试**：构造长路径、非法字符路径，验证 `--check` 拦截准确性。


* **集成验收**：提交 `audit_report.sample.json` 样板，确保 CI/CD 流水线解析兼容性。