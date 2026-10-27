# 🔌 TriggerForge 插件开发规范 (Plugin Development Specification)

> **版本**: v1.1-PRO
> **状态**: 已批准
> **对应实现**: `src/triggerforge/core/runner/plugin_runner.py`
> **适用范围**: 为构建模块化工作流的内部开发者及开源社区贡献者提供的权威生命周期接口指南。

---

## I. 架构理念与沙箱约束

为了确保核心引擎的绝对鲁棒性，TriggerForge 执行严格的 **“零信任插件模型”**。在执行流水线中注册的每一个插件都必须遵守以下运行时防护机制：

1. **子进程沙箱 (Subprocess Sandboxing)**：插件绝不会在核心监控进程内执行。它们作为独立的子进程被调用，确保内存限制和致命运行时错误（如段错误 Segfaults）被安全地隔离。
2. **防御性超时 (Defensive Timeouts)**：每个插件的生命周期都受严格的时间围栏限制。如果插件锁定或阻塞超过 `timeout` 阈值，子进程将被强制终止，文件进入故障隔离区。
3. **动态虚拟环境 (Dynamic Virtual Environments)**：插件可通过 `python_path` 明确指定特定的 Python 运行时。这使得需要旧版本依赖的遗留脚本能够与现代流水线无缝共存。
4. **短路熔断 (Short-Circuit)**：同一目录的 `strategies` 串行执行，任一插件失败则后续插件不再执行。

---

## II. 插件目录与入口约定

插件以**扁平化目录**形式存放，一个插件一个目录：

```plaintext
{plugin_directory}/           # 由配置项 plugin_directory 指定，默认 ./plugins
└── my_plugin/                # 目录名必须与策略中的 plugin_name 完全一致
    └── main.py               # 入口文件（备选：plugin.py、index.py）
```

引擎按 `main.py` → `plugin.py` → `index.py` 的顺序查找入口文件，全部缺失时该策略判定为失败。

---

## III. 执行契约（进程级接口）

插件**不是**通过类继承接入的，而是作为一个可执行的 Python 脚本被引擎拉起。引擎构建的命令行如下：

```bash
{interpreter} {plugin_main.py} {target_file} ["{json_params}"]
```

### 1. 输入通道

| 通道 | 内容 | 说明 |
| :--- | :--- | :--- |
| `sys.argv[1]` | 目标文件的**绝对路径** | 必传。即投递到监控目录、触发本次流水的文件。 |
| `sys.argv[2]` | 策略 `params` 的 JSON 字符串 | 仅在 `params` 非空时传入。 |
| 环境变量 `TRIGGERFORGE_PARAMS` | 策略 `params` 的 JSON 字符串 | 仅在 `params` 非空时设置，便于不解析 argv 的插件读取。 |
| 工作目录 | 引擎进程的当前工作目录 | 插件不应假设 cwd 为监控目录，请使用 `argv[1]` 的绝对路径。 |

### 2. 输出契约

插件必须向 **stdout 输出且仅输出一个 JSON 对象**，用于告知引擎执行结果：

```json
{"status": "success", "message": "processed 42 rows"}
```

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `status` | `str` | 是 | 值为 `"success"` 表示成功；其他值均视为失败并转入故障隔离区。 |
| 其他字段 | 任意 | 否 | 会原样保留在引擎的返回值中，可用于审计与日志（如 `message`、`rows`）。 |

> ⚠️ **重要**：若插件在 stdout 打印了额外的调试信息（非 JSON），引擎将因 JSON 解析失败判定该插件失败。调试信息请写入 **stderr**，引擎会把它记录进诊断报告（`.panic.json`）。

### 3. 退出码与失败判定

| 场景 | 引擎行为 |
| :--- | :--- |
| 退出码 `0` 且 stdout 为合法 JSON 且 `status == "success"` | 判定成功，继续执行下一个策略；全部成功则归档至 `success_path` |
| 退出码非 `0` | 判定失败，捕获 stderr 作为错误摘要 |
| 退出码 `0` 但 stdout 非合法 JSON | 判定失败（提示插件未输出合法 JSON） |
| 超过 `timeout` 秒未退出 | 强制终止子进程，判定失败 |
| 抛出未捕获异常 | 进程以非零码退出，判定失败 |

任一策略失败后，引擎会：
1. 在 `log_dir`（默认 `logs/`）下生成 `panic_{plugin_name}_{timestamp}.json` 故障现场诊断报告；
2. 将源文件移动至该监控目录配置的 `error_path`。

---

## IV. 参考实现

### 1. 最小可用插件

```python
# plugins/my_plugin/main.py
import json
import sys
from pathlib import Path

def main() -> int:
    target = Path(sys.argv[1])

    # 可选：读取策略参数
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    # 你的处理逻辑（示例：统计文件字节数）
    size = target.stat().st_size

    # 必须向 stdout 输出单个 JSON 对象
    print(json.dumps({
        "status": "success",
        "file": target.name,
        "size_bytes": size,
        "mode": params.get("mode", "default"),
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### 2. 对应的策略配置

```yaml
plugin_directory: "./plugins"

watch_folders:
  - path: "./storage/watch_folder"
    success_path: "./storage/success_folder"
    error_path: "./storage/error_folder"
    concurrency: 2
    debounce_seconds: 1.0
    strategies:
      - plugin_name: "my_plugin"     # 对应 plugins/my_plugin/main.py
        plugin_version: "1.0.0"
        timeout: 15
        params:
          mode: "strict"
```

### 3. 失败上报示例

```python
import json
import sys

def main() -> int:
    try:
        # ... 业务逻辑 ...
        raise ValueError("malformed input")
    except Exception as exc:
        # 失败也必须输出 JSON，便于引擎记录错误摘要
        print(json.dumps({"status": "failed", "error": str(exc)}))
        print(f"traceback details: {exc}", file=sys.stderr)   # 详细信息走 stderr
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## V. 插件自测清单

在接入流水线前，请在插件目录下手动验证：

```bash
# 1. 直接用引擎相同的命令行调用插件
python main.py /absolute/path/to/sample.txt '{"mode": "strict"}'

# 2. 确认 stdout 是单个合法 JSON 且 status 为 success
# 3. 确认退出码为 0（Windows: echo %ERRORLEVEL% / bash: echo $?）
```

若插件需要独立依赖环境，请在策略中配置 `python_path` 指向该虚拟环境的解释器；路径无效时引擎会告警并回退到当前解释器执行。
