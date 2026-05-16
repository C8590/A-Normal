# Adjusted Price Spec

## 1. 为什么需要复权行情

个股分红、送转、配股等公司行为会让原始价格序列出现跳变。`adjusted_daily_bar` 生成层把 `daily_bar` 与本地 `adjustment_factor.csv` 结合，输出 raw/qfq/hfq 三类可审计行情，供后续研究任务计算 adjusted return、momentum、volatility 和质量检查。

本阶段只生成复权行情文件，不改变现有 `factor_daily`、`run-backtest`、`run-pipeline`、概率模型或策略默认逻辑。

## 2. raw / qfq / hfq 定义

- `raw`: 不使用复权因子，复权 OHLC 等于原始 OHLC，`adjustment_ratio=1.0`，`is_adjusted=false`。
- `qfq`: 使用样本区间内最后一个可用 `adj_factor` 作为 `base_adj_factor`，`adjustment_ratio=adj_factor_t/base_adj_factor`，生成近似前复权价格。
- `hfq`: 使用样本区间内第一个可用 `adj_factor` 作为 `base_adj_factor`，`adjustment_ratio=adj_factor_t/base_adj_factor`，生成近似后复权价格。

## 3. adjustment_factor 字段

`adjustment_factor.csv` 由本地样本或离线导入流程提供，核心字段包括：

- `ts_code`: 股票代码。
- `trade_date`: 因子日期。
- `adj_factor`: 大于 0 的复权因子。
- `adj_type`: `qfq`、`hfq`、`raw` 或 `none`。本生成层支持输出 `raw`、`qfq`、`hfq`。
- `available_at`: 因子对研究流程可见的时间。缺失时会在复权报告中给出 warning。

## 4. build-adjusted-bars 用法

```bash
python -m ashare_alpha build-adjusted-bars --date 2026-03-20 --adj-type qfq
python -m ashare_alpha build-adjusted-bars --start 2026-01-05 --end 2026-03-20 --adj-type qfq
python -m ashare_alpha build-adjusted-bars --start 2026-01-05 --end 2026-03-20 --adj-type raw
```

参数：

- `--data-dir PATH`: 默认 `data/sample/ashare_alpha`。
- `--date YYYY-MM-DD`: 单日生成。
- `--start YYYY-MM-DD --end YYYY-MM-DD`: 区间生成。
- `--adj-type qfq/hfq/raw`: 默认 `qfq`。
- `--output-dir PATH`: 可选输出目录。
- `--format text/json`: 默认 `text`。

必须提供 `--date` 或同时提供 `--start/--end`，两种模式不能混用。

## 5. 输出文件

默认写入 `outputs/adjusted/adjusted_YYYYMMDD_HHMMSS/`：

- `adjusted_daily_bar.csv`
- `adjusted_summary.json`
- `adjusted_validation.json`
- `adjusted_report.md`

## 6. 质量 flags

- `MISSING_ADJ_FACTOR`: 非 raw 模式缺少同日复权因子。
- `INVALID_ADJ_FACTOR`: 复权因子、基准因子或调整比例非法。
- `FALLBACK_ADJ_TYPE`: 请求的 adj_type 缺失，使用 qfq 因子回退。
- `MISSING_BASE_FACTOR`: 样本区间内缺少基准因子。
- `INVALID_RAW_PRICE`: 原始 OHLC 关系异常。
- `INVALID_ADJUSTED_PRICE`: 复权 OHLC 关系异常。
- `CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE`: 公司行为附近未发现因子变化。
- `FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION`: 因子变化附近未发现公司行为。
- `STALE_FACTOR`: 存在历史因子，但缺少同日因子。
- `MISSING_FACTOR_AVAILABLE_AT`: 复权因子缺少可见时间。

## 7. 公司行为 mismatch 检查

第一版使用简单提示规则：

- 如果某日 `adj_factor` 相比前一日变化超过 0.1%，但前后 3 个自然日没有 `corporate_action`，标记 `FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION`。
- 如果公司行为 `ex_date` 或 `action_date` 前后 3 个自然日没有因子变化，标记 `CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE`。

这些 mismatch 只作为质量提示，不代表公司行为数据或复权因子一定错误。

## 8. 研究边界

本复权层基于输入的 `adjustment_factor` 生成标准化研究价格，不直接用 `corporate_action` 重构复权因子，不代表交易所官方复权。

本系统只用于研究、回测、信号生成和报告，不构成投资建议，不保证收益，不接券商接口，不自动下单。
