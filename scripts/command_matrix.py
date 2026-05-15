from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "COMMAND_MATRIX.md"
JSON_PATH = PROJECT_ROOT / "outputs" / "dev" / "command_matrix.json"


COMMAND_MATRIX: list[dict[str, Any]] = [
    {"category": "Release", "command": "show-version", "purpose": "显示当前 MVP 版本、包路径和 Python 版本。", "required_args": "-", "common_example": "python -m ashare_alpha show-version", "output_location": "stdout", "safety_note": "只读版本信息，不联网。"},
    {"category": "Release", "command": "release-check", "purpose": "运行本地发布检查并生成 release manifest/checklist。", "required_args": "-", "common_example": "python -m ashare_alpha release-check", "output_location": "outputs/release/...", "safety_note": "只做本地文件与安全边界检查，不运行重型回测。"},
    {"category": "基础", "command": "show-config", "purpose": "加载并打印项目配置。", "required_args": "-", "common_example": "python -m ashare_alpha show-config", "output_location": "stdout", "safety_note": "只读配置，不联网。"},
    {"category": "基础", "command": "validate-data", "purpose": "校验本地 CSV 样本数据。", "required_args": "-", "common_example": "python -m ashare_alpha validate-data", "output_location": "stdout", "safety_note": "只读本地数据，不联网。"},
    {"category": "数据源", "command": "list-data-sources", "purpose": "列出注册的数据源元数据。", "required_args": "-", "common_example": "python -m ashare_alpha list-data-sources", "output_location": "stdout", "safety_note": "不会调用外部数据源。"},
    {"category": "数据源", "command": "inspect-data-source", "purpose": "查看单个数据源元数据。", "required_args": "--name", "common_example": "python -m ashare_alpha inspect-data-source --name local_csv", "output_location": "stdout", "safety_note": "不会调用外部数据源。"},
    {"category": "数据源", "command": "validate-adapter-contract", "purpose": "校验外部适配器离线 fixture 合约。", "required_args": "--source-name --fixture-dir", "common_example": "python -m ashare_alpha validate-adapter-contract --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like", "output_location": "stdout", "safety_note": "只读离线 fixture。"},
    {"category": "数据源", "command": "convert-source-fixture", "purpose": "将离线 fixture 转成标准本地表。", "required_args": "--source-name --fixture-dir --output-dir", "common_example": "python -m ashare_alpha convert-source-fixture --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like --output-dir data/imports/tushare_like/contract_sample", "output_location": "data/imports/...", "safety_note": "不调用供应商 API。"},
    {"category": "数据源", "command": "cache-source-fixture", "purpose": "将离线 fixture 复制到外部 raw cache。", "required_args": "--source-name --fixture-dir", "common_example": "python -m ashare_alpha cache-source-fixture --source-name tushare_like --fixture-dir tests/fixtures/external_sources/tushare_like --cache-version contract_sample", "output_location": "data/cache/external/...", "safety_note": "只读写本地文件，不联网。"},
    {"category": "数据源", "command": "list-caches", "purpose": "列出外部缓存版本。", "required_args": "-", "common_example": "python -m ashare_alpha list-caches", "output_location": "stdout", "safety_note": "只读本地 cache manifest。"},
    {"category": "数据源", "command": "inspect-cache", "purpose": "查看单个外部缓存 manifest。", "required_args": "--source-name --cache-version", "common_example": "python -m ashare_alpha inspect-cache --source-name tushare_like --cache-version contract_sample", "output_location": "stdout", "safety_note": "只读本地 cache manifest。"},
    {"category": "数据源", "command": "materialize-cache", "purpose": "将 raw cache 转成标准四表。", "required_args": "--source-name --cache-version", "common_example": "python -m ashare_alpha materialize-cache --source-name tushare_like --cache-version contract_sample", "output_location": "data/cache/external/.../normalized", "safety_note": "使用本地 mapping，不调用 API。"},
    {"category": "数据源", "command": "list-source-profiles", "purpose": "列出外部源运行 profile。", "required_args": "-", "common_example": "python -m ashare_alpha list-source-profiles", "output_location": "stdout", "safety_note": "只读配置。"},
    {"category": "数据源", "command": "inspect-source-profile", "purpose": "检查一个 source profile 是否可离线运行。", "required_args": "--profile", "common_example": "python -m ashare_alpha inspect-source-profile --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml", "output_location": "stdout", "safety_note": "遵守 offline security policy。"},
    {"category": "数据源", "command": "materialize-source", "purpose": "物化离线 source profile 数据。", "required_args": "--profile --data-version", "common_example": "python -m ashare_alpha materialize-source --profile configs/ashare_alpha/source_profiles/tushare_like_offline.yaml --data-version contract_sample", "output_location": "data/materialized/...", "safety_note": "只使用离线 fixture/cache。"},
    {"category": "导入与质量", "command": "import-data", "purpose": "导入标准 CSV 到版本化目录。", "required_args": "--source-name --source-data-dir", "common_example": "python -m ashare_alpha import-data --source-name local_csv --source-data-dir data/sample/ashare_alpha", "output_location": "data/imports/...", "safety_note": "本地文件操作，不联网。"},
    {"category": "导入与质量", "command": "list-imports", "purpose": "列出版本化导入。", "required_args": "-", "common_example": "python -m ashare_alpha list-imports", "output_location": "stdout", "safety_note": "只读本地索引。"},
    {"category": "导入与质量", "command": "inspect-import", "purpose": "查看一个导入版本。", "required_args": "--source-name --data-version", "common_example": "python -m ashare_alpha inspect-import --source-name local_csv --data-version sample_v1", "output_location": "stdout", "safety_note": "只读本地 manifest。"},
    {"category": "导入与质量", "command": "quality-report", "purpose": "生成数据质量报告。", "required_args": "-", "common_example": "python -m ashare_alpha quality-report", "output_location": "outputs/quality/...", "safety_note": "只检查本地数据。"},
    {"category": "导入与质量", "command": "audit-leakage", "purpose": "运行 point-in-time 泄漏审计。", "required_args": "--date 或 --start --end", "common_example": "python -m ashare_alpha audit-leakage --date 2026-03-20", "output_location": "outputs/audit/...", "safety_note": "不改变研究逻辑。"},
    {"category": "研究", "command": "build-universe", "purpose": "构建当日研究股票池。", "required_args": "--date", "common_example": "python -m ashare_alpha build-universe --date 2026-03-20", "output_location": "outputs/universe/...", "safety_note": "只生成研究文件。"},
    {"category": "研究", "command": "compute-factors", "purpose": "计算日频因子。", "required_args": "--date", "common_example": "python -m ashare_alpha compute-factors --date 2026-03-20", "output_location": "outputs/factors/...", "safety_note": "不联网。"},
    {"category": "研究", "command": "compute-events", "purpose": "计算公告事件特征。", "required_args": "--date", "common_example": "python -m ashare_alpha compute-events --date 2026-03-20", "output_location": "outputs/events/...", "safety_note": "只用本地公告样本。"},
    {"category": "研究", "command": "generate-signals", "purpose": "生成研究信号。", "required_args": "--date", "common_example": "python -m ashare_alpha generate-signals --date 2026-03-20", "output_location": "outputs/signals/...", "safety_note": "信号仅用于研究，不下单。"},
    {"category": "研究", "command": "run-pipeline", "purpose": "运行完整日频研究流水线。", "required_args": "--date", "common_example": "python -m ashare_alpha run-pipeline --date 2026-03-20", "output_location": "outputs/pipelines/...", "safety_note": "不连接券商，不下单。"},
    {"category": "回测与报告", "command": "run-backtest", "purpose": "运行本地研究回测。", "required_args": "--start --end", "common_example": "python -m ashare_alpha run-backtest --start 2026-01-05 --end 2026-03-20", "output_location": "outputs/backtests/...", "safety_note": "模拟回测，不实盘。"},
    {"category": "回测与报告", "command": "daily-report", "purpose": "生成日度研究报告。", "required_args": "--date", "common_example": "python -m ashare_alpha daily-report --date 2026-03-20", "output_location": "outputs/reports/...", "safety_note": "研究报告，不构成投资建议。"},
    {"category": "回测与报告", "command": "backtest-report", "purpose": "渲染回测报告。", "required_args": "--backtest-dir", "common_example": "python -m ashare_alpha backtest-report --backtest-dir outputs/backtests/backtest_2026-01-05_2026-03-20", "output_location": "outputs/reports/...", "safety_note": "只读回测产物。"},
    {"category": "概率", "command": "train-probability-model", "purpose": "训练本地概率模型。", "required_args": "--start --end", "common_example": "python -m ashare_alpha train-probability-model --start 2026-01-05 --end 2026-03-20", "output_location": "outputs/models/...", "safety_note": "只用本地样本，不调用 API。"},
    {"category": "概率", "command": "predict-probabilities", "purpose": "用本地模型生成概率预测。", "required_args": "--date --model-dir", "common_example": "python -m ashare_alpha predict-probabilities --date 2026-03-20 --model-dir outputs/models/probability_2026-01-05_2026-03-20", "output_location": "outputs/probability/...", "safety_note": "预测仅用于研究。"},
    {"category": "实验", "command": "record-experiment", "purpose": "登记已完成研究运行。", "required_args": "--command --output-dir", "common_example": "python -m ashare_alpha record-experiment --command run-pipeline --output-dir outputs/pipelines/pipeline_2026-03-20", "output_location": "outputs/experiments/...", "safety_note": "只记录元数据。"},
    {"category": "实验", "command": "list-experiments", "purpose": "列出实验记录。", "required_args": "-", "common_example": "python -m ashare_alpha list-experiments", "output_location": "stdout", "safety_note": "只读实验记录。"},
    {"category": "实验", "command": "show-experiment", "purpose": "查看实验记录。", "required_args": "--id", "common_example": "python -m ashare_alpha show-experiment --id EXP_ID", "output_location": "stdout", "safety_note": "只读实验记录。"},
    {"category": "实验", "command": "compare-experiments", "purpose": "比较两个实验指标。", "required_args": "--baseline --target", "common_example": "python -m ashare_alpha compare-experiments --baseline EXP_A --target EXP_B", "output_location": "outputs/experiments/comparisons/...", "safety_note": "研究比较，不保证收益。"},
    {"category": "Sweep / Walk-forward / Candidates", "command": "run-sweep", "purpose": "运行批量配置实验。", "required_args": "--spec", "common_example": "python -m ashare_alpha run-sweep --spec configs/ashare_alpha/sweeps/sample_pipeline_thresholds.yaml", "output_location": "outputs/sweeps/...", "safety_note": "不启用实盘能力。"},
    {"category": "Sweep / Walk-forward / Candidates", "command": "show-sweep", "purpose": "查看 sweep 结果。", "required_args": "--path", "common_example": "python -m ashare_alpha show-sweep --path outputs/sweeps/SWEEP_ID/sweep_result.json", "output_location": "stdout", "safety_note": "只读结果。"},
    {"category": "Sweep / Walk-forward / Candidates", "command": "run-walkforward", "purpose": "运行样本外 walk-forward 验证。", "required_args": "--spec", "common_example": "python -m ashare_alpha run-walkforward --spec configs/ashare_alpha/walkforward/sample_backtest_walkforward.yaml", "output_location": "outputs/walkforward/...", "safety_note": "研究验证，不实盘。"},
    {"category": "Sweep / Walk-forward / Candidates", "command": "show-walkforward", "purpose": "查看 walk-forward 结果。", "required_args": "--path", "common_example": "python -m ashare_alpha show-walkforward --path outputs/walkforward/WF_ID/walkforward_result.json", "output_location": "stdout", "safety_note": "只读结果。"},
    {"category": "Sweep / Walk-forward / Candidates", "command": "select-candidates", "purpose": "评估研究候选配置。", "required_args": "--source", "common_example": "python -m ashare_alpha select-candidates --source outputs/walkforward/WF_ID/walkforward_result.json", "output_location": "outputs/candidates/...", "safety_note": "研究筛选，不是投资建议。"},
    {"category": "Sweep / Walk-forward / Candidates", "command": "promote-candidate-config", "purpose": "复制候选配置快照。", "required_args": "--selection --candidate-id --promoted-name", "common_example": "python -m ashare_alpha promote-candidate-config --selection outputs/candidates/selection_ID/candidate_selection.json --candidate-id CANDIDATE_ID --promoted-name test_candidate", "output_location": "outputs/candidate_configs/...", "safety_note": "不覆盖 base config，不下单。"},
    {"category": "Dashboard", "command": "build-dashboard", "purpose": "构建静态研究 Dashboard。", "required_args": "-", "common_example": "python -m ashare_alpha build-dashboard", "output_location": "outputs/dashboard/...", "safety_note": "只读扫描研究产物。"},
    {"category": "Dashboard", "command": "show-dashboard", "purpose": "查看 Dashboard 摘要。", "required_args": "--path", "common_example": "python -m ashare_alpha show-dashboard --path outputs/dashboard/DASHBOARD_ID", "output_location": "stdout", "safety_note": "只读 Dashboard 文件。"},
    {"category": "安全", "command": "check-security", "purpose": "扫描配置安全风险。", "required_args": "-", "common_example": "python -m ashare_alpha check-security", "output_location": "outputs/security/...", "safety_note": "不读取或输出密钥。"},
    {"category": "安全", "command": "check-secrets", "purpose": "检查环境变量密钥状态。", "required_args": "-", "common_example": "python -m ashare_alpha check-secrets", "output_location": "stdout", "safety_note": "只输出是否设置，不输出 secret 值。"},
    {"category": "安全", "command": "show-network-policy", "purpose": "显示网络和券商连接策略。", "required_args": "-", "common_example": "python -m ashare_alpha show-network-policy", "output_location": "stdout", "safety_note": "只读安全配置。"},
]


