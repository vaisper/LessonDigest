# Запускает LessonDigest: веб-интерфейс + обработка уроков (один процесс).
# Примеры:
#   .\scripts\start.ps1
#   .\scripts\start.ps1 -Bind 0.0.0.0 -Port 8000

param(
    [string]$Bind = "127.0.0.1",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $root ".venv\Scripts\lessondigest.exe"

if (-not (Test-Path $exe)) {
    Write-Error "Не найден $exe. Сначала установи окружение (README, раздел «Установка с нуля»)."
    exit 1
}

Set-Location $root
Write-Host "LessonDigest: http://${Bind}:$Port   (Ctrl+C - остановить)"
& $exe serve --host $Bind --port $Port
