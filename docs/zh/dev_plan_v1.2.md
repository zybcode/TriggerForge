# TriggerForge v1.2 开发规划文档

> **版本**：v1.2-Final (已终审)
> **状态**：启动开发
> **目录**：docs/zh/dev_plan_v1.2.md

## 1. 概述
本版本旨在构建 TriggerForge 的运维自动化闭环，核心目标是实现配置管理的流水线式管理，并通过“全局约束 + 插件策略”的联动，提升系统在高负载下的稳定性与防锁死能力。

## 2. 核心任务清单

| 序号 | 任务模块 | 关键开发内容 |
| :--- | :--- | :--- |
| 1 | **Schema 扩展** | 实现 `priority` 枚举与 `allow_override_timeout` 标志位，引入双重校验逻辑。 |
| 2 | **配置审计引擎** | 开发 `ForgeConfigManager`，支持 `--check` 模式与结构化 JSON 输出。 |
| 3 | **架构基准更新** | 补充进程级调度机制说明及 v1.3 热加载演进方向。 |
| 4 | **迁移指引** | 编写 `migration_v1.2.md`，明确弃用字段清单及升级路径。 |
| 5 | **集成测试** | 构建单元测试，覆盖豁免越权与边界条件检查。 |

## 3. 技术详细实现要求

### 3.1 双重约束校验逻辑 (`src/triggerforge/core/schema.py`)
在 `PluginStrategySchema` 模型中实现 `model_validator`：
*   当 `allow_override_timeout` 设置为 `True` 时，必须同时指定 `priority = "high"`。
*   违规配置需在启动预检阶段抛出 `ValueError`，阻断引擎运行。

### 3.2 配置审计接口 (`src/triggerforge/utils/config_manager.py`)
*   **CLI 交互**: 
    *   **终端模式**: 输出人类可读的彩色报告。
    *   **CI/CD 模式**: 通过环境变量 `CI=true` 检测，强制输出符合标准格式的 JSON 报告。
*   **退出码规范 (Exit Codes)**:
    *   **0**: 校验通过，配置合规。
    *   **1**: 校验失败，存在违规配置（如超时溢出）。
    *   **2**: 文件不存在或 YAML 语法错误。
    *   **3**: 内部执行异常。
*   **JSON 结构**:
    ```json
    {
      "status": "fail",
      "exit_code": 1,
      "errors": [
        {"field": "plugin_name", "message": "描述详细错误原因"}
      ]
    }
    ```

## 4. 测试策略
*   **单元测试**: 使用 `hatch run pytest tests/test_config_manager.py -v` 执行配置审计模块的专项测试，确保豁免逻辑覆盖率 > 90%。
*   **集成测试**: 将 `--check` 模式接入 Git Hooks，确保配置变更在提交阶段即可完成自动化审计。

## 5. 系统演进预览
*   **v1.3 预留**: 计划引入 `SIGHUP` 信号支持配置热加载，以实现无中断更新。
*   **可观测性**: 未来规划将配置元数据接入 Prometheus 等监控系统，实现配置维度的可观测性。

---
*注：本开发规划已通过架构评审委员会批准，开发过程中若涉及逻辑变动，需报备评审专家组。请参考 [迁移指南](../zh/migration_v1.2.md) 进行配置平滑演进。*