def main() -> int:
    payload = {
        "generated_at": datetime.now().isoformat(),
        "command_count": len(COMMAND_MATRIX),
        "commands": COMMAND_MATRIX,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(render_markdown(payload), encoding="utf-8")
    print(f"Wrote {JSON_PATH}")
    print(f"Wrote {DOC_PATH}")
    return 0


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Command Matrix",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- command_count: {payload['command_count']}",
        "",
        "This matrix documents local offline research commands. It does not introduce external API calls, broker integration, web scraping, or live trading.",
        "",
    ]
    categories: list[str] = []
    for row in payload["commands"]:
        if row["category"] not in categories:
            categories.append(row["category"])
    for category in categories:
        lines.extend(
            [
                f"## {category}",
                "",
                "| command | purpose | required args | common example | output location | safety note |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in payload["commands"]:
            if row["category"] != category:
                continue
            lines.append(
                "| "
                f"{_escape(row['command'])} | "
                f"{_escape(row['purpose'])} | "
                f"{_escape(row['required_args'])} | "
                f"`{_escape(row['common_example'])}` | "
                f"{_escape(row['output_location'])} | "
                f"{_escape(row['safety_note'])} |"
            )
        lines.append("")
    lines.extend(
        [
            "## Safety Boundary",
            "",
            "- This project is for research, backtesting, signal generation, and reporting only.",
            "- It does not guarantee future returns.",
            "- It does not connect to brokers.",
            "- It does not place live orders.",
            "",
        ]
    )
    return "\n".join(lines)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
