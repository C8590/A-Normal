# Changelog

## 0.1.0-mvp - 2026-05-15

### Added

- 数据模型与 `LocalCsvAdapter`：本地 CSV 样例数据加载、校验和标准表结构。
- 配置系统：股票池、交易规则、费用、因子、评分、回测、概率和安全配置。
- 股票池过滤：主板优先，排除 ST / *ST、退市风险、停牌、新股等不适合 MVP 的样本。
- 行情因子：日频低频研究因子计算与 CSV 输出。
- 公告事件：离线公告事件特征、风险分和信号影响。
- 信号生成：规则评分、中文可读原因和买入/观察/阻断分层。
- 回测：T+1、100 股手、价格 tick、涨跌停、费用、滑点、现金和持仓约束。
- 报告：日度报告、回测报告和 CSV / Markdown / JSON 输出。
- 概率模型：基线分箱校准、训练、预测和指标输出。
- pipeline：日频研究流水线，支持质量、安全和 point-in-time 审计选项。
- 数据源注册：本地 CSV 源与离线外部源 profile / mapping。
- point-in-time 审计：数据快照和泄漏检查报告。
- `import-data`：本地 CSV 数据版本化导入。
- `quality-report`：本地数据质量报告。
- adapter contract：离线 fixture 合约校验和转换。
- security：离线模式、安全开关、网络/券商/实盘禁用检查和 secret 状态检查。
- source runtime：离线 source profile 物化流程。
- experiments：研究运行登记、比较和元数据追踪。
- sweeps：批量参数实验与指标表。
- walk-forward：样本外滚动验证。
- candidate selection：候选配置筛选与提升快照。
- dashboard：只读静态研究产物仪表盘。
- dev scripts：开发环境诊断、命令矩阵和 smoke test。
- release：`VERSION`、发布说明、变更日志、发布清单、检查清单和 release check CLI。

### Safety

- 默认 `offline_mode=true`。
- 默认 `allow_network=false`。
- 不连接券商接口。
- 不自动下单。
- 不包含实盘交易能力。

### Known Limitations

- 当前只使用本地 CSV / 离线 fixture。
- 当前不联网获取真实数据。
- 概率模型是基线分箱校准。
- 样例数据是虚构/测试数据。
- 本项目不构成投资建议，不保证收益。
