"""
Скрипт для быстрого выпуска новой версии
Запрашивает только номер версии
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

def run(cmd: str, check: bool = True, shell: bool = True, encoding: str = 'utf-8') -> Optional[subprocess.CompletedProcess]:
    """Выполняет команду и безопасно читает вывод"""
    print(f"🔧 Выполняю: {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors='replace'  # Заменяет некорректные символы на 
        )
        if result.stdout:
            clean_out = result.stdout.strip()
            if clean_out:
                print(f"✅ Вывод: {clean_out}")
        if result.stderr:
            clean_err = result.stderr.strip()
            if clean_err:
                print(f"⚠️  Ошибка: {clean_err}")
        if check and result.returncode != 0:
            print(f"❌ Команда завершилась с кодом {result.returncode}")
            sys.exit(result.returncode)
        return result
    except Exception as e:
        print(f"❌ Исключение при выполнении команды: {e}")
        if check:
            sys.exit(1)
        return None  # Явно возвращаем None при ошибке

def main():
    print("🚀 Скрипт выпуска новой версии")
    print("Формат версии: X.Y.Z, например: 1.2.0")

    version = input("\nВведите номер версии: ").strip()

    # Проверка формата
    if not version.replace(".", "").isdigit() or len(version.split(".")) != 3:
        print("❌ Ошибка: версия должна быть в формате X.Y.Z (например, 1.2.0)")
        sys.exit(1)

    tag_name = f"v{version}"

    print(f"\n📦 Версия: {version}")
    print(f"🏷  Тег: {tag_name}")

    confirm = input("\nПодтвердите выпуск (y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("❌ Отменено пользователем")
        sys.exit(0)

    # Обновляем VERSION
    try:
        with open("VERSION", "w", encoding="utf-8") as f:
            f.write(f"{version}\n")
        print(f"✅ Записано в VERSION: {version}")
    except Exception as e:
        print(f"❌ Не удалось записать VERSION: {e}")
        sys.exit(1)

    # Git команды
    run("git add VERSION")
    run(f'git commit -m "chore: bump version to {version}"')
    run("git checkout main")

    # Merge — может не потребоваться
    merge_result = run(
        "git merge HEAD@{1} --no-ff -m 'chore: merge release branch'",
        check=False
    )
    # ✅ Pylance: проверяем, что merge_result не None
    if merge_result is not None and merge_result.returncode != 0:
        print("ℹ️  Merge не требуется или уже выполнен — продолжаем")

    run("git push origin main")
    run(f"git tag {tag_name}")
    run(f"git push origin {tag_name}")

    print("\n" + "✅" * 50)
    print(f"🎉 Выпуск {tag_name} запущен!")
    print("GitHub Actions начнёт сборку .exe и создаст релиз.")
    print(f"Смотрите: github.com/ваш-репозиторий/actions")
    print("✅" * 50)


if __name__ == "__main__":
    main()