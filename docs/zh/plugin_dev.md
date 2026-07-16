# 🔌 TriggerForge 插件开发规范 (Plugin Development Specification)

> **版本**: v1.1-PRO  
> **状态**: 已批准  
> **适用范围**: 为构建模块化工作流的内部开发者及开源社区贡献者提供的权威生命周期接口指南。

---

## I. 架构理念与沙箱约束

为了确保核心引擎的绝对鲁棒性，TriggerForge 执行严格的 **“零信任插件模型”**。在执行流水线中注册的每一个插件都必须遵守以下运行时防护机制：

1. **子进程沙箱 (Subprocess Sandboxing)**：插件绝不会在核心监控进程内执行。它们作为独立的子进程被调用，确保内存限制和致命运行时错误（如段错误 Segfaults）被安全地隔离。
2. **防御性超时 (Defensive Timeouts)**：每个插件的生命周期都受严格的时间围栏限制。如果插件锁定或阻塞超过配置阈值，它将被强制终止。
3. **动态虚拟环境 (Dynamic Virtual Environments)**：插件可通过 `python_path` 明确指定特定的 Python 运行时。这使得需要旧版本依赖的遗留脚本能够与现代流水线无缝共存。

---

## II. 基础接口 (`BasePlugin`)

所有 TriggerForge 插件必须使用 Python 编写，并继承自抽象基类 `BasePlugin`。引擎将完全通过这一抽象契约与您的自定义逻辑进行交互。

### 1. 接口定义
您的插件模块必须暴露一个实现以下结构的具体类：

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Path

class BasePlugin(ABC):
    """
    抽象基类：定义 TriggerForge 插件的生命周期契约。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        返回插件的唯一标识字符串。
        必须与 config.yaml 中指定的 'plugin_name' 一致。
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        返回插件的语义版本字符串（例如 '1.0.0'）。
        """
        pass

    @abstractmethod
    def execute(self, target_file: Path, params: Dict[str, Any]) -> bool:
        """
        由 ForgeCore 子进程管理器调用的核心执行流水线块。
        
        参数:
            target_file (Path): 触发事件的目标文件绝对路径。
            params (Dict[str, Any]): 从 YAML 配置文件中传递下来的动态自定义参数。
            
        返回:
            bool: 处理成功返回 True；如果发生预期内的失败，返回 False。
        """
        pass