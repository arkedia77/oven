@echo off
cd /d C:\projects\harmonicity
set PYTHONIOENCODING=utf-8
set HARMONICITY_API_URL=http://localhost:8080/v1/chat/completions
set HARMONICITY_CONFIG_OVERRIDES={"REP_WARMTH_FLOOR": 0.15}

rem --- D-track gates (kee decision 2026-07-31): observation/safety ON, behavior-change HOLD ---
set HARMONICITY_DECISION_LOG=1
set HARMONICITY_KILL_SWITCH=1
set HARMONICITY_SAFETY_SNAPSHOT=1
rem HOLD (do not enable without kee/LEO decision): HARMONICITY_ECONOMY, HARMONICITY_INSTITUTION, HARMONICITY_AUTONOMY_LOCATION

echo [%date% %time%] Waiting for LLM server...
:WAITLLM
curl -s http://localhost:8080/health >nul 2>&1
if errorlevel 1 (
    timeout /t 10 /nobreak >nul
    goto WAITLLM
)
echo [%date% %time%] LLM server ready, testing slot...
curl -s http://localhost:8080/slots >nul 2>&1
if errorlevel 1 (
    timeout /t 10 /nobreak >nul
    goto WAITLLM
)

echo [%date% %time%] Starting simulation...
C:\Python314\python.exe -u run_village.py 2>> sim_stderr.log
echo [%date% %time%] Simulation exited, code=%errorlevel% >> sim_stderr.log
