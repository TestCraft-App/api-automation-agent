#!/bin/bash

echo "🚀 Building API Automation Agent for macOS..."

if [ -d "build" ]; then
    rm -rf "build"
fi

if [ -d "dist" ]; then
    rm -rf "dist"
fi

if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

pyinstaller --clean --noconfirm --log-level WARN api-automation-agent.spec

if [ -f "dist/api-automation-agent" ]; then
    echo "✅ Build completed successfully!"
    echo "📦 Executable created: dist/api-automation-agent"
    
    file_size=$(stat -f%z "dist/api-automation-agent" 2>/dev/null || stat -c%s "dist/api-automation-agent" 2>/dev/null)
    echo "📏 Size: $file_size bytes"
    
    echo "📁 Creating distribution package..."
    if [ -d "api-automation-agent-macos" ]; then
        rm -rf "api-automation-agent-macos"
    fi
    mkdir "api-automation-agent-macos"
    
cp "dist/api-automation-agent" "api-automation-agent-macos/"
cp "example.env" "api-automation-agent-macos/"
cp "USAGE-GUIDE.txt" "api-automation-agent-macos/"    echo "✅ Distribution package created: api-automation-agent-macos/"
else
    echo "❌ Build failed!"
    exit 1
fi