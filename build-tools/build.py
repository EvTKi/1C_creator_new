"""
build.py — читает версию из VERSION
"""

import toml
import subprocess
import sys
from pathlib import Path
import shutil
import zipfile

# --- Пути ---
ROOT_DIR = Path(__file__).parent.parent
BUILD_TOOLS_DIR = Path(__file__).parent
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
FINAL_DIR = DIST_DIR / "final"

CONFIG_FILE = ROOT_DIR / "build.toml"
VERSION_FILE = ROOT_DIR / "VERSION"

# --- Чтение версии ---
try:
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        VERSION = f.read().strip()
    if not VERSION.replace(".", "").isdigit() or len(VERSION.split(".")) != 3:
        raise ValueError(f"Неверный формат версии: {VERSION}")
except Exception as e:
    print(f"❌ Ошибка чтения VERSION: {e}")
    sys.exit(1)

# --- Загрузка конфига ---
try:
    config = toml.load(CONFIG_FILE)
except Exception as e:
    print(f"❌ Ошибка загрузки build.toml: {e}")
    sys.exit(1)

pyi = config["pyinstaller"]
build = config["build"]

ZIP_NAME = DIST_DIR / f"{build['name']}_v{VERSION}.zip"

# --- Остальной код сборки ---
def clean():
    for folder in ["build", "dist"]:
        if Path(folder).exists():
            shutil.rmtree(folder)
            print(f"🧹 Удалена папка: {folder}")

def build_exe():
    cmd = [sys.executable, "-m", "PyInstaller"]
    cmd.append("--noconsole")
    cmd.append("--onefile")
    
    if pyi.get("name"):
        cmd.extend(["--name", pyi["name"]])
    
    for data in pyi.get("datas", []):
        src = data["src"]
        dest = data["dest"]
        sep = ";" if sys.platform.startswith("win") else ":"
        cmd.extend(["--add-data", f"{src}{sep}{dest}"])
    
    for module in pyi.get("hiddenimports", []):
        cmd.extend(["--hidden-import", module])
    
    for path in pyi.get("paths", []):
        cmd.extend(["--paths", path])
    
    cmd.append(pyi["script"])
    
    print(f"🔧 Сборка: {cmd}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("❌ Сборка не удалась")
        sys.exit(1)

def prepare_final():
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    exe_name = f"{pyi['name']}.exe"
    src_exe = DIST_DIR / exe_name
    dst_exe = FINAL_DIR / exe_name
    if not src_exe.exists():
        print(f"❌ Файл не найден: {src_exe}")
        sys.exit(1)
    shutil.copy(src_exe, dst_exe)
    print(f"✅ Скопирован: {exe_name}")
    shutil.copy(ROOT_DIR / "config.json", FINAL_DIR / "config.json")
    print("✅ Скопирован: config.json")

def make_zip():
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in FINAL_DIR.iterdir():
            zf.write(file, arcname=file.name)
    print(f"📦 Архив создан: {ZIP_NAME}")

if __name__ == "__main__":
    print(f"🚀 Сборка: {build['name']} v{VERSION}")
    clean()
    build_exe()
    prepare_final()
    make_zip()
    print(f"✅ Сборка завершена: {ZIP_NAME}")