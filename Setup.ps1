param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.9+ is required. Pass -Python with its executable path.' }
}
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $pythonExe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not (Test-Path -LiteralPath '.env')) {
    & $pythonExe scripts/setup_database.py
    if ($LASTEXITCODE -ne 0) { throw 'Database setup did not finish.' }
}
& $pythonExe manage.py init-db
if ($LASTEXITCODE -ne 0) { throw 'Schema initialization failed.' }
Write-Host 'Create a user: .\.venv\Scripts\python.exe manage.py create-user --login student'
Write-Host 'Run the API: .\Start.ps1'
