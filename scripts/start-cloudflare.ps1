param([string]$Cloudflared="cloudflared",[string]$Python="python")
$ErrorActionPreference="Stop"
$ProjectRoot=Split-Path $PSScriptRoot -Parent
$RuntimeRoot=Join-Path $ProjectRoot '.runtime'
New-Item -ItemType Directory -Force $RuntimeRoot | Out-Null
if (-not (Test-Path (Join-Path $ProjectRoot '.env'))) { & $Python (Join-Path $PSScriptRoot 'init-env.py') }
if (-not (Test-Path (Join-Path $ProjectRoot 'web/dist/index.html'))) { throw 'Compile o frontend antes: cd web; npm install; npm run build' }
$OriginProcess=Start-Process -FilePath $Python -ArgumentList @('scripts/local-https.py','--http') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RuntimeRoot 'origin.log') -RedirectStandardError (Join-Path $RuntimeRoot 'origin-error.log')
$TunnelLog=Join-Path $RuntimeRoot 'tunnel.log'
$TunnelProcess=Start-Process -FilePath $Cloudflared -ArgumentList @('tunnel','--url','http://127.0.0.1:8080','--no-autoupdate') -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RuntimeRoot 'tunnel-out.log') -RedirectStandardError $TunnelLog
$PublicUrl=$null
for ($Try=0;$Try -lt 45;$Try++) {
 Start-Sleep -Seconds 1
 if (Test-Path $TunnelLog) {
  $Match=[regex]::Match((Get-Content $TunnelLog -Raw),'https://[a-z0-9-]+\.trycloudflare\.com')
  if ($Match.Success) { $PublicUrl=$Match.Value; break }
 }
 if ($TunnelProcess.HasExited) { throw "Tunnel falhou. Consulte $TunnelLog" }
}
if (-not $PublicUrl) { throw "URL não recebida. Consulte $TunnelLog" }
$EnvFile=Join-Path $ProjectRoot '.env'
$EnvText=Get-Content $EnvFile -Raw
$EnvText=$EnvText -replace '(?m)^CORS_ORIGINS=.*$',"CORS_ORIGINS=$PublicUrl"
$EnvText=$EnvText -replace '(?m)^PUBLIC_URL=.*$',"PUBLIC_URL=$PublicUrl"
Set-Content -LiteralPath $EnvFile -Value $EnvText -Encoding utf8
Get-Content $EnvFile | ForEach-Object { if ($_ -match '^([A-Z_]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1],$matches[2],'Process') } }
Push-Location (Join-Path $ProjectRoot 'backend')
try { & $Python -m alembic upgrade head; if ($LASTEXITCODE -ne 0) { throw 'Migration falhou' } }
finally { Pop-Location }
$BackendProcess=Start-Process -FilePath $Python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $ProjectRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $RuntimeRoot 'backend.log') -RedirectStandardError (Join-Path $RuntimeRoot 'backend-error.log')
Write-Output "SetRastrear: $PublicUrl"
Write-Output "Configure a mesma URL no Android. Processos: origem=$($OriginProcess.Id), tunnel=$($TunnelProcess.Id), backend=$($BackendProcess.Id)."
Write-Output 'O computador precisa continuar ligado. Os logs ficam em .runtime. Não execute duas instâncias simultaneamente.'
