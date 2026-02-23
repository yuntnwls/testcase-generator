@echo off
echo ===================================================
echo   Universal Test Script Generator - UI Launcher
echo ===================================================
echo.
echo Activating Virtual Environment...
call .\venv\Scripts\activate.bat

echo.
echo Starting Web Dashboard (Streamlit)...
echo Please wait a moment while the browser opens.
echo.

:: Streamlit 앱 실행 시 프로젝트 루트를 PYTHONPATH에 추가하여 하위 프로세스 임포트 문제 방지
set PYTHONPATH=%cd%
python -m streamlit run src\ui\app.py
set PYTHONPATH=

echo.
echo Dashboard closed.
pause
