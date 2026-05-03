@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Bot Estiv - Tunel WhatsApp (Cloudflare)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-WhatsappTunnel.ps1"
echo.
pause
