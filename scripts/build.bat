
@echo off
echo 🚀 Building API Automation Agent...

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

call venv\Scripts\activate.bat

pyinstaller --clean --noconfirm --log-level WARN api-automation-agent.spec

if exist "dist\api-automation-agent.exe" (
    echo ✅ Build completed successfully!
    echo 📦 Executable created: dist\api-automation-agent.exe
    
    for %%A in ("dist\api-automation-agent.exe") do echo 📏 Size: %%~zA bytes
    
    echo 📁 Creating distribution package...
    if exist "api-automation-agent-windows" rmdir /s /q "api-automation-agent-windows"
    mkdir "api-automation-agent-windows"
    
    copy "dist\api-automation-agent.exe" "api-automation-agent-windows\"
    copy "example.env" "api-automation-agent-windows\"
    copy "USAGE-GUIDE.md" "api-automation-agent-windows\"
    copy "USAGE-GUIDE.txt" "api-automation-agent-windows\"
    
    echo ✅ Distribution package created: api-automation-agent-windows\
) else (
    echo ❌ Build failed!
)

pause