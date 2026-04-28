# Uso: PowerShell, desde la carpeta interna del proyecto (la que contiene apps/, infra/, .env)
#   .\scripts\levantar-docker-y-migrar.ps1
# Requisitos: Docker Desktop en ejecucion, uv en PATH, .env rellenado.
$ErrorActionPreference = "Stop"
$appRoot = Split-Path $PSScriptRoot -Parent
$composeDir = Join-Path $appRoot "infra"
$apiDir = Join-Path $appRoot "apps\api"
$composeFile = Join-Path $composeDir "docker-compose.yml"

if (-not (Test-Path (Join-Path $appRoot ".env"))) {
  Write-Error "Falta $appRoot\.env (copia desde .env.example y rellena credenciales)."
}

$docker = $null
try { $docker = Get-Command docker -ErrorAction Stop } catch { }
if (-not $docker) {
  foreach ($c in @(
      "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
      "${env:ProgramFiles}\Docker\Docker\resources\bin\docker.exe"
    )) {
    if (Test-Path $c) { $docker = @{ Source = $c }; break }
  }
}
if (-not $docker) {
  Write-Error "No se encontro 'docker'. Instala Docker Desktop, inicia el motor y reintenta."
}

& $docker.Source compose -f $composeFile up -d postgres redis
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$uv = $null
try { $uv = Get-Command uv -ErrorAction Stop } catch { }
if (-not $uv) {
  Write-Error "No se encontro 'uv'. Instalacion: irm https://astral.sh/uv/install.ps1 | iex"
}

Push-Location $apiDir
& $uv.Source sync
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
& $uv.Source run alembic upgrade head
$code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { exit $code }

Write-Host "Listo: Postgres y Redis en marcha; migraciones OK." -ForegroundColor Green
Write-Host "API:  cd apps\api  ->  uv run uvicorn bot_estiv.main:app --reload --port 8000" -ForegroundColor Cyan
Write-Host "Worker: cd apps\api  ->  uv run arq bot_estiv.schedulers.worker.WorkerSettings" -ForegroundColor Cyan
Write-Host "Dash:  cd apps\dashboard  ->  npm run dev" -ForegroundColor Cyan
