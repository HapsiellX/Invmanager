@echo off
echo Starting Inventory Management System...
echo.

REM Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running or not installed.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo Creating .env file from template...
    copy ".env.template" ".env"
    echo.
    echo WARNING: Please edit .env file with your configuration before continuing.
    echo Press any key to open .env file for editing...
    pause >nul
    notepad .env
    echo.
    echo Please save the .env file and restart this script.
    pause
    exit /b 1
)

echo Pulling latest images...
docker-compose pull

echo Building and starting services...
docker-compose up -d --build

echo.
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo Checking service status...
docker-compose ps

echo.
echo Services started successfully!
echo.
echo Access the application at: http://localhost:8501
echo Access database admin at: http://localhost:8080 (development only)
echo.
echo To stop the system, run: stop.bat
echo To view logs, run: docker-compose logs -f
echo.
pause