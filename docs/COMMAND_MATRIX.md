# Command Matrix

- generated_at: 2026-05-16T23:19:58.145363
- command_count: 56

This matrix documents local offline research commands. It does not introduce external API calls, broker integration, web scraping, or live trading.

## Release

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| evaluate-research-gates | Evaluate research quality gates for local artifacts. | --source | `python -m ashare_alpha evaluate-research-gates --source outputs/pipelines/pipeline_2026-03-20/manifest.json` | outputs/gates/... | Local quality control only; not investment advice, no external API, no broker connection, and no live orders. |
| show-version | 显示当前 MVP 版本、包路径和 Python 版本。 | - | `python -m ashare_alpha show-version` | stdout | 只读版本信息，不联网。 |
| release-check | 运行本地发布检查并生成 release manifest/checklist。 | - | `python -m ashare_alpha release-check` | outputs/release/... | 只做本地文件与安全边界检查，不运行重型回测。 |

## 基础

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| show-config | 加载并打印项目配置。 | - | `python -m ashare_alpha show-config` | stdout | 只读配置，不联网。 |
| validate-data | 校验本地 CSV 样本数据。 | - | `python -m ashare_alpha validate-data` | stdout | 只读本地数据，不联网。 |

## Basic

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| inspect-realism-data | Inspect optional A-share data realism CSV files. | - | `python -m ashare_alpha inspect-realism-data` | stdout | Reads only local optional CSV files; no network or broker access. |
| check-trading-calendar | Summarize open dates from optional trade_calendar.csv. | --start --end | `python -m ashare_alpha check-trading-calendar --start 2026-01-01 --end 2026-03-31` | stdout | Reads only local calendar data and does not change research logic. |

## 数据源

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| list-data-sources | 列出注册的数据源元数据。 | - | `python -m ashare_alpha list-data-sources` | stdout | 不会调用外部数据源。 |
| inspect-data-source | 查看单个数据源元数据。 | --name | `python -m ashare_alpha inspect-data-source --name local_csv` | stdout | 不会调用外部数据源。 |
| validate-adapter-contract | 校验外部适配器离线 fixture 合约。 | --source-name --fixture-dir | `python -m ashare_alpha validate-adapter-contract --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like` | stdout | 只读离线 fixture。 |
| convert-source-fixture | 将离线 fixture 转成标准本地表。 | --source-name --fixture-dir --output-dir | `python -m ashare_alpha convert-source-fixture --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like --output-dir data/imports/tushare_like/contract_sample` | data/imports/... | 不调用供应商 API。 |
| cache-source-fixture | 将离线 fixture 复制到外部 raw cache。 | --source-name --fixture-dir | `python -m ashare_alpha cache-source-fixture --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like --cache-version contract_sample` | data/cache/external/... | 只读写本地文件，不联网。 |
| list-caches | 列出外部缓存版本。 | - | `python -m ashare_alpha list-caches` | stdout | 只读本地 cache manifest。 |
| inspect-cache | 查看单个外部缓存 manifest。 | --source-name --cache-version | `python -m ashare_alpha inspect-cache --source-name tushare_like --cache-version contract_sample` | stdout | 只读本地 cache manifest。 |
| materialize-cache | 将 raw cache 转成标准四表。 | --source-name --cache-version | `python -m ashare_alpha materialize-cache --source-name tushare_like --cache-version contract_sample` | data/cache/external/.../normalized | 使用本地 mapping，不调用 API。 |
| list-source-profiles | 列出外部源运行 profile。 | - | `python -m ashare_alpha list-source-profiles` | stdout | 只读配置。 |
| inspect-source-profile | 检查一个 source profile 是否可离线运行。 | --profile | `python -m ashare_alpha inspect-source-profile --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml` | stdout | 遵守 offline security policy。 |
| materialize-source | 物化离线 source profile 数据。 | --profile --data-version | `python -m ashare_alpha materialize-source --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml --data-version contract_sample` | data/materialized/... | 只使用离线 fixture/cache。 |
| run-realdata-offline-drill | 运行 v0.3 离线真实数据演练链路。 | --spec | `python -m ashare_alpha run-realdata-offline-drill --spec configs/ashare_alpha/realdata/tushare_like_offline_drill.yaml` | outputs/realdata/... | 只使用离线 fixture/cache，不调用外部 API、不接券商、不下单。 |
| show-realdata-drill | 查看已保存的离线真实数据演练结果。 | --path | `python -m ashare_alpha show-realdata-drill --path outputs/realdata/DRILL_ID/drill_result.json` | stdout | 只读展示本地报告。 |

