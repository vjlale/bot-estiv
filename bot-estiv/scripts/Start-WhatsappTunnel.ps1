#Requires -Version 5.1
<#
.SYNOPSIS
  Expone la API local (puerto 8000) por HTTPS vía Cloudflare quick tunnel (trycloudflare.com).
  Copiá la URL que imprime en Twilio: WhatsApp sender > When a message comes in > POST

  Requisito: la API debe estar en marcha (make dev-api o uvicorn en :8000).
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CfExe = Join-Path $ProjectRoot "tools\cloudflared.exe"
$CfDownload = "https://github.com/cloudflare/cloudflared/releases/download/2025.8.1/cloudflared-windows-amd64.exe"
$UrlFile = Join-Path $ProjectRoot "tools\LAST_WEBHOOK_URL.txt"

if (-not (Test-Path $CfExe)) {
    $toolsDir = Split-Path $CfExe -Parent
    New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
    Write-Host "Descargando cloudflared (una sola vez)..." -ForegroundColor Cyan
    $tmp = "$CfExe.downloading"
    curl.exe -fsSL -o $tmp $CfDownload
    Move-Item -Force $tmp $CfExe
}

$portTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 8000 -WarningAction SilentlyContinue
if (-not $portTest.TcpTestSucceeded) {
    Write-Host ""
    Write-Host "ADVERTENCIA: no hay nada escuchando en 127.0.0.1:8000" -ForegroundColor Yellow
    Write-Host "Abrí OTRA terminal en la carpeta bot-estiv y ejecutá:" -ForegroundColor Yellow
    Write-Host "  make dev-api" -ForegroundColor White
    Write-Host "  (o: cd apps/api && uv run uvicorn bot_estiv.main:app --reload --port 8000)" -ForegroundColor DarkGray
    Write-Host ""
}

Write-Host ""
Write-Host "Iniciando tunel Cloudflare (dejá esta ventana abierta mientras probás WhatsApp)." -ForegroundColor Green
Write-Host "La URL cambia cada vez que reiniciás este script." -ForegroundColor DarkGray
Write-Host ""

$published = $false
& $CfExe tunnel --url "http://127.0.0.1:8000" 2>&1 | ForEach-Object {
    # 2>&1 devuelve ErrorRecord para stderr; forzar a cadena para -match
    $line = "$_"
    Write-Host $line
    if ($line -match "https://[a-zA-Z0-9.-]+\.trycloudflare\.com") {
        $base = $Matches[0].Trim()
        $webhook = "$base/webhook/twilio"
        if (-not $published) {
            $published = $true
            Set-Content -Path $UrlFile -Value $webhook -Encoding utf8
            Write-Host ""
            Write-Host "============================================================" -ForegroundColor Cyan
            Write-Host "  WEBHOOK (copiá en Twilio > Messaging / WhatsApp sender):" -ForegroundColor Cyan
            Write-Host "  $webhook" -ForegroundColor Yellow
                Write-Host "  (también guardado en: tools\LAST_WEBHOOK_URL.txt)" -ForegroundColor DarkGray
                Write-Host "  En Twilio: https://console.twilio.com/  > Messaging" -ForegroundColor DarkGray
                Write-Host "  > Senders o Sandbox > 'When a message comes in' = POST a la URL de arriba" -ForegroundColor DarkGray
                Write-Host "============================================================" -ForegroundColor Cyan
                Write-Host ""
        }
    }
}
