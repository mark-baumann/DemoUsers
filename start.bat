@echo off
setlocal

REM Stop any existing Python/Uvicorn processes first
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM uvicorn.exe /F >nul 2>&1

REM Install dependencies using the active Python
python -m pip install -r requirements.txt
if errorlevel 1 goto :end

REM Start API server in background (suppress access logs)
start "FakeAccounts API" /b python -m uvicorn MailService.api_server:app --host 127.0.0.1 --port 8000 --reload --log-level warning --no-access-log

echo Waiting for API to become ready...
powershell -NoProfile -Command "for($i=0;$i -lt 30;$i++){ try{ if((Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://127.0.0.1:8000/').StatusCode -ge 200){ exit 0 } } catch{} Start-Sleep -s 1 }; exit 1"
if errorlevel 1 (
  echo API did not start in time.
  goto :end
)

REM Run the Mail client
python MailClient.py

echo.
echo Press Ctrl+C to stop the API server window if still running.
pause >nul

:end
endlocal


