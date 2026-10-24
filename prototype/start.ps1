param([int]$Port=8765)
$ErrorActionPreference='Stop'
$env:TRACEY_PORT="$Port"
$pythonCommand=Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) { & $pythonCommand.Source (Join-Path $PSScriptRoot 'server.py'); exit $LASTEXITCODE }
$bundled=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (Test-Path -LiteralPath $bundled) { & $bundled (Join-Path $PSScriptRoot 'server.py'); exit $LASTEXITCODE }
throw 'Python 3.10 or later is required. Install Python or set up a Python environment, then run python prototype/server.py.'
