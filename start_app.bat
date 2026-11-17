@echo off
REM Startup script for ER Wait Time Prediction App (Windows)

echo ============================================== 
echo ER Wait Time Prediction - Starting Services
echo ==============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo Dependencies OK
echo.

echo Starting FastAPI server on port 8000...
start /B python main.py
timeout /t 3 /nobreak >nul

echo FastAPI server started
echo.

echo Starting Streamlit app on port 8501...
echo Opening browser at http://localhost:8501
echo.
echo Press Ctrl+C to stop both services
echo ==============================================
echo.

streamlit run streamlit_app.py

echo.
echo Goodbye!
