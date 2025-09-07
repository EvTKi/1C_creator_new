"""
Скрипт выпуска новой версии — с поддержкой UTF-8
"""

import subprocess
import sys
from pathlib import Path


def run(cmd: str, check=True, shell=True):
    print(f"🔧 Выполняю: {cmd}")
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.stdout:
        print(f"✅ {result.stdout.strip()}")
    if result.stderr:
        print(f"⚠️  {result.stderr.strip()}")
    if check and result.returncode != 0:
        print(f"❌ Ошибка: {result.returncode}")
        sys.exit(result.returncode)
    return result


def main():
    print("🚀 Скрипт выпуска новой версии")
    print("Формат версии: X.Y.Z, например: 1.5.0")

    version = input("\nВведите номер версии: ").strip()

    if not version.replace(".", "").isdigit() or len(version.split(".")) != 3:
        print("❌ Ошибка: версия должна быть в формате X.Y.Z")
        sys.exit(1)

    tag_name = f"v{version}"

    print(f"\n📦 Версия: {version}")
    print(f"🏷  Тег: {tag_name}")

    confirm = input("\nПодтвердите выпуск (y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("❌ Отменено пользователем")
        sys.exit(0)

    # ✅ Запись в UTF-8
    try:
        with open("VERSION", "w", encoding="utf-8", newline='\n') as f:
            f.write(f"{version}\n")
        print(f"✅ Записано в VERSION (UTF-8): {version}")
    except Exception as e:
        print(f"❌ Ошибка записи VERSION: {e}")
        sys.exit(1)

    # Git команды
    run("git add VERSION")
    run(f'git commit -m "chore: bump version to {version}"')
    run("git checkout main")
    merge_result = run("git merge HEAD@{1} --no-ff -m 'chore: merge release branch'", check=False)
    if merge_result.returncode != 0:
        print("ℹ️  Merge не требуется или уже выполнен")
    run("git push origin main")
    run(f"git tag {tag_name}")
    run(f"git push origin {tag_name}")

    print("\n" + "✅" * 50)
    print(f"🎉 Выпуск {tag_name} запущен!")
    print("GitHub Actions начнёт сборку .exe и создаст релиз.")
    print("✅" * 50)


if __name__ == "__main__":
    main()