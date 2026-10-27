param([ValidateSet("backend","web","test","purge")][string]$Component="backend")
$ErrorActionPreference="Stop"
$ProjectRoot=Split-Path $PSScriptRoot -Parent
Get-Content (Join-Path $ProjectRoot '.env') | ForEach-Object { if ($_ -match '^([A-Z_]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1],$matches[2],'Process') } }
if ($Component -eq 'web') { Set-Location (Join-Path $ProjectRoot 'web'); npm run dev }
else { Set-Location (Join-Path $ProjectRoot 'backend')
 if ($Component -eq 'test') { python -m pytest -q }
 elseif ($Component -eq 'purge') { python -m app.manage purge }
 else { python -m alembic upgrade head; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 }
}
