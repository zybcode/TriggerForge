
```markdown
# TriggerForge v1.2 版本迁移指南

> **版本**：v1.2-Final (已修正)
> **状态**：生效中
> **目录**：docs/zh/migration_v1.2.md

## 1. 概述
本指南旨在协助用户将 TriggerForge 的配置文件升级至 v1.2 标准。v1.2 版本引入了更严格的超时约束与配置审计机制，部分旧有的配置项已被弃用，建议尽早完成迁移[cite: 8]。

## 2. 弃用字段与迁移映射表

| 弃用配置项 | 实际状态 | 迁移方案 | 移除版本 |
| :--- | :--- | :--- | :--- |
| `timeout` (全局) | 弃用 | 映射至 `max_execution_timeout` | v1.4[cite: 8] |
| `strategies[].timeout` | 兼容 | 归纳至 `strategy.timeout` | v1.4[cite: 8] |
| `debounce_seconds` | 已失效 | v1.1 已重构，配置将被忽略 | v1.3[cite: 8] |
| `recursive` | 已失效 | 默认开启，配置将被忽略 | v1.3[cite: 8] |

## 3. 核心迁移步骤

### 第一步：更新全局配置
将旧的 `timeout` 参数重命名为 `max_execution_timeout`，作为系统的安全底线[cite: 8]。

### 第二步：适配插件策略
将原有的插件配置更新至 `strategy` 嵌套对象中[cite: 8]。

**v1.2 标准配置示例：**
```yaml
watch_folders:
  - path: "./data"
    strategies:
      - plugin_name: "OCRProcessor"
        strategy: 
          timeout: 60
          priority: "high"             # 必须为 high 以支持超时覆盖
          allow_override_timeout: true # 需与 priority: high 组合使用

```

### 第三步：合规性预检

迁移完成后，运行以下命令验证配置合规性：

```bash
hatch run python scripts/config_manager.py --check

```

如果输出返回值为 0，则迁移成功。

## 4. 商业扩展兼容承诺

本版本配置结构已预留 `metadata` 扩展槽，确保现有 v1.2 配置在后续升级商业版（启用数字签名校验）时，无需进行任何格式调整，实现“平滑演进”。

## 5. 常见问题 (FAQ)

**Q：如何验证迁移是否成功？**
A：运行上述 `--check` 命令，若无错误输出且退出码为 0，则表示配置合规。审计结果将自动记录在系统审计日志中。

**Q：新旧配置可以混用吗？**
A：v1.2 支持向下兼容，但会触发 `DeprecationWarning` 日志。为了确保 v1.4 版本升级平滑，请务必在近期内完成全量迁移。

**Q：为什么新增了优先级字段及 `allow_override_timeout`？**
A：为了实现“资源防锁死”机制。**注意：当您设置 `allow_override_timeout = true` 时，必须同时将 `priority` 设为 `high`，否则系统将在启动时抛出配置校验异常，拒绝启动。**

**Q：商业扩展的元数据字段会影响当前运行吗？**
A：不会。`metadata` 字段在 v1.2 中仅作占位处理，且在启动校验阶段已被设计为忽略，确保开源版本用户无感使用。

---

*技术支持与开发详情可参考 [开发规划](https://www.google.com/search?q=./dev_plan_v1.2.md)。*

```

```