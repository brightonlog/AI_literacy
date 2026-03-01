@echo off
setlocal

echo ============================================
echo   Voice Clone TTS - 서버 시작
echo ============================================
echo.
echo [1] GPT-SoVITS API 서버를 새 창으로 시작합니다...
start "GPT-SoVITS API :9880" cmd /k "C:\Users\SSAFY\Desktop\AI\TTS\start_gptsovits.bat"

echo [2] GPT-SoVITS 초기화 대기 중 (15초)...
timeout /t 15 /nobreak > nul

echo [3] FastAPI 서버 시작 중 (http://localhost:8000)...
cd /d C:\Users\SSAFY\Desktop\AI\TTS
call venv\Scripts\activate
python main.py
