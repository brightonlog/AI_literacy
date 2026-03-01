@echo off
setlocal

echo ============================================
echo   GPT-SoVITS 설치 스크립트
echo ============================================
echo.

REM GPT-SoVITS clone 위치
set INSTALL_DIR=C:\Users\SSAFY\Desktop\AI\GPT-SoVITS

if exist "%INSTALL_DIR%" (
    echo [INFO] GPT-SoVITS 디렉토리가 이미 존재합니다: %INSTALL_DIR%
    echo        건너뜁니다. 재설치하려면 디렉토리를 삭제 후 다시 실행하세요.
) else (
    echo [1/4] GPT-SoVITS 레포지토리 클론 중...
    cd /d C:\Users\SSAFY\Desktop\AI
    git clone https://github.com/RVC-Boss/GPT-SoVITS.git
    if errorlevel 1 (
        echo [ERROR] git clone 실패. git이 설치되어 있는지 확인하세요.
        pause
        exit /b 1
    )
)

echo.
echo [2/4] conda 환경 생성 중 (Python 3.10)...
conda create -n gpt-sovits python=3.10 -y
if errorlevel 1 (
    echo [ERROR] conda 환경 생성 실패. Anaconda/Miniconda가 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

echo.
echo [3/4] 의존성 패키지 설치 중...
call conda activate gpt-sovits
cd /d %INSTALL_DIR%
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARN] 일부 패키지 설치 오류가 발생했습니다. 로그를 확인하세요.
)

echo.
echo [4/4] 사전 학습 모델 안내
echo ============================================
echo   아래 모델 파일을 다운로드해서
echo   %INSTALL_DIR%\pretrained_models\ 에 배치하세요.
echo.
echo   HuggingFace: https://huggingface.co/lj1995/GPT-SoVITS
echo.
echo   필수 파일:
echo     - s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt
echo     - s2G488k.pth
echo     - s2D488k.pth
echo     - chinese-roberta-wwm-ext-large (폴더)
echo     - chinese-hubert-base (폴더)
echo ============================================
echo.
echo [완료] 설치 완료! 모델 배치 후 start_all.bat을 실행하세요.
pause
