针对评审专家提出的最后 2 项修正要求（补充 `priority` 约束说明及统一状态标记），以下是最终修正后的完整版 `dev_plan_v1.2.md`，可直接确认归档。

```markdown
# TriggerForge v1.2 开发规划文档

> **版本**：v1.2-Final (已修正)
> **状态**：已修正（待归档）
> **目录**：docs/zh/dev_plan_v1.2.md

## 1. 概述
本版本致力于实现 TriggerForge 的运维自动化闭环，核心目标是提升系统在高负载下的稳定性与防锁死能力，并正式引入配置热加载机制，为未来商业化工具链提供稳定的基座支持。

## 2. 核心任务清单
| 序号 | 任务模块 | 关键开发内容 |
| :--- | :--- | :--- |
| 1 | **Schema 扩展** | 实现 `priority` 与 `allow_override_timeout` 校验逻辑及 `metadata` 扩展槽[cite: 9]。 |
| 2 | **配置审计引擎** | 开发 `ForgeConfigManager`，支持 `--check` 模式与结构化 JSON 输出[cite: 9]。 |
| 3 | **热加载机制** | 实现 `SIGHUP` 信号监听，支持原子化配置切换与回滚降级[cite: 9]。 |
| 4 | **迁移指引** | 编写 `migration_v1.2.md`，明确弃用状态及迁移路径[cite: 9]。 |
| 5 | **集成测试** | 覆盖豁免越权、热加载一致性及原子切换测试[cite: 9]。 |

## 3. 技术详细实现要求

### 3.1 双重约束校验逻辑 (`src/triggerforge/core/schema.py`)
在 `PluginStrategySchema` 模型中实现 `model_validator`[cite: 9]：
* **强制约束**: 当 `allow_override_timeout = true` 时，必须同时指定 `priority = "high"`。若条件不满足，引擎在启动预检阶段抛出 `ValueError` 并拒绝启动，确保系统安全性[cite: 9]。
* **商业扩展预留**: 新增 `metadata` 字典字段，用于承载未来商业版本需要的数字签名、License Hash 或客户授权信息。该设计保持了 YAML 结构的向前兼容性[cite: 9]。

### 3.2 配置审计接口与热加载处理 (`src/triggerforge/utils/config_manager.py`)
* **热加载原子性校验**: 接收 `SIGHUP` 后，触发 `ForgeConfigManager` 进行审计。若新配置校验失败，则**保持当前运行配置不变**，输出错误审计日志并发出告警，确保系统状态不因错误配置而崩溃[cite: 9]。
* **退出码规范**: 0 (合规), 1 (违规), 2 (语法错误), 3 (内部执行异常)[cite: 9]。

### 3.3 热加载机制 (`src/triggerforge/engine/core.py`)
* **原子切换**: 采用“校验-替换”原子操作，非逐字段替换，确保热加载流程中系统内存中的配置集始终保持一致性[cite: 9]。
* **审计追踪**: 切换完成后，系统强制输出审计变更摘要（含前后配置对比），并更新运行状态日志[cite: 9]。

## 4. 插件开发对齐标准
* **标准化输出**: 插件须遵循 JSON 日志规范[cite: 9]。
* **优先级枚举**: 统一枚举值：`high` (高), `standard` (标准), `low` (低)[cite: 9]。
* **约束说明**: **仅当 `priority = "high"` 时，`allow_override_timeout` 字段才能设置为 `true`。`standard` 与 `low` 级别不支持超时覆盖。**

## 5. 测试策略
* **单元测试**: 使用 `hatch run pytest tests/test_config_manager.py -v` 执行配置审计模块专项测试。针对 `SIGHUP` 触发的重载逻辑增加时序测试，确保原子性切换[cite: 9]。
* **集成测试**: 将 `--check` 模式接入 Git Hooks，并增加自动化脚本模拟配置文件变更与信号发送，确保热加载流程稳定性[cite: 9]。

---
*注：本开发规划已符合架构评审要求，待最终归档。参考 [迁移指南](./migration_v1.2.md)。*

```