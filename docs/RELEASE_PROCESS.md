# Release Process

## 1. 如何查看版本

```bash
python -m ashare_alpha show-version
python -m ashare_alpha show-version --format json
```

当前 MVP 运行时版本记录在根目录 `VERSION` 和 `src/ashare_alpha/__init__.py`。`pyproject.toml` 使用 PEP 440 兼容的 `0.1.0`，发布标签使用 `0.1.0-mvp`。

## 2. 如何运行 release-check

```bash
python -m ashare_alpha release-check
python -m ashare_alpha release-check --format json
python -m ashare_alpha release-check --output-dir outputs/release/v0.1.0-mvp
```

`release-check` 只做本地文件、安全配置、源码禁用文本、版本一致性和工具可用性检查。它不联网，不运行重型回测，不调用外部 API。

## 3. 发布前推荐命令

```bash
python scripts/dev_check.py
python scripts/smoke_test.py
pytest
ruff check
python -m ashare_alpha run-pipeline --date 2026-03-20 --audit-leakage --quality-report --check-security
python -m ashare_alpha build-dashboard
python -m ashare_alpha release-check
```

## 4. 如何阅读 release_manifest.json

`release_manifest.json` 是机器可读发布清单，包含：

- `version`：当前发布版本。
- `checks_passed`：是否没有 FAIL。
- `pass_count` / `warn_count` / `fail_count`：检查统计。
- `checks`：每个检查项的状态、消息和建议。
- `key_files`：关键文件是否存在。
- `key_commands`：发布前建议执行的命令矩阵。
- `safety_summary`：离线、安全和非实盘边界摘要。

## 5. 如何阅读 release_checklist.md

`release_checklist.md` 是人工验收清单，包含版本信息、检查结果、文件检查、安全检查、已知限制和发布前建议。WARN 不阻断发布，但发布前应确认原因；FAIL 会让 `release-check` 返回非 0。

## 6. 当前版本边界

- 研究系统。
- 本地 CSV / 离线 fixture。
- 不联网。
- 不接券商。
- 不自动下单。
- 不保证收益。
- 不构成投资建议。

## 7. 后续版本建议

- 真实数据接入前继续加强数据质量、时间点一致性和防泄漏审计。
- 真实数据 Adapter 先实现 cache/offline 运行模式。
- 保持安全开关默认离线。
- 不直接接实盘交易能力。
