# 欢迎使用 TriggerForge

TriggerForge 是一个事件驱动的目录编排引擎：监控文件夹、按配置的插件流水线处理投递进来的文件，并把结果自动归档或隔离。

## 快速开始

### 1. 安装

```bash
python -m pip install -e .
```

### 2. 准备配置

创建 `config.yaml`（完整字段见 [配置参考](configuration.md)）：

```yaml
plugin_directory: "./plugins"

watch_folders:
  - path: "./storage/watch_folder"       # 投递文件到该目录即触发流水线
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 2
    debounce_seconds: 1.0
    strategies:
      - plugin_name: "my_plugin"         # 对应 plugins/my_plugin/main.py
        timeout: 15
        params:
          mode: "default"
```

### 3. 校验并启动

```bash
# 仅校验配置，不启动监听
python -m triggerforge.cli --config config.yaml --dry-run

# 启动守护进程
python -m triggerforge.cli --config config.yaml
```

终端出现 `TriggerForge looper is ready to receive files.` 后，说明监听器与工作线程均已就绪。

### 4. 投递文件验证

把任意文件复制到 `storage/watch_folder/`，引擎会自动：

1. 等待文件写入完成（防抖窗口）；
2. 以独立子进程依次执行 `strategies` 中的插件；
3. 成功 → 移动到 `storage/success_folder/`；失败 → 移动到 `storage/error_folder/`，并在 `logs/` 下生成 `panic_*.json` 诊断报告。

> 若文件未被处理，请先确认：监控目录路径是否正确、插件入口 `plugins/{plugin_name}/main.py` 是否存在、以及日志中是否出现 `Plugin not found` 或 JSON 解析失败提示。

## 延伸阅读

- [插件开发规范](plugin_dev.md) —— 插件入口、参数注入与输出契约
- [配置参考](configuration.md) —— 全部配置字段与运行时行为
- [架构设计](architecture.md) —— 分层模型与故障隔离机制
