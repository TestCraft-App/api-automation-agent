# -*- mode: python ; coding: utf-8 -*-

import certifi

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('prompts', 'prompts'), ('api-framework-template', 'api-framework-template'), ('example.env', '.'), (certifi.where(), 'certifi')],
    hiddenimports=['six', 'dependency_injector.errors', 'anthropic', 'openai', 'langchain_anthropic', 'langchain_openai', 'langchain_core', 'tiktoken', 'json_repair', 'yaml', 'dotenv', 'tabulate', 'certifi'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='api-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
