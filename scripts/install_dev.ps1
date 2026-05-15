param(
    [switch]$NoDev
)

$ErrorActionPreference = "Stop"

Write-Host "ashare-alpha-lab development install"
Write-Host "Current python:"
python --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "python is not available on PATH."
}

Write-Host "Recommended interpreter:"
py -3.12 --version

if ($NoDev) {
    Write-Host "Installing editable package without dev extras..."
    py -3.12 -m pip install -e .
} else {
    Write-Host "Installing editable package with dev extras..."
    py -3.12 -m pip install -e ".[dev]"
}

Write-Host "Running environment diagnostics..."
py -3.12 scripts/dev_check.py