## 导入与质量

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| import-data | 导入标准 CSV 到版本化目录。 | --source-name --source-data-dir | `python -m ashare_alpha import-data --source-name local_csv --source-data-dir data/sample/ashare_alpha` | data/imports/... | 本地文件操作，不联网。 |
| list-imports | 列出版本化导入。 | - | `python -m ashare_alpha list-imports` | stdout | 只读本地索引。 |
| inspect-import | 查看一个导入版本。 | --source-name --data-version | `python -m ashare_alpha inspect-import --source-name local_csv --data-version sample_v1` | stdout | 只读本地 manifest。 |
| quality-report | 生成数据质量报告。 | - | `python -m ashare_alpha quality-report` | outputs/quality/... | 只检查本地数据。 |
| build-adjusted-bars | 生成可审计的 raw/qfq/hfq 复权行情。 | --date 或 --start --end | `python -m ashare_alpha build-adjusted-bars --date 2026-03-20 --adj-type qfq` | outputs/adjusted/... | 只读本地 CSV，不改变 pipeline 默认逻辑，不联网、不接券商、不下单。 |
| audit-leakage | 运行 point-in-time 泄漏审计。 | --date 或 --start --end | `python -m ashare_alpha audit-leakage --date 2026-03-20` | outputs/audit/... | 不改变研究逻辑。 |

## 研究

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| build-universe | 构建当日研究股票池。 | --date | `python -m ashare_alpha build-universe --date 2026-03-20` | outputs/universe/... | 只生成研究文件。 |
| compute-factors | 计算日频因子，可显式选择 raw/qfq/hfq 价格源。 | --date | `python -m ashare_alpha compute-factors --date 2026-03-20 --price-source qfq` | outputs/factors/... | 默认 raw；qfq/hfq 只读取本地复权数据，不改变 pipeline/backtest 默认逻辑，不联网。 |
| compare-factor-price-sources | 比较两个 factor price_source 版本的差异。 | --date | `python -m ashare_alpha compare-factor-price-sources --date 2026-03-20 --left raw --right qfq` | outputs/factors/compare_... | 仅生成研究比较报告，不构成投资建议，不下单。 |
| compute-events | 计算公告事件特征。 | --date | `python -m ashare_alpha compute-events --date 2026-03-20` | outputs/events/... | 只用本地公告样本。 |
| generate-signals | 生成研究信号。 | --date | `python -m ashare_alpha generate-signals --date 2026-03-20` | outputs/signals/... | 信号仅用于研究，不下单。 |
| run-pipeline | 运行完整日频研究流水线。 | --date | `python -m ashare_alpha run-pipeline --date 2026-03-20` | outputs/pipelines/... | 不连接券商，不下单。 |

## 回测与报告

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| run-backtest | Run local research backtest with optional raw/qfq/hfq valuation price source. | --start --end | `python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20 --price-source qfq` | outputs/backtests/... | Default remains raw; execution constraints use raw daily bars; no broker connection or live orders. |
| compare-backtest-price-sources | Compare two backtest valuation price sources such as raw vs qfq. | --start --end | `python -m ashare_alpha compare-backtest-price-sources --start 2026-01-05 --end 2026-03-20 --left raw --right qfq` | outputs/backtests/compare_... | Research comparison only; execution constraints stay raw; no automatic orders. |
| adjusted-research-report | Build a unified raw/qfq/hfq factor and backtest research comparison report. | --date --start --end | `python -m ashare_alpha adjusted-research-report --date 2026-03-20 --start 2026-01-05 --end 2026-03-20` | outputs/adjusted_research/... | Research valuation comparison only; execution constraints remain raw; no external API, broker connection, or live orders. |
| daily-report | 生成日度研究报告。 | --date | `python -m ashare_alpha daily-report --date 2026-03-20` | outputs/reports/... | 研究报告，不构成投资建议。 |
| backtest-report | 渲染回测报告。 | --backtest-dir | `python -m ashare_alpha backtest-report --backtest-dir outputs/backtests/backtest_2026-01-05_2026-03-20` | outputs/reports/... | 只读回测产物。 |

