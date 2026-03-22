@echo off
echo.
echo  ========================================
echo   World Simulation - Avvio completo
echo  ========================================
echo.

echo [1/3] Installazione dipendenze Python...
cd /d "%~dp0backend"
pip install -r requirements.txt
if errorlevel 1 ( echo ERRORE: pip install fallito & pause & exit /b 1 )

echo.
echo [2/3] Installazione dipendenze Node...
cd /d "%~dp0frontend"
npm install
if errorlevel 1 ( echo ERRORE: npm install fallito & pause & exit /b 1 )

echo.
echo [3/3] Avvio backend (porta 8000) e frontend (porta 3000)...
cd /d "%~dp0"
npm run dev

pause
