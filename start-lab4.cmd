@echo off
cd /d "%~dp0"
docker compose up -d --wait --wait-timeout 180
if errorlevel 1 (
  echo Start Docker Desktop, then try again. See Labs.md\lab4.md for first-time model import.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8501"
