# ⚙️ TriggerForge 配置指南 (Configuration Specification)

> **版本**：v1.1-PRO
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
| `timeout` | `int` | `30` | 可选 | 该插件子进程的硬超时熔断秒数，必须大于 0。超时将被强制终止。 |
| `params` | `Dict[str, Any]` | `{}` | 可选 | 传递给插件的动态自定义参数，会以 JSON 注入子进程。 |
| `python_path` | `Optional[str]` | `None` | 可选 | 指定独立解释器（虚拟环境）路径。路径不存在时自动回退到当前解释器。 |

---

## 二、 完整配置示例 (`config.sample.yaml`)

下面是一个生产就绪的配置示例。你可以直接复制此内容创建你的 `config.yaml` 并部署到生产环境中：

```yaml
# =================================================================
# TriggerForge 生产级配置文件示例
# =================================================================

# 插件根目录：引擎在 {plugin_directory}/{plugin_name}/main.py 下查找入口
plugin_directory: "./plugins"

# 全局默认防抖窗口（秒），可被每个监控目录覆盖
debounce_seconds: 1.0

watch_folders:
  - path: "./storage/watch_folder"       # 投递文件到该目录即触发流水线
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 4                       # 该目录独立的工作线程数量
    debounce_seconds: 1.0                # 该目录专属防抖窗口

    strategies:
      # 策略 1：调用现代压缩插件，限时 15 秒熔断
      - plugin_name: "compress_plugin"
        plugin_version: "1.0.0"
        timeout: 15                      # 15秒硬超时防锁死
        params:
          level: "high"
          archive_type: "tar.gz"

      # 策略 2：调用历史遗留数据解析插件，挂载独立的虚拟环境运行
      - plugin_name: "legacy_parser_plugin"
        plugin_version: "0.8.2"
        # 核心亮点：打破依赖冲突，子进程动态切换至老旧的独立隔离环境运行
        python_path: "/opt/venv/legacy_env/bin/python"
        timeout: 30                      # 30秒超时熔断
        params:
          legacy_mode: true
          encoding: "gbk"
```

---

## 三、 运行时行为说明

1. **事件链路**：文件写入监控目录 → 防抖窗口等待写入完成 → 进入事件缓冲队列 → 工作线程消费 → 串行执行 `strategies`。
2. **短路熔断**：`strategies` 中任一策略执行失败，后续策略不再执行，直接进入失败归档。
3. **归档策略**：全部策略成功 → `success_path`；任一失败 → 生成 `.panic.json` 诊断报告并移动至 `error_path`。
4. **配置校验**：启动时通过 `TriggerForgeConfigSchema` 校验；使用 `--dry-run` 可在不启动监听的情况下仅做校验。
