"""
Сборка .exe — безопасный вывод (только ASCII)
"""

import subprocess
import sys
from pathlib import Path
import shutil
import zipfile
import toml


# --- Пути ---
ROOT_DIR = Path(__file__).parent.parent
DIST_DIR = ROOT_DIR / "dist"
FINAL_DIR = DIST_DIR / "final"

CONFIG_FILE = ROOT_DIR / "build.toml"
VERSION_FILE = ROOT_DIR / "VERSION"


# --- Чтение версии ---
try:
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        VERSION = f.read().strip()
    if not VERSION.replace(".", "").isdigit() or len(VERSION.split(".")) != 3:
        raise ValueError(f"Invalid version format: {VERSION}")
    print(f"[OK] Version: {VERSION}")
except Exception as e:
    print(f"[ERROR] Failed to read VERSION: {e}")
    sys.exit(1)


# --- Загрузка конфига ---
try:
    if not CONFIG_FILE.exists():
        print(f"[ERROR] Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = toml.load(f)
    print(f"[OK] Config loaded")
except Exception as e:
    print(f"[ERROR] Failed to load build.toml: {type(e).__name__}")
    sys.exit(1)


# --- Данные из конфига ---
pyi = config["pyinstaller"]
build = config["build"]
ZIP_NAME = DIST_DIR / f"{build['name']}_v{VERSION}.zip"


# --- Очистка ---
def clean():
    for folder in ["build", "dist"]:
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p)
            print(f"[OK] Cleaned: {folder}")


# --- Сборка ---
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

    print("[INFO] Running PyInstaller...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("[ERROR] Build failed")
        sys.exit(1)


# --- Подготовка финальной папки ---
def prepare_final():
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    exe_name = f"{pyi['name']}.exe"
    src_exe = DIST_DIR / exe_name
    dst_exe = FINAL_DIR / exe_name

    if not src_exe.exists():
        print(f"[ERROR] Executable not found: {exe_name}")
        sys.exit(1)

    shutil.copy(src_exe, dst_exe)
    print(f"[OK] Binary copied")

    config_json = ROOT_DIR / "config.json"
    if not config_json.exists():
        print("[ERROR] config.json not found")
        sys.exit(1)
    shutil.copy(config_json, FINAL_DIR / "config.json")
    print("[OK] Config copied")


# --- Архивация ---
def make_zip():
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in FINAL_DIR.iterdir():
            zf.write(file, arcname=file.name)
    print(f"[OK] Archive created: {ZIP_NAME}")


# --- Главная ---
if __name__ == "__main__":
    print(f"[INFO] Building {build['name']} v{VERSION}")
    clean()
    build_exe()
    prepare_final()
    make_zip()
    print(f"[SUCCESS] Build completed")