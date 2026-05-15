from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
USED_SRC_FALLBACK = False
EXPECTED_OUTPUTS = (
    "pipelines",
    "backtests",
    "sweeps",
    "walkforward",
    "experiments",
    "candidates",
    "dashboard",
    "quality",
    "audit",
    "security",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str
    details: dict[str, Any]
    critical: bool = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose the local ashare-alpha-lab development environment.")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format. Default: text.")
    args = parser.parse_args(argv)

    results = run_checks()
    payload = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "cwd": str(Path.cwd()),
        "project_root": str(PROJECT_ROOT),
        "results": [asdict(result) for result in results],
        "failed_count": sum(1 for result in results if result.status == "FAILED"),
        "warning_count": sum(1 for result in results if result.status == "WARNING"),
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_text(payload)
    return 1 if any(result.status == "FAILED" and result.critical for result in results) else 0


def run_checks() -> list[CheckResult]:
    _ensure_src_on_path()
    results = [
        CheckResult(
            name="python",
            status="OK",
            message="Python interpreter detected.",
            details={"executable": sys.executable, "version": sys.version.split()[0], "cwd": str(Path.cwd())},
        ),
        _path_check("src_package", PROJECT_ROOT / "src" / "ashare_alpha", critical=True),
        _import_check(),
        _tool_check("pytest"),
        _tool_check("ruff"),
        _editable_check(),
        _path_check("config_dir", PROJECT_ROOT / "configs" / "ashare_alpha", critical=True),
        _path_check("sample_data_dir", PROJECT_ROOT / "data" / "sample" / "ashare_alpha", critical=True),
    ]
    outputs_root = PROJECT_ROOT / "outputs"
    for name in EXPECTED_OUTPUTS:
        results.append(_path_check(f"outputs/{name}", outputs_root / name, critical=False, warning_only=True))
    return results


def _path_check(name: str, path: Path, critical: bool, warning_only: bool = False) -> CheckResult:
    if path.exists():
        return CheckResult(name=name, status="OK", message=f"Found {path}.", details={"path": str(path)}, critical=critical)
    return CheckResult(
        name=name,
        status="WARNING" if warning_only else "FAILED",
        message=f"Missing {path}.",
        details={"path": str(path)},
        critical=critical and not warning_only,
    )


def _import_check() -> CheckResult:
    spec = importlib.util.find_spec("ashare_alpha")
    if spec is None:
        return CheckResult(
            name="import_ashare_alpha",
            status="FAILED",
            message="ashare_alpha is not importable. Run editable install or set PYTHONPATH=src temporarily.",
            details={"sys_path": sys.path[:5]},
            critical=True,
        )
    return CheckResult(
        name="import_ashare_alpha",
        status="OK",
        message="ashare_alpha is importable.",
        details={"origin": spec.origin, "locations": list(spec.submodule_search_locations or [])},
        critical=True,
    )


def _tool_check(module_name: str) -> CheckResult:
    spec = importlib.util.find_spec(module_name)
    executable = shutil.which(module_name)
    if spec is None and executable is None:
        return CheckResult(
            name=f"tool_{module_name}",
            status="FAILED",
            message=f"{module_name} is not available in this Python environment or PATH.",
            details={},
            critical=True,
        )
    details = {"origin": spec.origin if spec is not None else None, "executable": executable}
    return CheckResult(
        name=f"tool_{module_name}",
        status="OK",
        message=f"{module_name} is available.",
        details=details,
        critical=True,
    )


def _editable_check() -> CheckResult:
    spec = importlib.util.find_spec("ashare_alpha")
    origin = str(spec.origin) if spec and spec.origin else ""
    src_root = str(SRC_ROOT.resolve())
    pip_payload = _pip_show()
    editable = bool(pip_payload.get("editable_project_location")) or (
        origin.startswith(src_root) and not USED_SRC_FALLBACK and pip_payload.get("pip_show_returncode") == "0"
    )
    status = "OK" if editable else "WARNING"
    message = "Package appears to be installed/editable from this checkout." if editable else "Editable install was not detected; using source-tree fallback for diagnostics."
    return CheckResult(
        name="editable_install",
        status=status,
        message=message,
        details={"import_origin": origin, "used_src_fallback": USED_SRC_FALLBACK, **pip_payload},
        critical=False,
    )


def _pip_show() -> dict[str, str]:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "show", "-f", "ashare-alpha-lab"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"pip_show_error": str(exc)}
    payload: dict[str, str] = {"pip_show_returncode": str(completed.returncode)}
    for line in completed.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"location", "editable_project_location", "version", "name"}:
            payload[normalized] = value.strip()
    return payload


def _ensure_src_on_path() -> None:
    global USED_SRC_FALLBACK
    src = str(SRC_ROOT)
    if SRC_ROOT.exists() and src not in sys.path:
        sys.path.insert(0, src)
        USED_SRC_FALLBACK = True


def _print_text(payload: dict[str, Any]) -> None:
    print("ashare-alpha-lab development environment check")
    print(f"Python: {payload['python_executable']}")
    print(f"Version: {str(payload['python_version']).splitlines()[0]}")
    print(f"CWD: {payload['cwd']}")
    print(f"Project root: {payload['project_root']}")
    for result in payload["results"]:
        print(f"[{result['status']}] {result['name']}: {result['message']}")
        details = result.get("details") or {}
        if details:
            compact = json.dumps(details, ensure_ascii=False)
            print(f"  {compact}")
    print(f"Warnings: {payload['warning_count']}")
    print(f"Failures: {payload['failed_count']}")


if __name__ == "__main__":
    raise SystemExit(main())
