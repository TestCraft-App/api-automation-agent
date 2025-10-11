
@echo off
echo 🚀 Building API Automation Agent...

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

call venv\Scripts\activate.bat

pyinstaller --clean --noconfirm --log-level WARN api-automation-agent.spec

if exist "dist\api-agent.exe" (
    echo ✅ Build completed successfully!
    echo 📦 Executable created: dist\api-agent.exe
    
    for %%A in ("dist\api-agent.exe") do echo 📏 Size: %%~zA bytes
    
    echo 📁 Creating distribution package...
    if exist "api-agent-windows" rmdir /s /q "api-agent-windows"
    mkdir "api-agent-windows"
    
    copy "dist\api-agent.exe" "api-agent-windows\"
    copy "example.env" "api-agent-windows\"
    copy "USAGE-GUIDE.txt" "api-agent-windows\"
    
    echo ✅ Distribution package created: api-agent-windows\
) else (
    echo ❌ Build failed!
)

pause