@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist ".venv\Scripts\lessondigest.exe" (
  echo Не найден .venv\Scripts\lessondigest.exe
  echo Сначала установи окружение: README, раздел "Установка с нуля".
  pause
  exit /b 1
)
echo LessonDigest: http://127.0.0.1:8000   (Ctrl+C - остановить)
".venv\Scripts\lessondigest.exe" serve --host 127.0.0.1 --port 8000
pause
