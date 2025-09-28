@echo off
echo Git Operations for Inventory Management System
echo.

REM Check if we're in a git repository
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo This directory is not a git repository.
    echo Initializing git repository...
    git init
    echo.
    echo Please set up your remote repository first:
    echo git remote add origin [your-repository-url]
    echo.
    pause
    exit /b 1
)

echo Current git status:
git status
echo.

echo What would you like to do?
echo 1. Add all changes and commit
echo 2. Push to remote repository
echo 3. Pull from remote repository
echo 4. View commit history
echo 5. Create and push a new branch
echo 6. Complete workflow (add, commit, push)
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto add_commit
if "%choice%"=="2" goto push
if "%choice%"=="3" goto pull
if "%choice%"=="4" goto history
if "%choice%"=="5" goto new_branch
if "%choice%"=="6" goto complete_workflow

echo Invalid choice. Exiting...
pause
exit /b 1

:add_commit
echo.
set /p message="Enter commit message: "
if "%message%"=="" (
    set message="Update inventory management system"
)
echo Adding all changes...
git add .
echo Committing changes...
git commit -m "%message%"
echo Done!
goto end

:push
echo.
echo Pushing to remote repository...
git push origin main
if %errorlevel% neq 0 (
    echo Push failed. Trying to push current branch...
    git push origin HEAD
)
echo Done!
goto end

:pull
echo.
echo Pulling from remote repository...
git pull origin main
echo Done!
goto end

:history
echo.
echo Recent commit history:
git log --oneline -10
goto end

:new_branch
echo.
set /p branch_name="Enter new branch name: "
if "%branch_name%"=="" (
    echo Branch name cannot be empty.
    goto end
)
echo Creating and switching to new branch...
git checkout -b %branch_name%
echo Pushing new branch to remote...
git push -u origin %branch_name%
echo Done!
goto end

:complete_workflow
echo.
set /p message="Enter commit message: "
if "%message%"=="" (
    set message="Update inventory management system"
)
echo Adding all changes...
git add .
echo Committing changes...
git commit -m "%message%"
echo Pushing to remote repository...
git push origin main
if %errorlevel% neq 0 (
    echo Push to main failed. Trying to push current branch...
    git push origin HEAD
)
echo Complete workflow finished!
goto end

:end
echo.
echo Current status:
git status
echo.
pause