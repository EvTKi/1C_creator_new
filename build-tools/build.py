"""
Сборка .exe — с защитой от ошибок путей и кодировки
"""

import subprocess
import sys
from pathlib import Path
import shutil
import zipfile
import toml


# --- Пути ---
ROOT_DIR = Path(__file__).parent.parent  # Корень проекта
BUILD_TOOLS_DIR = Path(__file__).parent
DIST_DIR = ROOT_DIR / "dist"
FINAL_DIR = DIST_DIR / "final"

CONFIG_FILE = ROOT_DIR/ "build.toml"
VERSION_FILE = ROOT_DIR / "VERSION"


# --- Чтение версии ---
try:
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        VERSION = f.read().strip()
    if not VERSION.replace(".", "").isdigit() or len(VERSION.split(".")) != 3:
        raise ValueError(f"Неверный формат версии: {VERSION}")
    print(f"✅ Версия: {VERSION}")
except Exception as e:
    print(f"Ошибка чтения VERSION: {e}")
    sys.exit(1)


# --- Загрузка конфига ---
try:
    if not CONFIG_FILE.exists():
        print(f"❌ Файл конфигурации не найден: {CONFIG_FILE.absolute()}")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = toml.load(f)
    print(f"✅ Конфиг загружен: {CONFIG_FILE}")
except Exception as e:
    print(f"Ошибка загрузки build.toml: {type(e).__name__}: {e}")
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
            print(f"🧹 Удалена папка: {folder}")


# --- Сборка ---
def build_ex():
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

    print("🔧 Команда сборки:")
    print(" ".join(cmd))

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("❌ Сборка не удалась")
        sys.exit(1)


# --- Подготовка финальной папки ---
def prepare_final():
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    exe_name = f"{pyi['name']}.exe"
    src_exec = DIST_DIR / exe_name
    dst_exec = FINAL_DIR / exe_name

    if not src_exec.exists():
        print(f"❌ Файл не найден: {src_exec}")
        sys.exit(1)

    shutil.copy(src_exec, dst_exec)
    print(f"✅ Скопирован: {exe_name}")

    config_json = ROOT_DIR / "config.json"
    if not config_json.exists():
        print(f"❌ config.json не найден: {config_json}")
        sys.exit(1)
    shutil.copy(config_json, FINAL_DIR / "config.json")
    print("✅ Скопирован: config.json")


# --- Архивация ---
def make_zip():
    with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in FINAL_DIR.iterdir():
            zf.write(file, arcname=file.name)
    print(f"📦 Архив создан: {ZIP_NAME}")


# --- Главная ---
if __name__ == "__main__":
    print(f"🚀 Сборка: {build['name']} v{VERSION}")
    clean()
    build_ex()
    prepare_final()
    make_zip()
    print(f"✅ Сборка завершена: {ZIP_NAME}")