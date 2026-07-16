# ⚙️ TriggerForge 配置指南 (Configuration Specification)

> **版本**：v1.1-PRO  
> **注意**：本文档由系统配置 Schema 自动生成，请勿手动修改。如需变更配置项，请修改 `src/triggerforge/core/schema.py` 并重新运行 `python scripts/generate_docs.py`。

---

## 一、 全局配置参数

TriggerForge 主配置文件采用标准 YAML 格式，核心配置分为**全局调度参数**与**监控目录策略**两大模块。

### 1. 核心字段定义

| 字段名 | 类型 | 默认值 | 状态 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `watch_folders` | `List[WatchFolderSchema]` | `[]` | **(必填)** | 系统监听的监控目录策略列表，支持配置多个独立目录。 |

### 2. `WatchFolderSchema` (监控目录配置对象)

<!-- WATCH_FOLDER_SCHEMA_TABLE -->

### 3. `PluginStrategySchema` (插件执行策略配置对象)

<!-- PLUGIN_STRATEGY_SCHEMA_TABLE -->

---

## 二、 完整配置示例 (`config.sample.yaml`)

下面是一个生产就绪的配置示例。你可以直接复制此内容创建你的 `config.yaml` 并部署到生产环境中：

```yaml
# =================================================================
# TriggerForge 生产级配置文件示例
# =================================================================

watch_folders:
  - path: "./storage/watch_folder"
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 4                      # 哨兵层独立线程池并发大小
    strategies:
      # 策略 1：调用现代压缩插件，限时 15 秒熔断
      - plugin_name: "compress_plugin"
        plugin_version: "1.0.0"
        timeout: 15                     # 15秒硬超时防锁死
        params:
          level: "high"
          archive_type: "tar.gz"

      # 策略 2：调用历史遗留数据解析插件，挂载独立的虚拟环境运行
      - plugin_name: "legacy_parser_plugin"
        plugin_version: "0.8.2"
        # 核心亮点：打破依赖冲突，子进程动态切换至老旧的独立隔离环境运行
        python_path: "/opt/venv/legacy_env/bin/python" 
        timeout: 30                     # 30秒超时熔断
        params:
          legacy_mode: true
          encoding: "gbk"