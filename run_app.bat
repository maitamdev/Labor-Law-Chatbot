@echo off
chcp 65001 > nul
title VietLabor AI - Khoi Chay Ung Dung

echo ========================================================
echo        VIETLABOR AI - TRO LY PHAP LUAT LAO DONG
echo ========================================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [LOI] Khong tim thay moi truong ao .venv!
    echo Vui long tao moi truong ao: python -m venv .venv
    pause
    exit /b 1
)

echo [1/2] Dang kich hoat moi truong ao .venv...
call .venv\Scripts\activate.bat

echo [2/2] Dang khoi chay giao dien Streamlit...
echo Dia chi truy cap: http://localhost:8501
echo.
streamlit run ui/streamlit_app.py

pause
