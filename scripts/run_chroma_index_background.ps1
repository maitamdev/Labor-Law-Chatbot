# Resume or continue Chroma V3 embed (no --force: keeps partial progress).
# Logs: storage/logs/chroma_build_stdout.log
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\build_index_v3.py"
$LogDir = Join-Path $Root "storage\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$OutLog = Join-Path $LogDir "chroma_build_stdout.log"
$ErrLog = Join-Path $LogDir "chroma_build_stderr.log"

$env:VIETLABOR_CHROMA_BATCH_SIZE = "128"
if (-not $env:VIETLABOR_TORCH_THREADS) { $env:VIETLABOR_TORCH_THREADS = "8" }

$args = @(
    $Script,
    "--target", "chroma",
    "--chroma-batch-size", "128"
)

Start-Process -FilePath $Python `
    -ArgumentList $args `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden

Write-Host "Chroma build started in background."
Write-Host "Stdout: $OutLog"
Write-Host "Stderr: $ErrLog"
Write-Host "Do NOT run build_index_v3 --force while this job runs."
