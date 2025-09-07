"""
Сборка .exe для Конвертера CSV → RDF/XML
Режим: только release (без консоли)
"""

import toml
import subprocess
import sys
from pathlib import Path
import shutil
import zipfile

# --- Настройки ---
CONFIG_FILE = "build.toml"
BUILD_MODE = "release"  # В CI всегда release

# --- Загружаем конфиг ---
try:
    config = toml.load(CONFIG_FILE)
except FileNotFoundError:
    print(f"❌ Файл конфигурации не найден: {CONFIG_FILE}")
    sys.exit(1)

pyi = config["pyinstaller"]
build = config["build"]

# --- Пути ---
src_dir = Path("src")
dist_dir = Path("dist")
final_dir = dist_dir / "final"
zip_name = f"{build['name']}_v{build['version']}.zip"

# --- Очистка ---
def clean():
    for folder in ["build", "dist"]:
        if Path(folder).exists():
            shutil.rmtree(folder)
            print(f"🧹 Удалена папка: {folder}")

# --- Сборка ---
def build_exe():
    cmd = [sys.executable, "-m", "PyInstaller"]
    cmd.append("--noconsole")        # Только release
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

# --- Подготовка финальной папки ---
def prepare_final():
    final_dir.mkdir(parents=True, exist_ok=True)
    
    # Копируем .exe
    exe_name = f"{pyi['name']}.exe"
    src_exe = dist_dir / exe_name
    dst_exe = final_dir / exe_name
    
    if not src_exe.exists():
        print(f"❌ Файл не найден: {src_exe}")
        sys.exit(1)
        
    shutil.copy(src_exe, dst_exe)
    print(f"✅ Скопирован: {exe_name}")
    
    # Копируем config.json
    if Path("config.json").exists():
        shutil.copy("config.json", final_dir / "config.json")
        print("✅ Скопирован: config.json")
    else:
        print("❌ config.json не найден!")
        sys.exit(1)

# --- Архивация ---
def make_zip():
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in final_dir.iterdir():
            zf.write(file, arcname=file.name)
    print(f"📦 Архив создан: {zip_name}")

# --- Основной процесс ---
if __name__ == "__main__":
    print(f"🚀 Сборка: {build['name']} v{build['version']} (режим: release)")
    clean()
    build_exe()
    prepare_final()
    make_zip()
    print(f"✅ Сборка завершена: {zip_name}")