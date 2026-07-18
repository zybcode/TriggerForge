
```markdown
# TriggerForge v1.2 版本迁移指南

> **版本**：v1.2-Final (已终审)
> **状态**：生效中
> **目录**：docs/zh/migration_v1.2.md

## 1. 概述
本指南旨在协助用户将 TriggerForge 的配置文件升级至 v1.2 标准。v1.2 版本引入了更严格的超时约束与配置审计机制，部分旧有的配置项已被弃用，建议尽早完成迁移。

## 2. 弃用字段与迁移映射表

| 弃用配置项 | 推荐新配置项 | 处置方案 | 计划移除版本 |
| :--- | :--- | :--- | :--- |
| `timeout` (全局) | `max_execution_timeout` | 重命名，明确为全局硬约束 | v1.4 |
| `strategies[].timeout` | `strategies[].strategy.timeout` | 归纳至策略对象 | v1.4 |
| `debounce_seconds` | (移除) | v1.1 已重构，无需配置 | v1.3 |
| `recursive` | (移除) | 默认开启，降低复杂度 | v1.3 |

## 3. 核心迁移步骤

### 第一步：更新全局配置
将旧的 `timeout` 参数重命名为 `max_execution_timeout`，作为系统的安全底线。

### 第二步：适配插件策略
将原有的插件配置更新至 `strategy` 嵌套对象中。

**v1.2 标准配置示例：**
```yaml
watch_folders:
  - path: "./data"
    strategies:
      - plugin_name: "OCRProcessor"
        strategy: 
          timeout: 60
          priority: "standard"
          allow_override_timeout: false

```

### 第三步：合规性预检

迁移完成后，运行以下命令验证配置合规性：

```bash
hatch run python scripts/config_manager.py --check

```

*如果输出返回值为 0，则迁移成功。*

## 4. 常见问题 (FAQ)

**Q：如何验证迁移是否成功？**
A：运行上述 `--check` 命令，若无错误输出且退出码为 0，则表示配置合规。审计结果将自动记录在系统审计日志中。

**Q：新旧配置可以混用吗？**
A：v1.2 支持向下兼容，但会触发 `DeprecationWarning` 日志。为了确保 v1.4 版本升级平滑，请务必在近期内完成全量迁移。

**Q：为什么新增了优先级字段？**
A：为了实现“资源防锁死”机制。高优先级插件（需配合 `allow_override_timeout`）可获得更长的运行时间，平衡核心业务稳定性与资源占用。

---

*技术支持与开发详情可参考 [开发规划](https://www.google.com/search?q=../zh/dev_plan_v1.2.md)。*

```

```