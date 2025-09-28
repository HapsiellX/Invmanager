@echo off
echo Stopping Inventory Management System...
echo.

REM Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running or not installed.
    pause
    exit /b 1
)

echo Stopping all services...
docker-compose down

echo.
echo Checking if services are stopped...
docker-compose ps

echo.
echo System stopped successfully!
echo.
echo To start the system again, run: start.bat
echo To completely remove all data (including database), run: docker-compose down -v
echo.
pause