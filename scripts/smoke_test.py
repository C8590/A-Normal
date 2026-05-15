from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "outputs" / "dev"
TAIL_CHARS = 4000


@dataclass(frozen=True)
class SmokeCommand:
    name: str
    args: list[str]


@dataclass(frozen=True)
class SmokeResult:
    name: str
    command: list[str]
    status: str
    returncode: int
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str


QUICK_COMMANDS = [
    SmokeCommand("help", ["-m", "ashare_alpha", "--help"]),
    SmokeCommand("show-config", ["-m", "ashare_alpha", "show-config"]),
    SmokeCommand("validate-data", ["-m", "ashare_alpha", "validate-data"]),
    SmokeCommand("build-universe", ["-m", "ashare_alpha", "build-universe", "--date", "2026-03-20"]),
    SmokeCommand("compute-factors", ["-m", "ashare_alpha", "compute-factors", "--date", "2026-03-20"]),
    SmokeCommand("compute-events", ["-m", "ashare_alpha", "compute-events", "--date", "2026-03-20"]),
    SmokeCommand("generate-signals", ["-m", "ashare_alpha", "generate-signals", "--date", "2026-03-20"]),
    SmokeCommand("run-backtest", ["-m", "ashare_alpha", "run-backtest", "--start", "2026-01-05", "--end", "2026-03-20"]),
    SmokeCommand("daily-report", ["-m", "ashare_alpha", "daily-report", "--date", "2026-03-20"]),
    SmokeCommand("build-dashboard", ["-m", "ashare_alpha", "build-dashboard"]),
    SmokeCommand("check-security", ["-m", "ashare_alpha", "check-security"]),
    SmokeCommand("quality-report", ["-m", "ashare_alpha", "quality-report"]),
]

FULL_EXTRA_COMMANDS = [
    SmokeCommand("show-version", ["-m", "ashare_alpha", "show-version"]),
    SmokeCommand("release-check", ["-m", "ashare_alpha", "release-check"]),
    SmokeCommand(
        "run-pipeline-full",
        ["-m", "ashare_alpha", "run-pipeline", "--date", "2026-03-20", "--audit-leakage", "--quality-report", "--check-security"],
    ),
    SmokeCommand("train-probability-model", ["-m", "ashare_alpha", "train-probability-model", "--start", "2026-01-05", "--end", "2026-03-20"]),
    SmokeCommand(
        "predict-probabilities",
        [
            "-m",
            "ashare_alpha",
            "predict-probabilities",
            "--date",
            "2026-03-20",
            "--model-dir",
            "outputs/models/probability_2026-01-05_2026-03-20",
        ],
    ),
    SmokeCommand("run-sweep", ["-m", "ashare_alpha", "run-sweep", "--spec", "configs/ashare_alpha/sweeps/sample_pipeline_thresholds.yaml"]),
    SmokeCommand(
        "run-walkforward",
        ["-m", "ashare_alpha", "run-walkforward", "--spec", "configs/ashare_alpha/walkforward/sample_backtest_walkforward.yaml"],
    ),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local ashare-alpha-lab smoke tests.")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use. Default: current interpreter.")
    parser.add_argument("--quick", action="store_true", default=True, help="Run quick smoke commands. Default.")
    parser.add_argument("--full", action="store_true", help="Run quick commands plus heavier research commands.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format. Default: text.")
    args = parser.parse_args(argv)

    commands = list(QUICK_COMMANDS)
    if args.full:
        commands.extend(FULL_EXTRA_COMMANDS)
    results = run_smoke_commands(args.python, commands)
    report = _build_report(args.python, results, full=args.full)
    save_smoke_report(report)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text(report)
    return 1 if any(result.status == "FAILED" for result in results) else 0


def run_smoke_commands(python_executable: str, commands: list[SmokeCommand]) -> list[SmokeResult]:
    env = _subprocess_env()
    results: list[SmokeResult] = []
    for command in commands:
        full_command = [python_executable, *command.args]
        start = time.perf_counter()
        completed = subprocess.run(
            full_command,
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        duration = time.perf_counter() - start
        results.append(
            SmokeResult(
                name=command.name,
                command=full_command,
                status="SUCCESS" if completed.returncode == 0 else "FAILED",
                returncode=completed.returncode,
                duration_seconds=round(duration, 4),
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
            )
        )
    return results


def save_smoke_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "smoke_test_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / "smoke_test_report.md").write_text(_render_markdown(report), encoding="utf-8")


def _build_report(python_executable: str, results: list[SmokeResult], full: bool) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(),
        "python": python_executable,
        "project_root": str(PROJECT_ROOT),
        "mode": "full" if full else "quick",
        "total_count": len(results),
        "success_count": sum(1 for result in results if result.status == "SUCCESS"),
        "failed_count": sum(1 for result in results if result.status == "FAILED"),
        "results": [asdict(result) for result in results],
        "safety_note": "Smoke tests run offline research commands only; they do not place orders or connect to brokers.",
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Smoke Test Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- python: {report['python']}",
        f"- mode: {report['mode']}",
        f"- success / failed: {report['success_count']} / {report['failed_count']}",
        "",
        "| name | status | returncode | duration_seconds |",
        "| --- | --- | ---: | ---: |",
    ]
    for result in report["results"]:
        lines.append(f"| {result['name']} | {result['status']} | {result['returncode']} | {result['duration_seconds']} |")
    lines.extend(
        [
            "",
            "## Failed Command Tails",
        ]
    )
    failed = [result for result in report["results"] if result["status"] == "FAILED"]
    if not failed:
        lines.append("- None")
    for result in failed:
        lines.extend(
            [
                f"### {result['name']}",
                "",
                "stdout tail:",
                "```text",
                result["stdout_tail"],
                "```",
                "stderr tail:",
                "```text",
                result["stderr_tail"],
                "```",
            ]
        )
    lines.extend(
        [
            "",
            "## Safety",
            "- Offline smoke tests only.",
            "- No broker connection.",
            "- No live orders.",
            "- No external API calls are introduced by this script.",
            "",
        ]
    )
    return "\n".join(lines)


def _print_text(report: dict[str, Any]) -> None:
    print("ashare-alpha-lab smoke test")
    print(f"Mode: {report['mode']}")
    print(f"Python: {report['python']}")
    print(f"Success / Failed: {report['success_count']} / {report['failed_count']}")
    for result in report["results"]:
        print(f"[{result['status']}] {result['name']} rc={result['returncode']} duration={result['duration_seconds']}s")
    print(f"Report: {REPORT_DIR / 'smoke_test_report.json'}")


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(PROJECT_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not existing else f"{src}{os.pathsep}{existing}"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _tail(value: str) -> str:
    return value[-TAIL_CHARS:] if len(value) > TAIL_CHARS else value


if __name__ == "__main__":
    raise SystemExit(main())
