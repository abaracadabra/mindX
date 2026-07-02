<#
.SYNOPSIS
  One-shot setup for The Dojo's training engine (Windows).
.EXAMPLE
  .\scripts\setup.ps1                # auto-detect target
  .\scripts\setup.ps1 rocm-windows   # force AMD ROCm (needs Python 3.12 + driver 26.2.2+)
#>
param([string]$Target = "auto")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "==> Creating venv (.venv)" -ForegroundColor Cyan
python -m venv .venv
$venvPy = ".\.venv\Scripts\python.exe"

Write-Host "==> Installing training stack (target: $Target)" -ForegroundColor Cyan
Push-Location engine
& "..\$venvPy" -m dojo_engine.installer --install --target $Target
Pop-Location

Write-Host "==> Fetching llama.cpp sidecar (auto-detect accel)" -ForegroundColor Cyan
try { & $venvPy scripts\fetch_llama.py } catch { Write-Warning "sidecar fetch skipped: $_" }

Write-Host "==> Done. Set the app's Python path to: $(Resolve-Path $venvPy)" -ForegroundColor Green
