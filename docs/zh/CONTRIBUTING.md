
---

### 1. 文件路径：`docs/zh/CONTRIBUTING.md`

```markdown
# 参与 TriggerForge 贡献指南

感谢你对 TriggerForge 的关注！我们非常欢迎任何形式的贡献，无论是功能开发、文档改进还是问题反馈。

## 1. 如何参与
### 1.1 提交问题 (Issues)
在提交 PR 前，请先检查是否已存在相关的 Issue。如果没有，请创建一个新的 Issue 并详细描述：
- 问题背景或功能建议。
- 复现步骤（如果是 Bug）。
- 期望的结果。

### 1.2 开发流程
1. **环境准备**: 使用 `hatch` 管理环境 (`hatch shell`)。
2. **分支管理**: 请从 `main` 分支拉取，遵循 `feature/功能名` 或 `fix/问题描述` 的分支命名规范。
3. **Commit 规范**: 建议遵循 [Conventional Commits](https://www.conventionalcommits.org/) 标准。

## 2. 自动化检查 (重点)
TriggerForge 采用了严格的配置审计机制。在提交代码前，必须确保通过本地校验：
```bash
# 运行配置审计逻辑单元测试
hatch run pytest tests/test_config_manager.py -v

# 运行全量测试套件
hatch run cov

```

## 3. 法律合规 (CLA)

本项目要求所有贡献者签署《贡献者许可协议》(CLA)。

* 当你发起第一个 Pull Request 时，CLA Assistant 会自动在 PR 下方留言。
* 请点击链接并签署 [CLA (docs/legal/CLA.md)](https://www.google.com/search?q=../legal/CLA.md)。只有协议状态显示为 "Passed" 后，你的 PR 才能被合并。

## 4. 文档贡献

本项目采用中英文双语文档。

* **文档路径**: 修改 `docs/zh/` 的同时，请尽量同步更新 `docs/en/`。
* **翻译协助**: 如果你只提交中文版本，维护者会协助进行翻译。

## 5. 行为准则

请保持友好交流。所有的决策均基于技术事实，并参考 [架构评审意见](https://www.google.com/search?q=../dev_plan_v1.2.md)。

```
