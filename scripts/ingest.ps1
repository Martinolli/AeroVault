# AeroVault native ingestion runner.
# Runs the pipeline on Windows Python (fast) instead of through the Docker/OneDrive
# mount, which is roughly 40x slower for file reads.
#
# Examples:
#   .\scripts\ingest.ps1 scan
#   .\scripts\ingest.ps1 ingest -NoVectors
#   .\scripts\ingest.ps1 ingest -Limit 20
#   .\scripts\ingest.ps1 vectors-only
#   .\scripts\ingest.ps1 ocr
#   .\scripts\ingest.ps1 status

param(
    [Parameter(Position = 0)]
    [ValidateSet('scan', 'ingest', 'vectors-only', 'ocr', 'status')]
    [string]$Command = 'scan',
    [int]$Limit = 0,
    [string]$Collection = '',
    [switch]$NoVectors,
    [switch]$Force,
    [switch]$Ocr
)

$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $PSScriptRoot
Set-Location $Project

$env:PYTHONPATH = "$Project\.work\native_libs;$Project\backend"
$env:AEROVAULT_DATA_DIR = "$Project\data"

if (-not (Test-Path "$Project\.work\native_libs\pymupdf")) {
    throw "Native libs missing. Install them with: py -3 -m pip install --target .work\native_libs pydantic-settings pypdf pymupdf lancedb litellm pillow pytesseract"
}

# Load .env (API key, library root). Data dir stays as set above.
if (Test-Path "$Project\.env") {
    Get-Content "$Project\.env" | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$') {
            $value = $matches[2].Trim().Trim('"').Trim("'")
            Set-Item -Path "env:$($matches[1])" -Value $value
        }
    }
}
$env:AEROVAULT_DATA_DIR = "$Project\data"
if (-not $env:AEROVAULT_LIBRARY_ROOT) {
    throw "AEROVAULT_LIBRARY_ROOT is not set in .env"
}

$cliArgs = @(
    '-3', '-m', 'app.ingest.pipeline',
    '--db', "$Project\data\aerovault.db",
    '--lance', "$Project\data\lancedb",
    '--root', $env:AEROVAULT_LIBRARY_ROOT,
    $Command
)
if ($Limit -gt 0) { $cliArgs += @('--limit', "$Limit") }
if ($Collection) { $cliArgs += @('--collection', $Collection) }
if ($NoVectors) { $cliArgs += '--no-vectors' }
if ($Force) { $cliArgs += '--force' }
if ($Ocr) { $cliArgs += '--ocr' }

& py @cliArgs
