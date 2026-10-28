# ⚙️ TriggerForge 配置指南 (Configuration Specification)

> **版本**：v1.2-Final
> **对应代码**：`src/triggerforge/core/schema.py`
> **说明**：本文档中的字段定义与 `schema.py` 中的 Pydantic 模型保持一致。修改 Schema 后请同步更新本页表格。

---

## 一、 全局配置参数

TriggerForge 主配置文件采用标准 YAML 格式，核心配置分为**全局调度参数**与**监控目录策略**两大模块。

### 1. 核心字段定义

| 字段名 | 类型 | 默认值 | 状态 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `watch_folders` | `List[WatchFolderSchema]` | 无 | **(必填)** | 系统监听的监控目录策略列表，支持配置多个独立目录。 |
| `plugin_directory` | `str` | `"./plugins"` | 可选 | 插件根目录。引擎在该目录下按 `{plugin_name}/main.py` 查找插件入口。 |
| `debounce_seconds` | `float` | `1.0` | 可选 | 全局默认文件写入防抖窗口（秒），必须大于 0。可被每个监控目录单独覆盖。 |
| `max_execution_timeout` | `Optional[int]` | `None` | 可选（v1.2） | 全局执行超时硬上限（安全底线）。策略 `timeout` 超过该值时被运行时钳制，除非策略满足 `priority="high"` + `allow_override_timeout=true` 豁免。 |

> **v1.2 弃用迁移**：旧全局 `timeout` 键自动映射为 `max_execution_timeout` 并触发 `DeprecationWarning`，计划于 v1.4 移除。详见 [迁移指南](./migration_v1.2.md)。

### 2. `WatchFolderSchema` (监控目录配置对象)

| 字段名 | 类型 | 默认值 | 状态 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `path` | `str` | 无 | **(必填)** | 引擎实施事件监听的源目标目录。投递文件至该目录即触发插件流水线。 |
| `success_path` | `str` | 无 | **(必填)** | 插件流水线全部执行成功后，源文件被原子化移动至该归档目录。 |
| `error_path` | `str` | 无 | **(必填)** | 任一插件执行失败或超时熔断后，源文件被移动至该故障隔离目录。 |
| `concurrency` | `int` | `1` | 可选 | 该监控目录分配的工作线程数量，必须大于 0。 |
| `debounce_seconds` | `float` | `1.0` | 可选 | 该目录专属的写入防抖窗口（秒），必须大于 0。 |
| `strategies` | `List[StrategySchema]` | 无 | **(必填)** | 事件触发后按顺序串行执行的插件策略流水线。 |

### 3. `StrategySchema` (插件执行策略配置对象)

| 字段名 | 类型 | 默认值 | 状态 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `plugin_name` | `str` | 无 | **(必填)** | 插件目录名，引擎据此定位 `{plugin_directory}/{plugin_name}/main.py`。 |
| `plugin_version` | `str` | `"0.0.0"` | 可选 | 插件版本标识，用于运行时校验与审计。 |
| `timeout` | `int` | `30` | 可选 | 该插件子进程的硬超时熔断秒数，必须大于 0。超时将被强制终止。旧扁平写法已弃用，推荐迁移至 `strategy.timeout` 嵌套对象（v1.4 移除扁平写法）。 |
| `params` | `Dict[str, Any]` | `{}` | 可选 | 传递给插件的动态自定义参数，会以 JSON 注入子进程。 |
| `python_path` | `Optional[str]` | `None` | 可选 | 指定独立解释器（虚拟环境）路径。路径不存在时自动回退到当前解释器。 |
| `strategy` | `Optional[dict]` | `None` | 可选（v1.2） | **新标准嵌套对象**：可承载 `timeout` / `priority` / `allow_override_timeout`，嵌套键优先于扁平字段。 |
| `priority` | `Literal["high","standard","low"]` | `"standard"` | 可选（v1.2） | 策略优先级枚举。**仅 `high` 支持超时覆盖**；`standard`/`low` 不支持。 |
| `allow_override_timeout` | `bool` | `false` | 可选（v1.2） | 超时覆盖豁免开关。**双重约束**：置 `true` 时必须同时指定 `priority="high"`，否则启动预检抛 `ValueError` 拒绝启动（资源防锁死机制）。 |
| `metadata` | `Dict[str, Any]` | `{}` | 可选（v1.2） | 商业扩展预留槽（数字签名 / License Hash / 客户授权信息）。v1.2 开源版仅占位，启动校验阶段忽略，保证向前兼容。 |

---

## 二、 完整配置示例 (`config.sample.yaml`)

下面是一个生产就绪的配置示例。你可以直接复制此内容创建你的 `config.yaml` 并部署到生产环境中：

```yaml
# =================================================================
# TriggerForge 生产级配置文件示例 (v1.2)
# =================================================================

# 插件根目录：引擎在 {plugin_directory}/{plugin_name}/main.py 下查找入口
plugin_directory: "./plugins"

# 全局默认防抖窗口（秒），可被每个监控目录覆盖
debounce_seconds: 1.0

# 全局执行超时硬上限（安全底线，v1.2 新增）
max_execution_timeout: 300

watch_folders:
  - path: "./storage/watch_folder"       # 投递文件到该目录即触发流水线
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 4                       # 该目录独立的工作线程数量
    debounce_seconds: 1.0                # 该目录专属防抖窗口

    strategies:
      # 策略 1（v1.2 嵌套写法）：核心高优策略，允许突破全局超时上限
      - plugin_name: "compress_plugin"
        plugin_version: "1.0.0"
        strategy:
          timeout: 15
          priority: "high"               # 仅 high 支持 allow_override_timeout
          allow_override_timeout: true   # 必须与 priority: high 组合使用
        params:
          level: "high"
          archive_type: "tar.gz"

      # 策略 2：普通标准策略 + 独立虚拟环境
      - plugin_name: "legacy_parser_plugin"
        plugin_version: "0.8.2"
        python_path: "/opt/venv/legacy_env/bin/python"
        strategy:
          timeout: 30
          priority: "standard"           # 默认值，不可开启超时覆盖
        params:
          legacy_mode: true
          encoding: "gbk"
```

---

## 三、 运行时行为说明

1. **事件链路**：文件写入监控目录 → 防抖窗口等待写入完成 → 进入事件缓冲队列 → 工作线程消费 → 串行执行 `strategies`。
2. **短路熔断**：`strategies` 中任一策略执行失败，后续策略不再执行，直接进入失败归档。
3. **归档策略**：全部策略成功 → `success_path`；任一失败 → 生成 `.panic.json` 诊断报告并移动至 `error_path`。
4. **配置校验**：启动时通过 `TriggerForgeConfigSchema` 校验；使用 `--dry-run` 仅校验、`--check` 执行 v1.2 完整合规审计（退出码 0/1/2/3）。
5. **资源防锁死（v1.2）**：策略 `timeout` 超过 `max_execution_timeout` 时被运行时钳制到硬上限；仅 `priority="high"` 且 `allow_override_timeout=true` 的策略可豁免。
6. **热加载（v1.2）**：向引擎进程发送 `SIGHUP` 触发配置热加载；新配置先经 `ForgeConfigManager` 完整审计，失败则保持当前运行配置不变并告警，成功则"校验-替换"原子切换并输出前后对比审计摘要。
