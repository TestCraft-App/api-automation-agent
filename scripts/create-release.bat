@echo off

if "%1"=="" (
    echo Usage: %0 ^<version^>
    echo Example: %0 v1.0.0
    exit /b 1
)

set VERSION=%1

echo 🚀 Creating release %VERSION%

for /f %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
if not "%BRANCH%"=="main" (
    echo ❌ Error: Must be on main branch to create release
    echo Current branch: %BRANCH%
    exit /b 1
)

git status --porcelain > temp_status.txt
for %%A in (temp_status.txt) do if %%~zA neq 0 (
    echo ❌ Error: Working directory is not clean
    echo Please commit all changes before creating release
    git status --short
    del temp_status.txt
    exit /b 1
)
del temp_status.txt

echo 📝 Creating and pushing tag %VERSION%
git tag -a "%VERSION%" -m "Release %VERSION%"
git push origin "%VERSION%"

echo ⬆️ Pushing latest changes to main branch
git push origin main

echo ✅ Release %VERSION% created successfully!
echo 📦 GitHub Actions is now building the release...
echo 🔗 Check progress at: https://github.com/TestCraft-App/api-automation-agent/actions