
```markdown
# Contributing to TriggerForge

Thank you for your interest in TriggerForge! We welcome contributions of all forms, whether it's feature development, documentation improvements, or bug reports.

## 1. How to Contribute
### 1.1 Issues
Before submitting a Pull Request, please check if there is an existing issue. If not, create a new issue detailing:
- The context or feature proposal.
- Steps to reproduce (if it's a bug).
- Expected results.

### 1.2 Development Workflow
1. **Environment**: Use `hatch` for environment management (`hatch shell`).
2. **Branching**: Branch from `main` using `feature/<feature-name>` or `fix/<description>`.
3. **Commit Messages**: Please follow the [Conventional Commits](https://www.conventionalcommits.org/) standard.

## 2. Automated Checks (Crucial)
TriggerForge employs strict configuration auditing. Before submitting your code, ensure you pass the local validation:
```bash
# Run unit tests for configuration audit logic
hatch run pytest tests/test_config_manager.py -v

# Run full test suite
hatch run cov

```

## 3. Legal Compliance (CLA)

All contributors are required to sign the Contributor License Agreement (CLA).

* When you open your first Pull Request, the CLA Assistant will automatically comment on your PR.
* Please follow the link to sign the [CLA (docs/legal/CLA.md)](https://www.google.com/search?q=../legal/CLA.md). Your PR can only be merged after the status check shows "Passed".

## 4. Documentation

TriggerForge maintains bilingual documentation.

* **Paths**: Please keep both `docs/zh/` and `docs/en/` updated.
* **Assistance**: If you only submit a Chinese version, a maintainer will assist with the English translation.

## 5. Code of Conduct

Please maintain a friendly and professional environment. All decisions are based on technical facts and the [Architecture Review Board's consensus](https://www.google.com/search?q=../dev_plan_v1.2.md).

```
