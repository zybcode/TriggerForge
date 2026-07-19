这是已修正为**相对路径引用**的 `migration_v1.2.md` 全文。该引用方式在本地编辑器可直接跳转，在 GitHub 上提交后将自动适配当前分支，无需在后续合并中进行任何人工维护。

---

# TriggerForge v1.2 版本迁移指南

> **版本**：v1.2-Final-Revised
> **状态**：已锁定（归档版）
> **目录**：docs/zh/migration_v1.2.md

## 1. 概述

本指南旨在协助用户将 TriggerForge 的配置文件升级至 v1.2 标准。v1.2 版本引入了更严格的超时约束、路径管理规范及配置审计机制，建议参考本指南完成全量迁移。

## 2. 弃用字段与迁移映射表

| 弃用配置项 | 实际状态 | 迁移方案 | 移除版本 |
| --- | --- | --- | --- |
| `timeout` (全局) | 弃用 | 映射至 `max_execution_timeout` | v1.4 |
| `strategies[].timeout` | 兼容 | 归纳至 `strategy.timeout` | v1.4 |
| `debounce_seconds` | 已失效 | v1.1 已重构，配置将被忽略 | v1.3 |
| `recursive` | 已失效 | 默认开启，配置将被忽略 | v1.3 |

## 3. 核心迁移步骤

### 第一步：更新全局配置

将旧的 `timeout` 参数重命名为 `max_execution_timeout`，作为系统的安全底线。

### 第二步：适配插件策略与路径管理

将插件配置更新至 `strategy` 对象，并根据 v1.2 规范显式配置 `working_dir`。

**v1.2 标准配置示例：**

```yaml
watch_folders:
  - path: "./data/input"
    strategies:
      - plugin_name: "OCRProcessor"
        strategy: 
          working_dir: "./output/OCRProcessor" # 新增路径配置
          timeout: 60
          priority: "high"             # 必须为 high 以支持超时覆盖
          allow_override_timeout: true # 需与 priority: high 组合使用

```

> **说明**：若 `working_dir` 指定的目录尚不存在，系统将在插件首次运行时自动创建（权限 `0750`，自动创建父级目录），无需用户手动创建。

### 第三步：合规性预检

迁移完成后，运行以下命令验证配置合规性：

```bash
hatch run python scripts/config_manager.py --check --format json

```

若输出 `status` 为 `pass`，则迁移成功。

## 4. 商业扩展兼容与新手建议

* **兼容性**：配置结构已预留 `metadata` 扩展槽，确保后续升级商业版（启用数字签名校验）时无需格式调整。
* **新手引导**：若不确定如何配置，建议使用 `triggerforge init --template` 命令自动生成符合 v1.2 标准的基准配置文件，系统将自动填充推荐的 `working_dir` 结构。

## 5. 常见问题 (FAQ)

**Q：新旧配置可以混用吗？**
A：v1.2 支持向下兼容，但会触发 `DeprecationWarning` 日志。建议尽快完成全量迁移，以确保 v1.4 版本升级平滑。

**Q：如何验证迁移是否成功？**
A：运行 `--check` 命令，若无错误输出且退出码为 0，即表示配置合规。

**Q：`working_dir` 配置后，旧任务会受影响吗？**
A：不会。热加载生效后，新配置仅对新任务生效，已运行的任务将继续使用原始路径，直至当前生命周期结束。

---

*技术支持与详细规划可参考 [开发规划文档](./dev_plan_v1.2.md)。*