## 概率

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| train-probability-model | 训练本地概率模型。 | --start --end | `python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20` | outputs/models/... | 只用本地样本，不调用 API。 |
| predict-probabilities | 用本地模型生成概率预测。 | --date --model-dir | `python -m ashare_alpha predict-probabilities --date 2026-03-20 --model-dir outputs/models/probability_2026-01-05_2026-03-20` | outputs/probability/... | 预测仅用于研究。 |

## 实验

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| record-experiment | 登记已完成研究运行。 | --command --output-dir | `python -m ashare_alpha record-experiment --command run-pipeline --output-dir outputs/pipelines/pipeline_2026-03-20` | outputs/experiments/... | 只记录元数据。 |
| list-experiments | 列出实验记录。 | - | `python -m ashare_alpha list-experiments` | stdout | 只读实验记录。 |
| show-experiment | 查看实验记录。 | --id | `python -m ashare_alpha show-experiment --id EXP_ID` | stdout | 只读实验记录。 |
| compare-experiments | 比较两个实验指标。 | --baseline --target | `python -m ashare_alpha compare-experiments --baseline EXP_A --target EXP_B` | outputs/experiments/comparisons/... | 研究比较，不保证收益。 |

## Sweep / Walk-forward / Candidates

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| run-sweep | 运行批量配置实验。 | --spec | `python -m ashare_alpha run-sweep --spec configs/ashare_alpha/sweeps/sample_pipeline_thresholds.yaml` | outputs/sweeps/... | 不启用实盘能力。 |
| show-sweep | 查看 sweep 结果。 | --path | `python -m ashare_alpha show-sweep --path outputs/sweeps/SWEEP_ID/sweep_result.json` | stdout | 只读结果。 |
| run-walkforward | 运行样本外 walk-forward 验证。 | --spec | `python -m ashare_alpha run-walkforward --spec configs/ashare_alpha/walkforward/sample_backtest_walkforward.yaml` | outputs/walkforward/... | 研究验证，不实盘。 |
| show-walkforward | 查看 walk-forward 结果。 | --path | `python -m ashare_alpha show-walkforward --path outputs/walkforward/WF_ID/walkforward_result.json` | stdout | 只读结果。 |
| select-candidates | 评估研究候选配置。 | --source | `python -m ashare_alpha select-candidates --source outputs/walkforward/WF_ID/walkforward_result.json` | outputs/candidates/... | 研究筛选，不是投资建议。 |
| promote-candidate-config | 复制候选配置快照。 | --selection --candidate-id --promoted-name | `python -m ashare_alpha promote-candidate-config --selection outputs/candidates/selection_ID/candidate_selection.json --candidate-id CANDIDATE_ID --promoted-name test_candidate` | outputs/candidate_configs/... | 不覆盖 base config，不下单。 |

## Dashboard

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| build-dashboard | 构建静态研究 Dashboard。 | - | `python -m ashare_alpha build-dashboard` | outputs/dashboard/... | 只读扫描研究产物。 |
| show-dashboard | 查看 Dashboard 摘要。 | --path | `python -m ashare_alpha show-dashboard --path outputs/dashboard/DASHBOARD_ID` | stdout | 只读 Dashboard 文件。 |

## Frontend

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| build-frontend | 生成本地只读静态 Research Frontend。 | - | `python -m ashare_alpha build-frontend --update-latest` | outputs/frontend/... | 只读扫描 outputs，不联网，不执行命令，不修改研究逻辑。 |
| serve-frontend | 用 Python http.server 服务已生成的静态前端目录。 | --dir | `python -m ashare_alpha serve-frontend --dir outputs/frontend/latest` | local static server | 只服务静态文件，不提供 API，不接券商接口。 |

## 安全

| command | purpose | required args | common example | output location | safety note |
| --- | --- | --- | --- | --- | --- |
| check-security | 扫描配置安全风险。 | - | `python -m ashare_alpha check-security` | outputs/security/... | 不读取或输出密钥。 |
| check-secrets | 检查环境变量密钥状态。 | - | `python -m ashare_alpha check-secrets` | stdout | 只输出是否设置，不输出 secret 值。 |
| show-network-policy | 显示网络和券商连接策略。 | - | `python -m ashare_alpha show-network-policy` | stdout | 只读安全配置。 |

## Safety Boundary

- This project is for research, backtesting, signal generation, and reporting only.
- It does not guarantee future returns.
- It does not connect to brokers.
- It does not place live orders.
