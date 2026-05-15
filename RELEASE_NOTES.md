# ashare-alpha-lab 0.1.0-mvp 发布说明

## 1. 版本定位

这是 A 股个股量化研究系统 MVP，不是实盘交易系统。当前版本用于离线研究、回测、信号生成、报告和发布前检查。

运行时版本为 `0.1.0-mvp`，记录在 `VERSION` 和 `ashare_alpha.__version__` 中。`pyproject.toml` 保留 PEP 440 兼容的 `0.1.0`，用于避免破坏现有安装和打包流程。

## 2. 当前能做什么

- `python -m ashare_alpha show-version`：查看版本、包位置和 Python 版本。
- `python -m ashare_alpha release-check`：生成本地发布检查清单和 manifest。
- `python -m ashare_alpha show-config`：加载并校验项目配置。
- `python -m ashare_alpha validate-data`：校验本地 CSV 样例数据。
- `python -m ashare_alpha build-universe --date 2026-03-20`：构建日度股票池。
- `python -m ashare_alpha compute-factors --date 2026-03-20`：计算日频因子。
- `python -m ashare_alpha compute-events --date 2026-03-20`：生成公告事件特征。
- `python -m ashare_alpha generate-signals --date 2026-03-20`：生成研究信号和中文原因。
- `python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20`：运行离线回测。
- `python -m ashare_alpha run-pipeline --date 2026-03-20 --audit-leakage --quality-report --check-security`：运行带审计、质量和安全检查的研究流水线。
- `python -m ashare_alpha build-dashboard`：生成只读研究 dashboard。

## 3. 当前不能做什么

- 不自动下单。
- 不接券商接口。
- 不联网获取真实数据。
- 不保证收益。
- 不构成投资建议。

## 4. 推荐验收命令

```bash
python scripts/dev_check.py
python scripts/smoke_test.py
pytest
ruff check
python -m ashare_alpha run-pipeline --date 2026-03-20 --audit-leakage --quality-report --check-security
python -m ashare_alpha build-dashboard
```

## 5. 关键输出目录

- `outputs/dev/`：开发检查、命令矩阵和 smoke test 报告。
- `outputs/release/`：发布 manifest 与 checklist。
- `outputs/pipelines/`：日频 pipeline 输出。
- `outputs/backtests/`：回测指标、交易和净值曲线。
- `outputs/reports/`：日度报告和回测报告。
- `outputs/models/`：概率模型训练产物。
- `outputs/quality/`：数据质量报告。
- `outputs/audit/`：point-in-time 审计报告。
- `outputs/security/`：安全扫描报告。
- `outputs/experiments/`：实验登记与比较。
- `outputs/sweeps/`：批量实验输出。
- `outputs/walkforward/`：walk-forward 验证输出。
- `outputs/candidates/`：候选配置筛选结果。
- `outputs/dashboard/`：静态 dashboard。

## 6. 下一阶段建议

- 真实数据接入前继续加强数据质量和防泄漏。
- 真实数据 Adapter 先 cache/offline。
- 不直接接实盘。
