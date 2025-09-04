"""
Скрипт для сборки приложения в .exe через PyInstaller.
"""
import os
import sys
from pathlib import Path

# Путь к проекту
project_dir = Path(__file__).parent
src_dir = project_dir / "src"

# Убедимся, что src в пути
sys.path.insert(0, str(src_dir))

def run_build():
    spec = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/ui.py'],
    pathex=[r'{src_dir}'],
    binaries=[],
    datas=[
        ('config.json', '.'),
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Конвертер CSV-RDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'  # если есть
)
"""

    spec_file = project_dir / "build.spec"
    spec_file.write_text(spec, encoding="utf-8")
    print("✅ Спецификация build.spec создана")

    # Запуск сборки
    os.system("pyinstaller build.spec")

if __name__ == "__main__":
    run_build()