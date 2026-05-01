# Despliega un servicio en Railway (requiere login o RAILWAY_TOKEN).
# 1) Instala CLI: npx --yes @railway/cli  (ya resuelto abajo)
# 2) Autenticacion (una vez):
#    npx @railway/cli login
#    o en CI:  $env:RAILWAY_TOKEN = "..."  (token de Account Settings en railway.app)
# 3) En el directorio del proyecto vinculado:  npx @railway/cli link
#
# Uso:
#   .\scripts\desplegar-railway.ps1 -Service api
#   .\scripts\desplegar-railway.ps1 -Service worker
#   .\scripts\desplegar-railway.ps1 -Service dashboard
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("api", "worker", "dashboard")]
  [string]$Service
)
$ErrorActionPreference = "Stop"
$appRoot = Split-Path $PSScriptRoot -Parent
Set-Location $appRoot

$npx = (Get-Command npx -ErrorAction Stop).Source
& $npx --yes @railway/cli whoami
if ($LASTEXITCODE -ne 0) {
  Write-Error "No hay sesion de Railway. Ejecuta: npx @railway/cli login  (o define RAILWAY_TOKEN en el entorno)."
}

# En el dashboard de Railway, cada servicio (api, worker, dashboard) debe existir; el -s apunta al nombre.
# El Dockerfile y build context de cada app estan bajo apps/<nombre> o segun vinculaste con 'railway link'.
& $npx @railway/cli up -s $Service
exit $LASTEXITCODE
