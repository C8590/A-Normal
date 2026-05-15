# Development Setup

This project is a local, offline research system. Development commands should run against the `ashare_alpha` package under `src/ashare_alpha`.

## 1. Python Environment

Recommended on Windows:

```powershell
py -3.12 --version
```

Use the same interpreter for install, diagnostics, tests, and smoke checks. Avoid mixing a bare `python` from one environment with `py -3.12` from another.

## 2. Editable Install

Install the package from the repository root:

```powershell
py -3.12 -m pip install -e .
```

For development tools:

```powershell
py -3.12 -m pip install -e ".[dev]"
```

Verify:

```powershell
py -3.12 -m ashare_alpha --help
ashare-alpha --help
```

The console script `ashare-alpha` is available after editable install. The most explicit form remains `py -3.12 -m ashare_alpha`.

## 3. Temporary PYTHONPATH Fallback

If editable install has not been run yet, this temporary fallback works from the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m ashare_alpha --help
```

This is only a local workaround. Prefer editable install for regular development.

## 4. Environment Diagnostics

```powershell
py -3.12 scripts/dev_check.py
py -3.12 scripts/dev_check.py --format json
```

The diagnostic checks Python path, package importability, package location, pytest, ruff, config directories, sample data, and expected output directories.

## 5. Tests And Lint

```powershell
py -3.12 -m pytest
py -3.12 -m ruff check
```

If Windows reports cache permission warnings, rerun pytest with a local temporary directory:

```powershell
$env:TMP = "$PWD\.tmp"
$env:TEMP = "$PWD\.tmp"
py -3.12 -m pytest -p no:cacheprovider --basetemp .tmp\pytest
```

## 6. Smoke Test

Lightweight local smoke test:

```powershell
py -3.12 scripts/smoke_test.py
```

Full smoke test:

```powershell
py -3.12 scripts/smoke_test.py --full
```

Reports are written to:

- `outputs/dev/smoke_test_report.json`
- `outputs/dev/smoke_test_report.md`

## 7. PowerShell Helpers

```powershell
.\scripts\install_dev.ps1
.\scripts\smoke_test.ps1
.\scripts\smoke_test.ps1 -Full
.\scripts\smoke_test.ps1 -Json
```

## 8. Common Problems

Bare `python` points to the wrong interpreter:

Use `py -3.12` consistently, then reinstall with `py -3.12 -m pip install -e ".[dev]"`.

`pip` environment is damaged:

Check the interpreter first with `py -3.12 --version`, then run `py -3.12 -m pip --version`. If pip itself fails, repair that Python installation before installing this project.

`pytest` cannot find `ashare_alpha`:

Run editable install or set `$env:PYTHONPATH = "src"` temporarily from the repository root.

Editable install succeeds but `python -m ashare_alpha` or `python -c "import ashare_alpha"` still fails:

Some damaged or non-standard global Python environments may install the editable package metadata but fail to process the generated `.pth` file on interpreter startup. First verify with a clean virtual environment:

```powershell
python -m venv .tmp\venv-editable-check
.tmp\venv-editable-check\Scripts\python -m pip install -e .
.tmp\venv-editable-check\Scripts\python -c "import ashare_alpha; print(ashare_alpha.__file__)"
.tmp\venv-editable-check\Scripts\python -m ashare_alpha --help
.tmp\venv-editable-check\Scripts\python -m ashare_alpha show-version
```

If the clean virtual environment works, the project package discovery is healthy and the global Python installation should be repaired or avoided. Use the clean virtual environment for development, or set `$env:PYTHONPATH = "src"` temporarily when validating the current checkout from the repository root.

Windows permission warnings:

Use a repo-local temporary directory and disable pytest cache provider as shown above.

## 9. Safety Boundary

Do not put API keys, tokens, broker credentials, or secrets in configs, docs, tests, scripts, or outputs. The current system is offline for research, backtesting, signal generation, and reporting. It does not scrape websites, call external APIs, connect to brokers, or place live orders.
