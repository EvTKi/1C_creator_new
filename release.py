"""
Скрипт для быстрого выпуска новой версии
Запрашивает номер версии и делает всё за вас
"""

import subprocess
import sys
from pathlib import Path


def run(cmd: str, check=True, shell=True):
    """Выполняет команду в оболочке"""
    print(f"🔧 Выполняю: {cmd}")
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"❌ Ошибка: {result.stderr}")
        if check:
            sys.exit(result.returncode)
    else:
        print(f"✅ Успешно: {result.stdout.strip()}")
    return result


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
    with open("VERSION", "w", encoding="utf-8") as f:
        f.write(version + "\n")
    
    print(f"✅ Записано в VERSION: {version}")
    
    # Git команды
    run("git add VERSION")
    run(f'git commit -m "chore: bump version to {version}"')
    run("git checkout main")
    run("git merge HEAD@{1} --no-ff -m 'chore: merge release branch' || echo 'Merge не требуется'")
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